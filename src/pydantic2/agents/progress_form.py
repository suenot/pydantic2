from typing import List, Callable, Optional, TypeVar, Generic
from pydantic import BaseModel, Field, ConfigDict
from pydantic2 import PydanticAIClient, ModelSettings
import logging
import inspect
from abc import ABC
from contextlib import contextmanager
from .session_db_manager import SessionDBManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestAgentResponse(BaseModel):
    """Response from test agent"""
    response: str = Field(description="Agent's response text")


FormT = TypeVar('FormT', bound=BaseModel)


class FormState(BaseModel, Generic[FormT]):
    """Base state for tracking form progress and processing"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Form data and progress
    form: FormT
    progress: int = Field(default=0, description="Form progress (0-100)")
    prev_question: str = Field(default="", description="Previous question asked")
    prev_answer: str = Field(default="", description="Previous answer received")

    # Processing state
    feedback: str = Field(default="", description="Feedback on provided info")
    confidence: float = Field(
        default=0.0,
        ge=0, le=1,
        description="Confidence in state"
    )
    next_question: str = Field(default="", description="Next question to ask")
    next_question_explanation: str = Field(
        default="",
        description="Explanation of next question based on state"
    )


class BaseProgressForm(ABC):
    """Base class for processing form data with AI assistance"""

    def __init__(
        self,
        user_id: str,
        client_id: str,
        max_budget: int = 10,
        verbose: bool = False,
        verbose_clients: bool = False,
        form_class: type[BaseModel] = BaseModel,  # type: ignore
        client_agent: Optional[PydanticAIClient] = None,
        form_prompt: str = "",
        default_session_id: str = None,
    ):
        self.user_id = user_id
        self.client_id = client_id
        self.max_budget = max_budget
        self.verbose = verbose
        self.verbose_clients = verbose_clients
        self.form_class = form_class
        self._state_dirty = False  # Track if state has changed

        # Client pool to reduce instantiation overhead
        self._client_pool = {}

        # Initialize DB manager with optional session_id
        self.db_manager = SessionDBManager(default_session_id)

        # Try to restore session or create a new one
        self._restore_or_initialize_session(form_class)

        # Initialize tools list with process_form by default
        self._tools: List[Callable] = []

        # Set up base client
        self.client_agent = client_agent or self._get_base_client()

        # Initialize test agent (to be configured by child class)
        self.test_agent_client = None
        self.test_agent_prompt = None

        # Initialize form prompt
        self.form_prompt = form_prompt

        # Set logger level
        self.set_verbose()

    def _restore_or_initialize_session(self, form_class: type[BaseModel]):
        """Restore session state from DB or initialize a new one"""
        # Get or create session
        self.db_manager.get_or_create_session(
            self.db_manager.session_id,
            user_id=self.user_id,
            client_id=self.client_id,
            form_class=form_class.__name__
        )

        # Try to get the latest state with caching
        self._restore_latest_state_from_db()

    def _restore_latest_state_from_db(self):
        """Restore latest state from database with error handling"""
        state_data = self.db_manager.get_latest_state(use_cache=True)

        if state_data:
            try:
                # Restore form from state data
                form_data = state_data.get('form', {})
                form = self.form_class(**form_data)

                # Create state with restored form
                self.current_state = FormState[self.form_class](
                    form=form,
                    progress=state_data.get('progress', 0),
                    prev_question=state_data.get('prev_question', ''),
                    prev_answer=state_data.get('prev_answer', ''),
                    feedback=state_data.get('feedback', ''),
                    confidence=state_data.get('confidence', 0.0),
                    next_question=state_data.get('next_question', ''),
                    next_question_explanation=state_data.get(
                        'next_question_explanation', ''
                    )
                )
                self._log("Restored session state")
                self._state_dirty = False
                return
            except Exception as e:
                self._log(f"Error restoring session: {e}", level="warning")

        # Initialize new state if could not restore
        self.current_state = FormState[self.form_class](form=self.form_class())
        self._log("Initialized new session state")
        self._state_dirty = True  # Mark as dirty to save initial state

    @contextmanager
    def temporary_session(self, session_id: str):
        """Context manager for temporarily switching to another session

        Args:
            session_id: The session ID to temporarily switch to
        """
        with self.db_manager.temporary_session(session_id):
            old_state = self.current_state
            old_dirty = self._state_dirty

            # Restore state from the temporary session
            self._restore_latest_state_from_db()

            try:
                yield
            finally:
                # Restore original state
                self.current_state = old_state
                self._state_dirty = old_dirty

    def _restore_session_state(self, session_id: str) -> bool:
        """Restore session state from a specific session ID

        Args:
            session_id: Session ID to restore from

        Returns:
            True if session was restored, False otherwise
        """
        # Update session ID and reset session cache
        self.db_manager.session_id = session_id
        self.db_manager._session = None

        # Clear client pool when changing sessions
        self._client_pool = {}

        # Try to restore from the database
        result = self._restore_latest_state_from_db()
        return result is not None

    @property
    def session_id(self) -> str:
        """Get the current session ID"""
        return self.db_manager.session_id or ""

    def get_session_id(self) -> str:
        """Get or create a session ID using the form's properties

        Returns:
            Session ID string
        """
        # Check if we already have a session ID
        if self.db_manager.session_id:
            return self.db_manager.session_id

        # Create a session using class properties
        session = self.db_manager.get_or_create_session(
            user_id=self.user_id,
            client_id=self.client_id,
            form_class=self.form_class.__name__
        )

        return session.id

    def _set_session(self, session_id: str = None) -> bool:
        """Set the active session and restore its latest state

        This method:
        1. Sets the session ID in the database manager
        2. Restores the most recent state for this session

        Args:
            session_id: The session ID to set

        Returns:
            True if session was set and state restored

        Raises:
            ValueError: If session ID is invalid or session not found
            RuntimeError: If error restoring session state
        """
        if not session_id:
            raise ValueError("Cannot set empty session ID")

        # Store old session ID in case restoration fails
        old_session_id = self.db_manager.session_id

        try:
            # Set new session ID
            self.db_manager.session_id = session_id
            self.db_manager._session = None

            # Clear client pool when changing sessions
            self._client_pool = {}

            # Try to get the session
            session = self.db_manager.get_or_create_session(session_id)
            if not session:
                # Restore old session ID
                self.db_manager.session_id = old_session_id
                self.db_manager._session = None
                raise ValueError(f"Session not found: {session_id}")

            # Try to restore state from this session
            self._restore_latest_state_from_db()
            return True

        except Exception as e:
            # Restore old session ID on any error
            self.db_manager.session_id = old_session_id
            self.db_manager._session = None
            self._log(f"Error setting session: {e}", level="error")
            raise RuntimeError(f"Error setting session: {e}")

    def get_session_history(self, session_id: str, limit: int = None) -> list:
        """Get all historical states for a session

        Args:
            session_id: Optional session ID.
            limit: Maximum number of states to return (newest first)

        Returns:
            List of state dictionaries in chronological order
        """
        with self.temporary_session(session_id):
            return self.db_manager.get_state_history(limit=limit)

    def refresh_current_state(self) -> bool:
        """Refresh the current state from the database to ensure it's the latest version

        Returns:
            True if state was refreshed, False if no state exists
        """
        if not self.db_manager.session_id:
            self._log("No session ID to refresh state from", level="warning")
            return False

        previous_state = self.current_state.model_dump() if hasattr(self, 'current_state') else {}

        # Always use cache to reduce database reads
        latest_state = self.db_manager.get_latest_state(use_cache=True)
        if not latest_state:
            self._log("No state found in database to refresh from", level="warning")
            return False

        try:
            # Update the current state with the latest data from the database
            form_data = latest_state.get('form', {})
            form = self.form_class(**form_data)

            self.current_state = FormState[self.form_class](
                form=form,
                progress=latest_state.get('progress', 0),
                prev_question=latest_state.get('prev_question', ''),
                prev_answer=latest_state.get('prev_answer', ''),
                feedback=latest_state.get('feedback', ''),
                confidence=latest_state.get('confidence', 0.0),
                next_question=latest_state.get('next_question', ''),
                next_question_explanation=latest_state.get(
                    'next_question_explanation', ''
                )
            )

            # Check if state has actually changed
            current_state = self.current_state.model_dump()
            if previous_state != current_state:
                self._log("Refreshed current state from database (state changed)")
            else:
                self._log("State refreshed but unchanged", level="debug")

            return True
        except Exception as e:
            self._log(f"Error refreshing state: {e}", level="error")
            return False

    def get_next_question(self, session_id: str = None) -> str:
        """Get the next question for a session

        This restores the session if needed and returns the stored next question from
        the most recent state.

        Args:
            session_id: Optional session ID. If None, uses current session

        Returns:
            The next question to ask in the conversation
        """
        # If session_id is provided and different from current, set it
        if session_id and session_id != self.db_manager.session_id:
            self._set_session(session_id)
        else:
            # Use a faster cached state check
            self.refresh_current_state()

        # Return the next question from the current state
        return self.current_state.next_question

    def save_current_state(self, session_id: str = None, force: bool = False):
        """Save current state to the database if it has changed

        Args:
            session_id: Optional session ID to save to
            force: Force save even if state hasn't changed
        """
        if not hasattr(self, 'current_state') or not self.current_state:
            self._log("No current_state to save", level="warning")
            return

        # Only save if state is dirty or forced
        if not self._state_dirty and not force:
            self._log("State unchanged, skipping save", level="debug")
            return

        # If session_id is provided, temporarily switch to that session
        if session_id and session_id != self.db_manager.session_id:
            with self.temporary_session(session_id):
                self._do_save_state()
        else:
            self._do_save_state()

        # Mark as clean after saving
        self._state_dirty = False

    def _do_save_state(self):
        """Internal method to save state to current session"""
        # Convert state to dict and save
        state_dict = self.current_state.model_dump()
        save_result = self.db_manager.save_state(
            state_dict,
            self.current_state.progress,
            user_id=self.user_id,
            client_id=self.client_id,
            form_class=self.form_class.__name__
        )

        if save_result:
            self._log("Successfully saved state", level="debug")
        else:
            self._log("Failed to save state", level="error")

    def _validate_tools(self) -> None:
        """Validate tools configuration"""
        if not self._tools:
            raise ValueError(
                "Tools list is empty. Register at least one tool."
            )

        """Print initialization information"""
        self._log("\n🛠️ Initialized tools:")
        for tool in self.tools:
            self._log(f"  - {tool.__name__}: {tool.__doc__ or 'No description'}")

    @property
    def tools(self) -> List[Callable]:
        """Get registered tools"""
        return self._tools

    @tools.setter
    def tools(self, tools: List[Callable]) -> None:
        """Register tools with docstring validation"""
        if not tools:
            raise ValueError(
                "Cannot register empty tools list. Register at least one tool."
            )

        for tool in tools:
            if not tool.__doc__:
                raise ValueError(
                    f"Tool {tool.__name__} must have a docstring"
                )

        # Ensure process_form is always included
        if self.process_form not in tools:
            tools = [self.process_form] + tools

        self._tools = tools

    def configure_test_agent(
        self,
        prompt: str,
        client: PydanticAIClient,
    ) -> None:
        """Configure test agent with custom prompt and client"""
        self.test_agent_client = client
        self.test_agent_prompt = prompt

    def _get_base_client(self, temperature: float = 0.1):
        """Get base AI client with default settings"""
        client_key = f'base_{temperature}'
        if client_key in self._client_pool:
            return self._client_pool[client_key]

        client = PydanticAIClient(
            model_name="openai/gpt-4o-mini-2024-07-18",
            client_id=f'{self.client_id}.orchestrator',
            user_id=self.user_id,
            verbose=self.verbose_clients,
            retries=2,
            online=False,
            max_budget=self.max_budget,
            model_settings=ModelSettings(temperature=temperature)
        )

        self._client_pool[client_key] = client
        return client

    def _get_tool_client(
        self,
        model_name: str = "openai/gpt-4o-mini-2024-07-18",
        temperature: float = 0.1
    ):
        """Get client for specific tool execution with client pooling"""
        caller_name = inspect.stack()[1].function
        client_key = f'{model_name}_{caller_name}_{temperature}'

        if client_key in self._client_pool:
            return self._client_pool[client_key]

        client = PydanticAIClient(
            model_name=model_name,
            client_id=f'{self.client_id}.{caller_name}',
            user_id=self.user_id,
            verbose=self.verbose_clients,
            max_budget=self.max_budget,
            model_settings=ModelSettings(temperature=temperature)
        )

        self._client_pool[client_key] = client
        return client

    def _get_test_agent_client(
            self,
            model_name: str = "openai/gpt-4o-mini-2024-07-18",
            temperature: float = 0.7,
            max_tokens: int = 1000,
    ):
        """Get test agent client with client pooling"""
        client_key = f'test_agent_{model_name}_{temperature}'

        if client_key in self._client_pool:
            return self._client_pool[client_key]

        client = PydanticAIClient(
            model_name=model_name,
            client_id=f'{self.client_id}.test_agent',
            user_id=self.user_id,
            verbose=self.verbose_clients,
            max_budget=self.max_budget,
            model_settings=ModelSettings(
                temperature=temperature,
                max_tokens=max_tokens
            )
        )

        self._client_pool[client_key] = client
        return client

    def set_verbose(self):
        """Set verbose mode and update logger level"""
        if self.verbose:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.WARNING)
        if self.client_agent:
            self.client_agent.verbose = self.verbose

    def _log(self, message: str, *args, level: str = "info", **kwargs) -> None:
        """Internal logging method with verbose check"""
        if level == "debug" and not self.verbose:
            return

        if not self.verbose and level != "error" and level != "warning":
            return

        log_func = getattr(logger, level)
        log_func(message, *args, **kwargs)

    def get_test_agent_response(self) -> str:
        """Get response from test agent using configured client and prompt"""
        if not self.test_agent_client or not self.test_agent_prompt:
            raise ValueError(
                "Test agent not configured. Call configure_test_agent first."
            )

        self._log("Getting test agent response for question")

        # Add base prompt
        self.test_agent_client.message_handler.add_message_system(
            self.test_agent_prompt + """

            TASK:
            - Answer the question based on the current state and the question
            """
        )

        # Add context
        self.test_agent_client.message_handler.add_message_block(
            "QUESTION",
            self.current_state.next_question
        )

        self.test_agent_client.message_handler.add_message_block(
            "CURRENT_STATE",
            self.current_state.model_dump(),
        )

        # Generate response
        result: TestAgentResponse = self.test_agent_client.generate(
            result_type=TestAgentResponse
        )

        self._log("Test agent response: %s", result.response)

        return result.response

    def process_form_batch(self, messages: List[str]) -> List[FormState]:
        """Process multiple messages in a batch to reduce database writes

        Args:
            messages: List of messages to process

        Returns:
            List of form states after processing each message
        """
        results = []

        # Process each message but only save at the end
        for message in messages:
            result = self._process_form_internal(message, save=False)
            results.append(result)

        # Save the final state
        self.save_current_state()

        return results

    def _process_form_internal(self, message: str, save: bool = True) -> FormState:
        """Internal implementation of form processing

        Args:
            message: The message to process
            save: Whether to save state after processing

        Returns:
            Updated form state
        """
        self._log("Processing message: %s", message)

        client = self._get_tool_client()

        # Prepare prompt
        client.message_handler.add_message_system(
            """You are a helpful assistant that processes information.

            TASK:
            1. Review the [USER_MESSAGE]
            2. Update the form fields based on the message content
            3. Preserve existing information, only append new details
            4. Focus on the form fields to update but check others if relevant
            5. Generate a relevant follow-up question based on the user's response
            6. Set this as the next_question field
            7. The next_question should follow up on what the user shared
            8. Return the updated form state
            9. Pay attention to the [CUSTOM_RULES]
            """
        )

        # Add form class definition
        form_fields = []
        for field_name, field in self.form_class.__annotations__.items():
            field_type = field.__name__ if hasattr(field, "__name__") else str(field)
            field_obj = self.form_class.model_fields.get(field_name, {})

            description = ""
            if hasattr(field_obj, "description") and field_obj.description:
                description = field_obj.description

            form_fields.append(f"- {field_name}: {field_type} - {description}")

        client.message_handler.add_message_block(
            "FORM_STRUCTURE",
            "Form fields:\n" + "\n".join(form_fields)
        )

        # Add current form state
        client.message_handler.add_message_block(
            "CURRENT_STATE",
            self.current_state.model_dump(),
        )

        # Add custom rules for form processing
        client.message_handler.add_message_block(
            "CUSTOM_RULES",
            """
            - Keep all existing information unless directly contradicted
            - If fields are empty and the message doesn't provide information, leave them empty
            - Incrementally build the form based on user input
            - The progress field should reflect overall form completion (0-100)
            """
        )

        # Add user message
        client.message_handler.add_message_user(message)

        # Process and get updated state
        result = client.generate(result_type=FormState[self.form_class])

        # Store history of Q&A
        result.prev_question = self.current_state.next_question
        result.prev_answer = message

        # Update current state
        self.current_state = result
        self._state_dirty = True

        # Save state to database if requested
        if save:
            self.save_current_state()

        return self.current_state

    def process_form(self, message: str) -> FormState:
        """Process and update form info

        Always ensures the latest state is loaded before processing.

        Args:
            message: User message to process

        Returns:
            Updated form state
        """
        # Always refresh the state first
        self.refresh_current_state()

        # Process using the internal method
        return self._process_form_internal(message)

    def determine_action(self, message: str, session_id: str = None):
        """Orchestrate which action should be taken based on user message

        Args:
            message: User message to process
            session_id: Optional session ID. If provided, will switch to that session
        """
        # If session_id is provided, switch to that session
        if session_id and session_id != self.db_manager.session_id:
            self._set_session(session_id)
        else:
            # Always refresh to ensure we have the latest state
            self.refresh_current_state()

        self._log("Determining action for message...")

        class OrchestratorAction(BaseModel):
            tool_name: str = Field(description="Name of tool to execute")
            confidence: float = Field(
                ge=0,
                le=1,
                description="Confidence in selection"
            )
            reasoning: str = Field(description="Why this tool was selected")

        client = self._get_base_client()

        # Create prompt with tools and current state
        client.message_handler.add_message_system(
            """You are an orchestrator that decides which action to take next.

            TASK:
            1. Review the [USER_MESSAGE]
            2. Decide which tool should be used to process the message
            3. Return the selected tool name, confidence, and reasoning

            Select one of these tools based on the message content and form state:
            """
        )

        # Add tools
        tools_prompt = []
        for tool in self.tools:
            name = tool.__name__
            description = tool.__doc__ or "No description"
            tools_prompt.append(f"- {name}: {description}")

        client.message_handler.add_message_block(
            "AVAILABLE_TOOLS",
            "\n".join(tools_prompt)
        )

        # Add form state
        client.message_handler.add_message_block(
            "CURRENT_STATE",
            self.current_state.model_dump(),
        )

        # Add user message
        client.message_handler.add_message_user(message)

        # Get recommendation
        action: OrchestratorAction = client.generate(
            result_type=OrchestratorAction
        )

        self._log(f"Selected action: {action.tool_name} (confidence: {action.confidence})")
        self._log(f"Reasoning: {action.reasoning}")

        # Execute the selected tool
        tool_map = {tool.__name__: tool for tool in self.tools}
        if action.tool_name in tool_map:
            selected_tool = tool_map[action.tool_name]
            state = selected_tool(message)

            # Mark state as dirty after tool execution
            self._state_dirty = True

            # Save updated state after tool execution
            self.save_current_state()

            return state
        else:
            self._log(f"Tool {action.tool_name} not found", level="error")
            # Default to process_form if tool not found
            return self.process_form(message)

    def run_test_dialog(self, session_id: str = None):
        """Run a test dialog between agent and test agent

        Args:
            session_id: Optional session ID. If provided, will switch to that session
        """
        # If session_id is provided, switch to that session
        if session_id and session_id != self.db_manager.session_id:
            self._set_session(session_id)
        else:
            # Always refresh to ensure we have the latest state
            self.refresh_current_state()

        # Check that test agent is configured
        if not self.test_agent_client or not self.test_agent_prompt:
            raise ValueError(
                "Test agent not configured. Call configure_test_agent first."
            )

        # Make sure there's a next question
        if not self.current_state.next_question:
            self._log("No next question available", level="warning")
            return

        # Get response from test agent
        response = self.get_test_agent_response()
        self._log(f"Test agent response: {response}")

        # Process response
        updated_state = self.process_form(response)

        # Log updated state
        self._log(f"Updated state progress: {updated_state.progress}%")
        if updated_state.next_question:
            self._log(f"Next question: {updated_state.next_question}")

        return updated_state
