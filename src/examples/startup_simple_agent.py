"""
Simple startup form agent that uses LLM to process user responses
"""

from pydantic import BaseModel, Field
import logging
import json
from typing import Dict, Any, Type, TypeVar, Generic, Optional, List
from smolagents import (
    LiteLLMModel,
    ToolCallingAgent,
    tool,
    PromptTemplates,
    PlanningPromptTemplate,
    ManagedAgentPromptTemplate,
    FinalAnswerPromptTemplate
)
import yaml
from src.pydantic2.client.litellm_client import LiteLLMClient
from src.pydantic2.client.models.base_models import Request

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class StartupForm(BaseModel):
    """Startup information"""
    product: str = Field(default="", description="Product description")
    stage: str = Field(default="", description="Development stage")
    audience: str = Field(default="", description="Target users")
    monetization: str = Field(default="", description="Business model")
    advantages: str = Field(default="", description="Unique features")


class FormWrapper(BaseModel, Generic[T]):
    """Wrapper for the startup form"""
    form_data: Optional[T] = None
    progress: int = Field(default=0, description="Form completion progress (0-100)")
    agent_question: str = Field(default="", description="Next question to ask")


class QuestionHistory(BaseModel):
    """Question model"""
    agent: str = Field(description="Agent question")
    user: str = Field(description="User message")


class StartupAnalysis(BaseModel):
    """Analysis and recommendations for a startup"""
    analysis: str = Field(description="Detailed analysis of the startup")
    recommendations: list[str] = Field(description="List of specific recommendations")


class QuestionResponse(BaseModel):
    """Response model for questions"""
    question: str = Field(description="Question to ask the user")


class Session(BaseModel):
    """Session model"""
    history: List[QuestionHistory] = Field(default_factory=list)
    last_question: str = Field(default="", description="Last question asked by agent")

    def add_interaction(self, agent_question: str, user_message: str) -> None:
        """Add a question-answer pair to history"""
        # Only add if we have both question and answer
        if agent_question and user_message:
            self.history.append(
                QuestionHistory(
                    agent=agent_question,
                    user=user_message
                )
            )
        # Update last question
        if agent_question:
            self.last_question = agent_question

    def get_last_question(self) -> str:
        """Get the last question asked by the agent"""
        return self.last_question


# Global instances
current_form = FormWrapper(form_data=StartupForm())
session = Session()


def get_client(answer_model: Type[BaseModel]) -> LiteLLMClient:
    """Create a LiteLLM client with the given answer model.

    Args:
        answer_model: Pydantic model to use for response structure

    Returns:
        Configured LiteLLM client
    """
    config = Request(
        model="openrouter/openai/gpt-4o-mini-2024-07-18",
        temperature=0.7,
        max_tokens=500,
        answer_model=answer_model,
    )
    return LiteLLMClient(config)


@tool
def extract_info(message: str) -> str:
    """
    Extract information from user message

    Args:
        message: User message containing details

    Returns:
        YAML formatted string with form data
    """
    global current_form, session

    # Create client with FormWrapper model
    client = get_client(FormWrapper[StartupForm])

    print('*' * 100)
    print('CURRENT MESSAGE:', message)
    print('*' * 100)

    # Add context and instructions
    client.msg.add_message_system("""
        You are a startup consultant.

        Rules:
        1. CAREFULLY analyze the message for ANY new information
        2. Update form fields with new info, keeping existing values if no new info
        3. If message mentions features/tech (like NLP, AI, etc), add to advantages
        4. Ask ONE specific question about missing or unclear information

        Important:
        - Enrich the [update_form] with new information based on the [user_message]
        - Determine the next agent question based on the 'form_data' field
        - Update the 'progress' field based on the 'form_data' field
        - Set 'progress' to 100 if the [update_form].form_data is complete
        """)

    # Add current state
    client.msg.add_message_block('update_form', current_form.model_dump())
    client.msg.add_message_block('user_message', message)

    # Get updated form
    response: FormWrapper = client.generate_response()

    # Update form
    current_form = response

    # Update session history with previous question and current message
    session.add_interaction(session.get_last_question(), message)

    # Store new question for next interaction
    if current_form.agent_question:
        session.last_question = current_form.agent_question

    # Convert to YAML
    yaml_str = yaml.dump(
        current_form.model_dump(),
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        indent=2
    ).strip()

    print('Current form:')
    print(yaml_str)
    print('\nSession history:')
    print(yaml.dump(session.model_dump(), default_flow_style=False, indent=2))

    return yaml_str


