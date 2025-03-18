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
    feedback: str = Field(default="", description="Feedback on provided information")
    confidence: float = Field(
        default=0.0,
        ge=0, le=1,
        description="Confidence in the current state"
    )
    next_question: str = Field(
        default="",
        description="Next question to ask the user"
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


# Predefined messages for form improvement
STARTUP_MESSAGES = [
    """SmartMail is an AI-powered email management platform. It uses machine
    learning to help professionals manage their inbox efficiently. The system
    analyzes email patterns and user behavior to provide smart organization
    and prioritization features.""",

    """Our target users are busy professionals handling 100+ emails daily:
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


# First, add the orchestrator model
class OrchestratorAction(BaseModel):
    """Model for orchestrator decisions"""
    tool_name: str = Field(description="Name of the tool to execute based on the [TOOLS_INFO] message")
    confidence: float = Field(ge=0, le=1, description="Confidence in tool selection")
    reasoning: str = Field(description="Why this tool was selected")


# Then update the orchestrator class
class BaseStartupOrchestrator:
    """Base orchestrator for processing startup information"""

    def __init__(self):
        # Orchestrator's own client for tool selection
        self.client_agent = PydanticAIClient(
            model_name="openai/gpt-4-turbo-preview",
            client_id="startup_orchestrator",
            user_id="startup_user",
            verbose=False,
            retries=2,
            online=True,
            max_budget=10,
            model_settings=ModelSettings(
                # max_tokens=500,
                temperature=0.1,
            )
        )

        # Store current form state
        self.current_state: FormState = FormState()

        # Define available tools with function names
        self.tools = [
            {
                "desc": "Process and update form info. Use when progress < 100%",
                "func": self.process_info
            },
            {
                "desc": "Analyze complete startup info. Use when progress = 100%",
                "func": self.analyze_startup
            }
        ]

    def process_info(self, message: str, form_state: FormState) -> FormState:
        """Process new information and generate follow-up questions"""
        logger.info("Starting process_info with message: %s", message)

        try:
            client = PydanticAIClient(
                model_name="openai/gpt-4-turbo-preview",
                client_id="info_processor",
                max_budget=10,
                model_settings=ModelSettings(temperature=0.3)
            )

            # Clear the message handler
            client.message_handler.clear()

            # First, send the system message with instructions
            client.message_handler.add_message_system(
                '''
                You are a helpful assistant that processes startup information and updates form fields.

                IMPORTANT: the form fields are:
                1. idea_desc: Technical description of product/service and technology
                2. target_mkt: Target market, user validation, and market size
                3. biz_model: Revenue model, pricing, traction metrics
                4. team_info: Team background, funding status, advisors

                YOUR TASK:
                1. Analyze the [USER_MESSAGE]
                2. Identify which form field(s) the information belongs to
                3. APPEND new information to existing content in those fields
                4. NEVER remove or overwrite existing data
            ''')

            # Then send the current state
            client.message_handler.add_message_block(
                'CURRENT_STATE',
                self.current_state.model_dump()
            )

            # Finally send the user message
            client.message_handler.add_message_block(
                'USER_MESSAGE',
                message
            )

            try:
                # Get updated state from AI
                new_state: FormState = client.generate(result_type=FormState)
                logger.info("Raw AI response: %s", new_state.model_dump())

                if not new_state or not new_state.form:
                    logger.error("AI returned invalid state")
                    # Create default state with message in idea_desc
                    new_state = FormState(
                        form=StartupForm(idea_desc=message),
                        progress=25,
                        feedback="Added new information",
                        next_question="Tell me more about your startup",
                        confidence=0.5
                    )

                # Create a new state preserving history
                updated_state = FormState(
                    form=new_state.form,
                    progress=new_state.progress,
                    feedback=new_state.feedback or "Information processed",
                    next_question=new_state.next_question or "Tell me more",
                    prev_question=self.current_state.next_question,
                    prev_answer=message,
                    last_msg=message,
                    confidence=new_state.confidence or 0.8
                )

                # Update current state
                self.current_state = updated_state
                return self.current_state

            except Exception as e:
                logger.error("Error processing AI response: %s", str(e))
                # Create fallback state
                fallback_state = FormState(
                    form=StartupForm(idea_desc=message),
                    progress=25,
                    feedback="Error occurred, but saved information",
                    next_question="Please continue telling me about your startup",
                    confidence=0.5
                )
                self.current_state = fallback_state
                return fallback_state

        except Exception as e:
            logger.error("Error in process_info: %s", str(e))
            return self.current_state

    def analyze_startup(self, message: str, form_state: FormState) -> StartupFormResponse:
        """Generate comprehensive startup analysis"""
        client = PydanticAIClient(
            model_name="openai/gpt-4-turbo-preview",
            client_id="startup_analyzer",
            model_settings=ModelSettings(temperature=0.7)
        )

        # Clear the message handler
        client.message_handler.clear()

        client.message_handler.add_message_system(
            """You are a startup analyst. Generate a comprehensive analysis:
            1. Evaluate overall viability and potential
            2. Identify key strengths and advantages
            3. Highlight areas for improvement
            4. Recommend specific next steps
            5. Score different aspects of the startup
            """
        )

        # Add all available information
        client.message_handler.add_message_block(
            "STARTUP_INFO",
            {
                "idea": self.current_state.form.idea_desc,
                "market": self.current_state.form.target_mkt,
                "business": self.current_state.form.biz_model,
                "team": self.current_state.form.team_info,
                "latest_update": message
            }
        )

        return client.generate(result_type=StartupFormResponse)

    def determine_action(self, message: str) -> FormState:
        """Determine and execute the next action based on message and form state"""
        logger.info("Starting determine_action with message: %s", message)

        # Get tools info with function names
        tools_info = [
            {
                "name": t['func'].__name__,
                "desc": t['desc']
            }
            for t in self.tools
        ]

        # Clear the message handler
        self.client_agent.message_handler.clear()

        # Add tools and context info
        self.client_agent.message_handler.add_message_system(
            '''
            You are an orchestrator that decides which tool to use for processing startup information.

            Available tools:
            1. process_info: Use this when the form is incomplete (progress < 100%)
            2. analyze_startup: Use this only when all information is collected (progress = 100%)

            Your task:
            1. Review the current form state and progress
            2. Select the appropriate tool based on completion status
            3. Return the tool name exactly as shown above
            '''
        )

        self.client_agent.message_handler.add_message_block(
            "TOOLS_INFO",
            tools_info
        )

        self.client_agent.message_handler.add_message_block(
            "CONTEXT",
            {
                "current_progress": self.current_state.progress,
                "form_state": self.current_state.model_dump()
            }
        )

        self.client_agent.message_handler.add_message_block(
            "USER_MESSAGE",
            message
        )

        try:
            # Get tool selection from AI
            result: OrchestratorAction = self.client_agent.generate(
                result_type=OrchestratorAction
            )

            if not result or not result.tool_name:
                logger.error("AI returned invalid tool selection")
                # Default to process_info if progress < 100%
                result = OrchestratorAction(
                    tool_name="process_info",
                    confidence=0.8,
                    reasoning="Defaulting to process_info due to incomplete form"
                )

            logger.info("Orchestrator selected function: %s with confidence %f",
                        result.tool_name, result.confidence)
            logger.info("Reasoning: %s", result.reasoning)

            # Find tool by name
            tool = next((t for t in self.tools if t['func'].__name__ == result.tool_name), None)
            if tool:
                logger.info("Executing function: %s", result.tool_name)
                try:
                    self.current_state = tool["func"](message, self.current_state)
                except Exception as e:
                    logger.error("Error executing function: %s", str(e))
                    # On error, try to continue with current state
                    return self.current_state
            else:
                logger.error("Invalid function name: %s", result.tool_name)

        except Exception as e:
            logger.error("Error in determine_action: %s", str(e))
            # On error, default to process_info
            try:
                self.current_state = self.process_info(message, self.current_state)
            except Exception as inner_e:
                logger.error("Error in fallback processing: %s", str(inner_e))

        return self.current_state


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


def main():
    # Initialize orchestrator and form state
    orchestrator = BaseStartupOrchestrator()
    state = FormState()
    available_messages = STARTUP_MESSAGES.copy()

    print("\n🚀 Welcome to the Startup Analyzer!")
    print("Processing startup information using predefined messages...\n")

    while (state.progress < 100 and available_messages):
        message = random.choice(available_messages)
        available_messages.remove(message)

        print("\n💬 Processing new information...")
        print(f"Progress: {state.progress}%")
        print(f"Next question: {state.next_question}")
        print(f"Message: {message}\n")

        state = orchestrator.determine_action(message)
        print_form_state(state)
        print(f"\n📈 Confidence: {state.confidence:.2%}")

        time.sleep(1)

    if state.progress >= 100:
        try:
            print("\n🔍 Generating startup analysis...")
            result = orchestrator.analyze_startup(state.next_question, state)

            print("\n📊 Analysis Results")
            print("================")
            print(f"\n💯 Overall Score: {result.score}/10")

            if result.market_potential:
                print(f"📈 Market Potential: {result.market_potential}/10")

            print(f"\n💡 Feedback:\n{result.feedback}")

            print("\n💪 Strengths:")
            for strength in result.strengths:
                print(f"✓ {strength}")

            print("\n⚠️ Areas for Improvement:")
            for weakness in result.weaknesses:
                print(f"! {weakness}")

            print("\n🎯 Next Steps:")
            for step in result.next_steps:
                print(f"→ {step}")

        except Exception as e:
            print(f"\n❌ Error in analysis: {str(e)}")
    else:
        print("\n⚠️ Not enough information for analysis")
        print_form_state(state)


if __name__ == "__main__":
    main()
