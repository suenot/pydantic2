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
    user_language: str = Field(default="", description="User's language (iso639-1)")

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

        # If this is a new session (no history), save initial state
        history = self.db_manager.get_state_history()
        # if not history:
        #     self._log("New session detected, saving initial state")
        #     self.current_state.next_question = "Tell me about your startup idea."
        #     self._state_dirty = True
        #     self.save_current_state()
        #     history = self.db_manager.get_state_history()

        # Get state history for logging
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
                    ),
                    user_language=state_data.get('user_language', '')
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

    def process_form(
        self,
        message: str,
        session_id: str = None
    ) -> FormState:
        """Process and update form info - base implementation"""
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

        self._log("Processing info with message: %s", message)

        client = self._get_tool_client()

        client.message_handler.add_message_system(
            """You are a helpful assistant that processes information.

            IMPORTANT:
            - Define user's language from the message and set it to the 'user_language' field
            - Ask in [USER_LANGUAGE] language
            - Pay attention to the [CUSTOM_RULES]

            TASK:
            1. Review the [USER_MESSAGE]
            2. Update the form fields based on the message content
            3. Preserve existing information, only append new details
            4. Focus on the form fields to update but check others if relevant
            5. Generate a relevant follow-up question based specifically on the user's response.
            6. Set this as the next_question field
            7. The next_question should follow up on what the user just shared, not be generic
            8. Return the updated form state
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

        # Save state to database
        self.save_current_state()

        return self.current_state

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

    def _process_message(self, message: str) -> str:
        """Internal method to process a form message and get a response"""
        self._log(f"Processing message: {message}")

        # Process using test agent
        result = self._process_with_test_agent(message)

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

    def _process_with_test_agent(self, message: str) -> str:
        """Internal method to process a form message using test agent"""
        self._log("Processing message with test agent")

        # Get response from test agent
        response = self.get_test_agent_response()
        self._log(f"Test agent response: {response}")

        return response

    def get_current_progress(self) -> int:
        """Get the current progress of the form

        Returns:
            Current progress value (0-100)
        """
        if not hasattr(self, 'current_state'):
            return 0
        return self.current_state.progress
