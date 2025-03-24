from typing import List, Callable, Optional, TypeVar, Generic
from pydantic import BaseModel, Field, ConfigDict
from pydantic2 import PydanticAIClient, ModelSettings
import logging
import inspect
from abc import ABC
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
        session_id: str = None,
    ):
        self.user_id = user_id
        self.client_id = client_id
        self.max_budget = max_budget
        self.verbose = verbose
        self.verbose_clients = verbose_clients
        self.form_class = form_class
        self._state_dirty = False

        # Client pool to reduce instantiation overhead
        self._client_pool = {}

        # Initialize DB manager with session_id
        self.db_manager = SessionDBManager(session_id=session_id, verbose=verbose)

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

        # Initialize or restore session state
        self._initialize_session()

    def _initialize_session(self):
        """Initialize or restore session state"""
        # Get or create session
        session = self.db_manager.get_or_create_session(
            user_id=self.user_id,
            client_id=self.client_id,
            form_class=self.form_class.__name__
        )

        if not session:
            self._log("Failed to initialize session", "error")
            return

        # Try to get the latest state
        self._restore_latest_state_from_db()

        # Get state history for logging
        history = self.db_manager.get_state_history()
        self._log(f"States in history: {len(history)}")
        for i, state in enumerate(history, 1):
            self._log(f"State {i}:")
            self._log(f"  Progress: {state.get('state', {}).get('progress', 'None')}%")
            self._log(f"  Question: {state.get('state', {}).get('prev_question', 'None')}")
            self._log(f"  Answer: {state.get('state', {}).get('prev_answer', 'None')}")
            self._log(f"  Timestamp: {state.get('timestamp', 'None')}")

    def _restore_latest_state_from_db(self):
        """Restore latest state from database with error handling"""
        state_data = self.db_manager.get_latest_state()

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
        self._state_dirty = True

        # Get state history for logging
        history = self.db_manager.get_state_history()
        self._log(f"States in history: {len(history)}")
        for i, state in enumerate(history, 1):
            self._log(f"State {i}:")
            self._log(f"  Progress: {state.get('state', {}).get('progress', 'None')}%")
            self._log(f"  Question: {state.get('state', {}).get('prev_question', 'None')}")
            self._log(f"  Answer: {state.get('state', {}).get('prev_answer', 'None')}")
            self._log(f"  Timestamp: {state.get('timestamp', 'None')}")

    def process_form(
        self,
        message: str,
        session_id: str = None
    ) -> FormState:
        """Process a single form message

        Args:
            message: User's message to process
            session_id: Optional session ID to use. If None, uses current session.

        Returns:
            Updated form state after processing
        """
        # Ensure we have a session
        if session_id:
            session = self.db_manager.get_or_create_session(session_id=session_id)
            if not session:
                raise ValueError(f"Session not found: {session_id}")
        elif not self.db_manager.session_id:
            session = self.db_manager.create_session(
                user_id=self.user_id,
                client_id=self.client_id,
                form_class=self.form_class.__name__
            )

        # Process the message
        result = self._process_form_internal(message)

        # Get state history for logging
        history = self.db_manager.get_state_history()
        self._log(f"States in history: {len(history)}")
        for i, state in enumerate(history, 1):
            self._log(f"State {i}:")
            self._log(f"  Progress: {state.get('state', {}).get('progress', 'None')}%")
            self._log(f"  Question: {state.get('state', {}).get('prev_question', 'None')}")
            self._log(f"  Answer: {state.get('state', {}).get('prev_answer', 'None')}")
            self._log(f"  Timestamp: {state.get('timestamp', 'None')}")

        return result

    def save_current_state(self):
        """Save current state to the database if it has changed"""
        if not hasattr(self, 'current_state') or not self.current_state:
            self._log("No current_state to save", level="warning")
            return

        if not self._state_dirty:
            self._log("State unchanged, skipping save", level="debug")
            return

        # Convert state to dict and save
        state_dict = self.current_state.model_dump()
        if self.db_manager.save_state(state_dict):
            self._state_dirty = False
            self._log("Successfully saved state")
        else:
            self._log("Failed to save state", level="error")

    def get_session_history(self, session_id: str = None) -> list:
        """Get all historical states for a session

        Args:
            session_id: Optional session ID. If None, uses current session

        Returns:
            List of state dictionaries in chronological order
        """
        if session_id:
            self.db_manager.set_session(session_id)
        return self.db_manager.get_state_history(session_id)

    def _process_form_internal(self, message: str) -> FormState:
        """Internal method to process a form message

        Args:
            message: User's message to process

        Returns:
            Updated form state
        """
        self._log(f"Processing message: {message}")

        # Update form with new data
        self.current_state.prev_question = self.current_state.next_question
        self.current_state.prev_answer = message

        # Process using test agent
        result = self._process_with_test_agent(message)

        # Get state history for logging
        history = self.db_manager.get_state_history()
        self._log(f"States in history: {len(history)}")
        for i, state in enumerate(history, 1):
            self._log(f"State {i}:")
            self._log(f"  Progress: {state.get('state', {}).get('progress', 'None')}%")
            self._log(f"  Question: {state.get('state', {}).get('prev_question', 'None')}")
            self._log(f"  Answer: {state.get('state', {}).get('prev_answer', 'None')}")
            self._log(f"  Timestamp: {state.get('timestamp', 'None')}")

        return result

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

    def _process_with_test_agent(self, message: str) -> FormState:
        """Internal method to process a form message using test agent"""
        self._log("Processing message with test agent")

        # Get response from test agent
        response = self.get_test_agent_response()
        self._log(f"Test agent response: {response}")

        # Update form data based on the message
        form_data = self.current_state.form.model_dump()

        # Map messages to form fields with more specific conditions
        if "food delivery app" in message.lower() or "startup idea" in message.lower():
            form_data["idea_desc"] = message
            self._log(f"Updated idea_desc: {message}")
        elif "target market" in message.lower() or "urban professionals" in message.lower():
            form_data["target_mkt"] = message
            self._log(f"Updated target_mkt: {message}")
        elif "revenue" in message.lower() or "commission" in message.lower() or "fee" in message.lower():
            form_data["biz_model"] = message
            self._log(f"Updated biz_model: {message}")
        elif "team" in message.lower() or "developer" in message.lower() or "experienced" in message.lower():
            form_data["team_info"] = message
            self._log(f"Updated team_info: {message}")

        # Create a new state with updated form data
        new_state = FormState[self.form_class](
            form=self.form_class(**form_data),
            progress=self.current_state.progress,
            prev_question=self.current_state.next_question,
            prev_answer=message,
            feedback="",
            confidence=0.0,
            next_question=response,
            next_question_explanation=""
        )

        # Update progress based on form completion
        filled_fields = sum(1 for value in form_data.values() if value)
        total_fields = len(form_data)
        new_state.progress = min(100, int((filled_fields / total_fields) * 100))

        self._log(f"Updated progress: {new_state.progress}%")
        self._log(f"Form data: {form_data}")

        # Update current state and mark as dirty
        self.current_state = new_state
        self._state_dirty = True

        # Save state to database
        self.save_current_state()

        return new_state

    def get_current_progress(self) -> int:
        """Get the current progress of the form

        Returns:
            Current progress value (0-100)
        """
        if not hasattr(self, 'current_state'):
            return 0
        return self.current_state.progress
