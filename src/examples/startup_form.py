from typing import List, Optional, Any
import yaml
import re
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, ConfigDict
from src.pydantic2 import PydanticAIClient, ModelSettings
from dotenv import load_dotenv
import random
import time
import logging
import inspect

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class StartupForm(BaseModel):
    """Structure for storing startup form data"""
    idea_desc: str = Field(default="", description="Description of startup idea")
    target_mkt: str = Field(default="", description="Target market info")
    biz_model: str = Field(default="", description="Business model info")
    team_info: str = Field(default="", description="Team background")


class FormState(BaseModel):
    """State for tracking form progress and processing"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Form data and progress
    form: StartupForm = Field(default_factory=StartupForm)
    progress: int = Field(default=0, description="Form progress (0-100)")
    last_msg: str = Field(
        default="Initial startup form state",
        description="Last processed message"
    )
    prev_question: str = Field(
        default="",
        description="Previous question asked"
    )
    prev_answer: str = Field(
        default="",
        description="Previous answer received"
    )

    # Processing state
    feedback: str = Field(default="", description="Feedback on provided information to the user")
    confidence: float = Field(
        default=0.0,
        ge=0, le=1,
        description="Confidence in the current state"
    )
    next_question: str = Field(
        default="",
        description="Next question to ask the user"
    )
    next_question_explanation: str = Field(
        default="",
        description="Explanation of the next question to ask the user, with example based on the known information in [CURRENT_STATE]"
    )


class StartupFormResponse(BaseModel):
    """Response format for startup form analysis."""
    feedback: str = Field(description="Detailed feedback on the startup idea")
    score: float = Field(ge=0, le=10, description="Overall score of the startup idea")
    strengths: List[str] = Field(description="Key strengths of the startup idea")
    weaknesses: List[str] = Field(description="Areas for improvement")
    next_steps: List[str] = Field(description="Recommended next steps")
    market_potential: Optional[float] = Field(
        ge=0, le=10,
        description="Market potential score"
    )


# First, add the orchestrator model
class OrchestratorAction(BaseModel):
    """Model for orchestrator decisions"""
    tool_name: str = Field(
        description=(
            "Name of the tool to execute based on the [TOOLS_INFO] message"
        )
    )
    confidence: float = Field(ge=0, le=1, description="Confidence in tool selection")
    reasoning: str = Field(description="Why this tool was selected")


# Then update the orchestrator class
class BaseStartupOrchestrator:
    """Base orchestrator for processing startup information"""

    def __init__(self):
        # Orchestrator's own client for tool selection
        self.max_budget = 10
        self.client_id = "startup"
        self.user_id = "startup_user"
        self.verbose = False

        self.client_agent = PydanticAIClient(
            model_name="openai/gpt-4o-mini-2024-07-18",
            client_id=f'{self.client_id}_orchestrator',
            user_id=self.user_id,
            verbose=self.verbose,  # Pass verbose to client
            retries=2,
            online=False,
            max_budget=self.max_budget,
            model_settings=ModelSettings(
                temperature=0.1,
            )
        )

        # Store current form state
        self.current_state: FormState = FormState()

        # Define available tools with function names
        self.tools = [self.process_info, self.analyze_startup]

        # Set logger level based on verbose
        self.set_verbose()

    def set_verbose(self):
        """Set verbose mode and update logger level"""
        if self.verbose:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.WARNING)

        # Update client verbose settings
        if self.client_agent:
            self.client_agent.verbose = self.verbose

    def _get_client(self, temperature: float = 0.1):

        # get caller name
        caller_name = inspect.stack()[1].function
        return PydanticAIClient(
            model_name="openai/gpt-4o-mini-2024-07-18",
            client_id=f'{self.client_id}_{caller_name}',
            user_id=self.user_id,
            verbose=False,
            model_settings=ModelSettings(
                temperature=temperature,
            )
        )

    def process_info(self, message: str, form_state: FormState) -> FormState:
        """
        Process and update form info. Use when progress < 100%
        """
        logger.info("Starting process_info with message: %s", message)

        try:
            # Create unique client ID for each request
            client = self._get_client(
                temperature=0.1,
            )

            # Keywords for each category
            form_fields = self.current_state.form.model_dump().keys()
            # Send instructions to AI
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
                """
            )

            # Send current form state and category
            client.message_handler.add_message_block(
                "CURRENT_STATE",
                {
                    "current form": self.current_state.form.model_dump(),
                    "form fields to update": form_fields
                }
            )

            # Send the user message
            client.message_handler.add_message_block(
                "USER_MESSAGE",
                message
            )

            # Add previous question and answer
            client.message_handler.add_message_block(
                "PREV_QUESTION",
                self.current_state.prev_question
            )

            try:
                # Get updated state from AI
                new_state: FormState = client.generate(result_type=FormState)

                # Create updated state preserving history
                updated_state = FormState(
                    form=new_state.form,
                    progress=new_state.progress,
                    feedback=new_state.feedback,
                    next_question=new_state.next_question,
                    next_question_explanation=new_state.next_question_explanation,
                    prev_question=self.current_state.next_question,
                    prev_answer=message,
                    last_msg=message,
                    confidence=new_state.confidence or 0.8
                )

                # Update current state
                self.current_state = updated_state

                print_form_state(self.current_state)

                return self.current_state

            except Exception as e:
                logger.error("Error processing AI response: %s", str(e))
                # Create fallback state
                self.current_state = FormState(
                    form=self.current_state.form,
                    progress=self.current_state.progress,
                    feedback="Error occurred, but saved information",
                    next_question=self.current_state.next_question,
                    next_question_explanation=self.current_state.next_question_explanation,
                    prev_question=self.current_state.prev_question,
                )

        except Exception as e:
            logger.error("Error in process_info: %s", str(e))
            return self.current_state

    def analyze_startup(self, message: str, form_state: FormState) -> StartupFormResponse:
        """
        Analyze complete startup info. Use when progress = 100%
        """
        try:
            # Create unique client ID for analysis
            client = self._get_client(
                temperature=0.7
            )

            # Prepare system message
            system_msg = """
            You are a startup analyst. Generate a comprehensive analysis:
            1. Evaluate overall viability (0-10)
            2. List 3-5 key strengths
            3. List 2-3 areas for improvement
            4. Suggest 2-3 specific next steps
            5. Score market potential (0-10)
            """

            client.message_handler.add_message_system(system_msg)

            client.message_handler.add_message_block(
                "STARTUP_INFO",
                self.current_state.form.model_dump()
            )

            # Generate analysis with default values if AI fails
            result: StartupFormResponse = client.generate(result_type=StartupFormResponse)
            return result

        except Exception as e:
            msg = f"Error in analyze_startup: {str(e)}"
            logger.error(msg)
            raise e

    def determine_action(self, message: str):
        """Determine and execute the next action based on message and form state"""
        logger.info("Starting determine_action with message: %s", message)

        self.client_agent.message_handler.add_message_system(
            f"""
            You are an orchestrator that determines the next action.

            TASK:
            - Determine the next action based on the [USER_MESSAGE]
            - Use description of [TOOLS_INFO] to determine the next action

            PROGRESS:
            - Current progress is: {self.current_state.progress}%
            """
        )
        # send message to orchestrator
        self.client_agent.message_handler.add_message_block(
            "USER_MESSAGE",
            message
        )

        # send tools info
        tools_info = [
            {
                "desc": tool.__doc__,
                "func": tool.__name__
            }
            for tool in self.tools
        ]
        self.client_agent.message_handler.add_message_block(
            "TOOLS_INFO",
            tools_info
        )

        result: OrchestratorAction = self.client_agent.generate(
            result_type=OrchestratorAction
        )

        # call the tool
        next_action = result.tool_name

        try:
            # call the tool
            call_tool = getattr(self, next_action)
            result = call_tool(message, self.current_state)

            logger.info("*" * 100)
            logger.info("Tool: %s", next_action)
            logger.info("Result: %s", result)
            logger.info("*" * 100)

            return result

        except Exception as e:
            logger.error("Error calling tool: %s", str(e))
            raise e