@tool
def analyze_startup(form_data: str) -> str:
    """
    Analyze startup information and provide recommendations.
    Only call this tool once, when the 'progress' field is 100.

    Args:
        form_data: JSON string containing data from the form

    Returns:
        Analysis and recommendations text
    """

    try:
        form_data = json.loads(form_data)

        # Create client for analysis
        client = get_client(StartupAnalysis)

        # Add context and instructions
        client.msg.add_message_system("""You are a startup consultant analyzing a startup.
Your task is to:
1. Review the [form_data]
2. Provide detailed analysis of market fit and potential
3. Give 3 specific, actionable recommendations
4. Return analysis and recommendations as JSON""")

        client.msg.add_message_block('form_data', form_data)

        # Get analysis from LLM
        response: StartupAnalysis = client.generate_response()

        # Format response
        return response.model_dump_json()

    except json.JSONDecodeError:
        return "Error: Invalid JSON data provided for analysis"
    except Exception as e:
        logger.error(f"Error analyzing startup: {e}")
        return f"Error analyzing startup: {e}"


class StartupAgent:
    """Agent for gathering startup information"""

    def __init__(
        self,
        model_id: str = "openrouter/openai/gpt-4o-mini-2024-07-18",
        # model_id: str = "openrouter/openai/gpt-4o-2024-11-20",
        # model_id: str = "openrouter/anthropic/claude-3.7-sonnet",
        api_base: str = "https://openrouter.ai/api/v1",
        api_key: str = "",
        max_steps: int = 5
    ) -> None:
        try:
            model_kwargs: Dict[str, Any] = {}
            if api_key:
                model_kwargs["api_key"] = api_key

            model = LiteLLMModel(
                model_id=model_id,
                api_base=api_base,
                max_tokens=2000,
                temperature=0.7,
                **model_kwargs
            )

            # Create agent with tools
            prompt_templates = PromptTemplates(
                system_prompt=(
                    "You are a startup assistant gathering information.\n"
                    "\nWhen receiving a user message:\n"
                    "1. Use extract_info to update form with new information\n"
                    "2. If form is complete (progress=100), use analyze_startup\n"
                    "3. Otherwise, just output the agent_question from extract_info response\n"
                    "\nIMPORTANT:\n"
                    "- NEVER use extract_info for your own questions\n"
                    "- NEVER use extract_info when asking follow-up questions\n"
                    "- Only use extract_info for actual user responses"
                ),
                planning=PlanningPromptTemplate(
                    initial_facts="",
                    initial_plan="",
                    update_facts_pre_messages="",
                    update_facts_post_messages="",
                    update_plan_pre_messages="",
                    update_plan_post_messages=""
                ),
                managed_agent=ManagedAgentPromptTemplate(
                    task="",
                    report=""
                ),
                final_answer=FinalAnswerPromptTemplate(
                    pre_messages="",
                    post_messages=""
                )
            )

            self.agent = ToolCallingAgent(
                tools=[extract_info, analyze_startup],
                model=model,
                max_steps=max_steps,
                prompt_templates=prompt_templates
            )
            logger.info("Agent initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing agent: {e}")
            self.agent = None

    def process(self, message: str) -> str:
        """Process user message"""
        if not self.agent:
            return "Error: Agent not initialized"

        try:
            # Extract info from user message
            info = extract_info(message)
            if not isinstance(info, str):
                return "Error: Invalid response format"

            # Parse response as YAML
            try:
                form_data = yaml.safe_load(info)
                if not isinstance(form_data, dict):
                    return "Error: Invalid form data format"
            except yaml.YAMLError as e:
                logger.error(f"Error parsing YAML: {e}")
                return "Error parsing response format"

            # If form is complete, analyze
            if form_data.get("progress") == 100:
                if not form_data.get("form_data"):
                    return "Error: Missing form data"
                analysis = analyze_startup(json.dumps(form_data["form_data"]))
                return analysis

            # Get next question if available
            question = form_data.get("agent_question")
            if not question:
                return "What else can you tell me about your startup?"

            return question

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"Error processing message: {e}"


def main():
    """Run example conversation"""
    agent = StartupAgent()

    messages = [
        "I'm building an AI email assistant that organizes emails",
        "We're in MVP stage",
        "For busy professionals, $10/month",
        "Using NLP for smart email processing"
    ]

    for msg in messages:
        print(f"\nUser: {msg}")
        print(f"Agent: {agent.process(msg)}")


if __name__ == "__main__":
    main()
