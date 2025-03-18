from typing import List, Callable, Optional, TypeVar, Generic
from pydantic import BaseModel, Field, ConfigDict
from src.pydantic2 import PydanticAIClient, ModelSettings
import logging
import inspect
from abc import ABC

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
    ):
        self.user_id = user_id
        self.client_id = client_id
        self.max_budget = max_budget
        self.verbose = verbose
        self.verbose_clients = verbose_clients
        self.form_class = form_class

        # Initialize state with form class
        self.current_state = FormState[form_class](form=form_class())

        # Initialize tools list with process_form by default
        self._tools: List[Callable] = []

        # Set up base client
        self.client_agent = client_agent or self._get_base_client()

        # Initialize test agent (to be configured by child class)
        self.test_agent_client = None
        self.test_agent_prompt = None

        # Set logger level
        self.set_verbose()

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
        return PydanticAIClient(
            model_name="openai/gpt-4o-mini-2024-07-18",
            client_id=f'{self.client_id}.orchestrator',
            user_id=self.user_id,
            verbose=self.verbose_clients,
            retries=2,
            online=False,
            max_budget=self.max_budget,
            model_settings=ModelSettings(temperature=temperature)
        )

    def _get_tool_client(self, model_name: str = "openai/gpt-4o-mini-2024-07-18", temperature: float = 0.1):
        """Get client for specific tool execution"""
        caller_name = inspect.stack()[1].function
        return PydanticAIClient(
            model_name="openai/gpt-4o-mini-2024-07-18",
            client_id=f'{self.client_id}.{caller_name}',
            user_id=self.user_id,
            verbose=self.verbose_clients,
            max_budget=self.max_budget,
            model_settings=ModelSettings(temperature=temperature)
        )

    def _get_test_agent_client(
            self,
            model_name: str = "openai/gpt-4o-mini-2024-07-18",
            temperature: float = 0.7,
            max_tokens: int = 1000,
    ):
        """Get test agent client"""
        return PydanticAIClient(
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
        if not self.verbose and level != "error":
            return

        log_func = getattr(logger, level)
        log_func(message, *args, **kwargs)

    def get_test_agent_response(self) -> str:
        """Get response from test agent using configured client and prompt"""
        if not self.test_agent_client or not self.test_agent_prompt:
            raise ValueError(
                "Test agent not configured. Call configure_test_agent first."
            )

        self._log("Getting test agent response for question: %s",
                  self.current_state.next_question)

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
            self.current_state.model_dump()
        )

        # Generate response
        result: TestAgentResponse = self.test_agent_client.generate(
            result_type=TestAgentResponse
        )

        self._log("Test agent response: %s", result.response)

        return result.response

    def process_form(self, message: str) -> FormState:
        """Process and update form info - base implementation"""
        self._log("Processing info with message: %s", message)

        client = self._get_tool_client()

        client.message_handler.add_message_system(
            """You are a helpful assistant that processes startup information.

            TASK:
            1. Review the [USER_MESSAGE]
            2. Update the form fields based on the message content
            3. Preserve existing information, only append new details
            4. Focus on the form fields to update but check others if relevant
            5. Return the updated form state

            PROGRESS:
            - Always update the progress value
            - Never decrease the progress value
            - Progress reflects the percentage of form fields that have been updated

            FEEDBACK:
            - Provide a feedback on the [USER_MESSAGE] related to [PREV_QUESTION]
            - Address the user's message directly
            - Be concise and to the point

            NEXT_QUESTION:
            - Ask a question to the user based on missing information in [CURRENT_STATE]
            """
        )

        # Keywords for each category
        form_dump = self.current_state.form.model_dump()
        form_fields = self.client_agent.message_handler.to_flat_yaml(form_dump)

        # Add current form state and available fields
        current_form = self.current_state.form.model_dump()

        client.message_handler.add_message_block(
            "CURRENT_STATE",
            {
                "current form": current_form,
                "form fields to update": form_fields
            }
        )

        client.message_handler.add_message_block(
            "USER_MESSAGE",
            message
        )

        try:
            new_state: FormState = client.generate(result_type=FormState[self.form_class])

            self._log("Generated new state with progress: %d%%", new_state.progress)

            # Add detailed form state logging
            self._log("Current form state:")
            self._log("Form fields:")
            for field, value in new_state.form.model_dump().items():
                self._log("  %s: %s", field, value or "(empty)")
            self._log("Progress: %d%%", new_state.progress)
            self._log("Feedback: %s", new_state.feedback)
            self._log("Next question: %s", new_state.next_question)
            self._log("Confidence: %.2f", new_state.confidence or 0.0)

            # Update state preserving history
            updated_state = FormState(
                form=new_state.form,
                progress=new_state.progress,
                feedback=new_state.feedback,
                next_question=new_state.next_question,
                next_question_explanation=new_state.next_question_explanation,
                prev_question=self.current_state.next_question,
                prev_answer=message,
                confidence=new_state.confidence or 0.8
            )

            self.current_state = updated_state
            return self.current_state

        except Exception as e:
            error_msg = f"Error processing information: {str(e)}"
            self._log(error_msg, level="error")
            self.current_state.feedback = error_msg
            return self.current_state

    def determine_action(self, message: str):
        """Determine and execute next action based on message and form state"""
        # Validate tools configuration
        self._validate_tools()

        self._log("Starting determine_action with message: %s", message)

        try:
            self.client_agent.message_handler.add_message_system(
                f"""
                You are an orchestrator that determines the next action.

                TASK:
                - Determine the next action based on the [USER_MESSAGE]
                - Use description of [TOOLS_INFO] to determine the next action

                IMPORTANT:
                - Current progress is: {self.current_state.progress}%
                - Try to define the next action based on the progress
                """
            )

            self.client_agent.message_handler.add_message_block(
                "USER_MESSAGE",
                message
            )

            tools_info = [
                {
                    "desc": tool.__doc__,
                    "func": tool.__name__
                }
                for tool in self.tools
            ]

            self._log("Available tools: %s", [t["func"] for t in tools_info])

            self.client_agent.message_handler.add_message_block(
                "TOOLS_INFO",
                tools_info
            )

            class OrchestratorAction(BaseModel):
                tool_name: str = Field(description="Name of tool to execute")
                confidence: float = Field(
                    ge=0,
                    le=1,
                    description="Confidence in selection"
                )
                reasoning: str = Field(description="Why this tool was selected")

            try:
                orchestrator_result: OrchestratorAction = self.client_agent.generate(
                    result_type=OrchestratorAction
                )

                tool_name = orchestrator_result.tool_name

                self._log(
                    "Orchestrator selected tool: %s (confidence: %.2f)",
                    tool_name,
                    orchestrator_result.confidence
                )
                self._log("Reasoning: %s", orchestrator_result.reasoning)

                call_tool = getattr(self, tool_name)
                self._log("Executing tool: %s", tool_name)
                result: BaseModel = call_tool(message)

                self._log("Tool result: %s", result.model_dump_json(indent=2))
                return result

            except Exception as e:
                self._log("Error in orchestrator: %s", str(e), level="error")
                # Default to process_form if orchestrator fails
                self._log("Falling back to process_form", level="warning")
                return self.process_form(message)

        except Exception as e:
            self._log("Critical error in determine_action: %s", str(e), level="error")
            raise e

    def run_test_dialog(self):
        """Run dialog between test agent and form processing"""
        # Validate tools configuration before starting dialog
        self._validate_tools()

        self._log("Starting dialog with registered tools: %s",
                  [t.__name__ for t in self.tools])

        print("\n🤖 Starting Form Dialog...")

        while True:
            state = self.current_state

            # Get test agent response
            message = self.get_test_agent_response()

            self._log("Dialog state - Progress: %d%%, Confidence: %.2f",
                      state.progress, state.confidence)

            self._log("\n💬 Processing new information...")
            self._log(f"Response: {message}\n")
            self._log(f"Feedback: {state.feedback}")
            self._log(f"Progress: {state.progress}%")
            self._log(f"Next question: {state.next_question}")
            self._log(f"Confidence: {state.confidence:.2%}")

            # Process message
            self.determine_action(message)

            # Check if form is complete
            if state.progress >= 100:
                self._log("Dialog complete with final progress: %d%%", state.progress)

                break

        self._log("\n✅ Dialog Complete!")