def print_form_state(state: FormState) -> None:
    """Print detailed form state"""
    print("\n📋 Current Form State:")
    print("-------------------")

    form_data = state.form.model_dump()
    for field, content in form_data.items():
        filled = "✅" if content.strip() else "❌"
        print(f"\n{filled} {field}:")
        if content.strip():
            print(f"   {content}")

    print(f"\n📊 Progress: {state.progress}%")
    print(f"\n💭 Feedback: {state.feedback}")

    if state.prev_question and state.prev_answer:
        print("\n📝 Previous Q&A:")
        print(f"Q: {state.prev_question}")
        print(f"A: {state.prev_answer}")

    print(f"\n❓ Next Question: {state.next_question}")
    print(f"\n💡 Next Question Explanation: {state.next_question_explanation}")


# Predefined messages for form improvement
STARTUP_MESSAGES = [
    """SmartMail is an AI-powered email management platform. It uses machine
    learning to help professionals manage their inbox efficiently. The system
    analyzes email patterns and user behavior to provide smart organization
    and prioritization features.""",

    """Our target users are busy professionals handling 100 + emails daily:
    executives, entrepreneurs, and knowledge workers. We've validated through
    50+ user interviews and have a 200-person waitlist including employees
    from major tech companies.""",

    """Freemium SaaS model with proven traction. Basic tier free for user
    acquisition, premium at $15/month for individuals, $49/user/month for
    enterprise. Current MRR: $2,000 from early adopters.""",

    """Two technical co-founders with ML/AI experience from Google and Amazon.
    One business developer with 5 years in SaaS sales and previous successful
    exit. Advisory board includes email security expert and VP of Product
    from major email provider.""",

    """We're focusing on the US market initially, specifically targeting tech hubs
    like Silicon Valley, New York, and Boston where email overload is a major
    problem.""",

    """Our ML models have been trained on over 1 million emails, achieving 95%
    accuracy in priority detection. We use state-of-the-art NLP for understanding
    email context.""",

    """Current competition includes traditional email clients and some AI plugins,
    but none offer our level of intelligent automation and personalization.""",

    """We've secured $500K in pre-seed funding and are looking to raise a seed
    round of $2M to accelerate growth and expand the engineering team."""
]


def get_next_message() -> str:
    global STARTUP_MESSAGES
    if not STARTUP_MESSAGES:
        return 'No more messages'
    message = random.choice(STARTUP_MESSAGES)
    STARTUP_MESSAGES.remove(message)
    return message


def main():
    # Initialize orchestrator and form state
    orchestrator = BaseStartupOrchestrator()

    print("\n🚀 Welcome to the Startup Analyzer!")
    print("Processing startup information using predefined messages...\n")

    while True:

        state = orchestrator.current_state
        message = get_next_message()

        print("\n💬 Processing new information...")

        print(f"User Message: {message}\n")
        print(f"Feedback: {state.feedback}")
        print(f"Progress: {state.progress}%")
        print(f"Next question: {state.next_question}")
        print(f"Next question explanation: {state.next_question_explanation}")
        print(f"Confidence: {state.confidence:.2%}")

        orchestrator.determine_action(message)

        if state.progress >= 100:
            break

        time.sleep(1)

    print(f"Final score: {state.feedback}")


if __name__ == "__main__":
    main()
