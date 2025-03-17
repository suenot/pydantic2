from typing import List
from pydantic import BaseModel, Field, ConfigDict
from pydantic_ai import Agent
from pydantic_ai.usage import Usage
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.tools import RunContext
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIModel
from bs4 import BeautifulSoup
import re
import os
from dotenv import load_dotenv
import json

# load env variables
load_dotenv()


class StartupForm(BaseModel):
    """Startup information form"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    product: str = Field(default="", description="Product description")
    stage: str = Field(default="", description="Development stage")
    target_users: str = Field(default="", description="Target audience description")
    business_model: str = Field(default="", description="How the startup makes money")
    unique_features: List[str] = Field(default_factory=list, description="List of unique features/advantages")


class FormState(BaseModel):
    """State for tracking form progress"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    form: StartupForm = Field(default_factory=StartupForm)
    progress: int = Field(default=0, description="Form completion progress (0-100)")
    last_question: str = Field(default="Tell me about your startup idea.", description="Last question asked")
    feedback: str = Field(default="", description="Feedback on the last answer")

    def print_state(self):
        """Print current state of the form"""
        print("\n=== FORM STATE ===")
        print(f"Progress: {self.progress}%")
        print("\nForm Data:")
        print(self.form.model_dump_json(indent=2))
        if self.feedback:
            print("\nFeedback:", self.feedback)
        print("\nLast Question:", self.last_question)
        print("=" * 50)


class FormProcessorResponse(BaseModel):
    """Response from the form processor"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    updated_form: StartupForm = Field(description="Updated form with new information")
    progress: int = Field(description="Overall form completion (0-100)", ge=0, le=100)
    feedback: str = Field(description="Feedback on the provided information")
    example: str = Field(description="Example of a good answer that would improve completion")
    next_question: str = Field(description="Next question to ask")
    next_message: str = Field(default="", description="Next message to process from available messages")
    selection_reason: str = Field(default="", description="Reason for selecting the next message")


class StartupAnalysis(BaseModel):
    """Analysis results for the startup"""
    summary: str = Field(description="Brief summary of the startup")
    strengths: List[str] = Field(description="Key strengths of the startup")
    risks: List[str] = Field(description="Potential risks and challenges")
    recommendations: List[str] = Field(description="Actionable recommendations")


# Initialize OpenAI models with OpenRouter
form_processor_model = OpenAIModel(
    'openai/gpt-4o-mini-2024-07-18',
    provider=OpenAIProvider(
        base_url='https://openrouter.ai/api/v1',
        api_key=os.getenv('OPENROUTER_API_KEY'),
    ),
)

analyzer_model = OpenAIModel(
    'openai/gpt-4o-mini-2024-07-18',
    provider=OpenAIProvider(
        base_url='https://openrouter.ai/api/v1',
        api_key=os.getenv('OPENROUTER_API_KEY'),
    ),
)

# Create the form processor agent
form_processor = Agent(
    form_processor_model,
    result_type=FormProcessorResponse,
    retries=3,  # Increase retries to handle validation errors
    system_prompt="""
    You are a startup form assistant. Your task is to:
    1. Look at the 'current form' data and user's answer
    2. Update and improve ANY fields in the form based on the information provided
    3. Calculate progress based on field completion and quality:
       - Progress should never decrease from previous state
       - All fields need specific metrics for 100% completion
       - Increase progress based on the quality of the 'updated form'
    4. Provide feedback and an example of a better answer
    5. If available messages are provided, select the most appropriate next message
       that would best fill in missing information or enhance existing details
    6. Determine the next best question to ask
    """
)

# Create the analyzer agent
analyzer = Agent(
    analyzer_model,
    result_type=StartupAnalysis,
    retries=3,  # Increase retries for analyzer as well
    system_prompt="""
    You are an expert startup analyst.
    Analyze the startup information and provide structured feedback
    including strengths, risks, and actionable recommendations.
    Focus on market fit, scalability, and competitive advantages.
    """
)


def clean_text(text: str) -> str:
    """Clean text from special characters and HTML tags"""
    # Remove HTML tags
    soup = BeautifulSoup(text, "html.parser")
    text = soup.get_text()
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s.,!?-]', '', text)
    # Normalize whitespace
    return ' '.join(text.split())


# Create the main form agent with text cleaning in the system prompt
form_agent = Agent(
    form_processor_model,
    deps_type=FormState,
    result_type=FormProcessorResponse,
    retries=3,
    system_prompt="""
    You are a startup consultant gathering information about startups.
    Your task is to:
    1. Process the user's message and extract relevant information
    2. Update the form with new information
    3. If you have enough information (all fields have specific metrics),
       use the analyze_startup tool to perform final analysis
    4. Otherwise, provide feedback and determine the next question
    """
)


@form_agent.tool
async def process_message(ctx: RunContext[FormState], message: str, available_messages: List[str] = None) -> FormProcessorResponse:
    """Process user message and update form"""
    # Clean the input text
    cleaned_message = clean_text(message)

    # Process message with form processor
    result = await form_processor.run(
        f"""
        Current form state:
        {ctx.deps.form.model_dump_json(indent=2)}

        Previous question: {ctx.deps.last_question}
        User answer: {cleaned_message}

        Available messages for next selection:
        {json.dumps(available_messages, indent=2) if available_messages else "No more messages available"}

        Please update the form with any new information from the user's answer.
        If available messages are provided, select the most appropriate next message.
        Remember to provide feedback and an example of a better answer.
        If all fields have specific metrics, use the analyze_startup tool.
        """
    )

    # Update form state
    ctx.deps.form = result.data.updated_form
    ctx.deps.progress = result.data.progress
    ctx.deps.last_question = result.data.next_question
    ctx.deps.feedback = result.data.feedback

    return result.data


@form_agent.tool
async def analyze_startup(ctx: RunContext[FormState]) -> StartupAnalysis:
    """Analyze the complete startup information"""

    # Convert current data to StartupForm
    form_data = ctx.deps.form.model_dump()

    # Get analysis from analyzer agent
    result = await analyzer.run(
        f"Please analyze this startup:\n{form_data}"
    )

    return result.data


async def main():
    # Initialize form state
    form_state = FormState()

    print("\n🚀 Welcome to the Startup Form Assistant!")
    print("Processing startup information...\n")

    # Predefined message blocks
    messages = [
        # Product and Vision
        (
            "SmartMail is an AI-powered email management platform. It leverages advanced machine "
            "learning to help professionals regain control of their inbox. The core technology "
            "analyzes email patterns and user behavior to deliver increasingly personalized email "
            "handling, including smart organization and prioritization."
        ),

        # Market and Validation
        (
            "We've validated our market through extensive research and testing. Our target users "
            "are busy professionals who handle 100+ emails daily, including executives, "
            "entrepreneurs, and knowledge workers. The demand is clear – we've conducted in-depth "
            "interviews with over 50 potential users and built a waitlist of 200 people, including "
            "employees from Google, Microsoft, and various startups."
        ),

        # Development Stage
        (
            "Development-wise, we're in beta with strong traction – 100 active users are already "
            "using the platform. We launched our MVP two months ago and are on track for full "
            "release in Q3 2024. Our technical roadmap is solid, with advanced AI features planned "
            "for Q4, including sentiment analysis and automated meeting scheduling."
        ),

        # Business Model
        (
            "We've implemented a freemium SaaS model that's already showing promising results. "
            "The basic tier is free to drive user acquisition, while premium features are "
            "monetized at $15/month for individuals and $49/user/month for enterprise clients. "
            "This model is working – we're already generating $2,000 in Monthly Recurring Revenue "
            "from our early adopters."
        ),

        # Competitive Advantages
        (
            "What sets us apart is our comprehensive feature set: 1) Our AI engine learns and "
            "adapts to personal communication patterns, 2) Smart templates automatically adjust "
            "based on recipient and context, 3) We provide a detailed analytics dashboard for "
            "tracking email productivity, 4) Our automated follow-up system ensures no important "
            "emails slip through the cracks, and 5) We've implemented enterprise-grade security "
            "with end-to-end encryption to protect sensitive communications."
        ),

        # Marketing Strategy
        (
            "To grow our user base, we employ a mix of organic, paid, and partnership-driven "
            "strategies: 1) SEO & content marketing through blog posts, YouTube tutorials, and "
            "LinkedIn thought leadership, 2) Paid acquisition via Google Ads, Facebook, and "
            "LinkedIn targeting professionals, 3) Community engagement on Reddit, IndieHackers, "
            "and relevant Discord groups, 4) Influencer collaborations and affiliate programs "
            "to drive referrals, 5) ProductHunt and media outreach to gain traction among early "
            "adopters and tech publications."
        )
    ]

    while messages and form_state.progress < 100:
        # Process current message
        message = messages.pop(0)  # Take the first message

        print("\n📝 Processing message:")
        print(f"└─ {message[:100]}...")  # Print first 100 chars of message

        # Process the message
        result: AgentRunResult[FormProcessorResponse] = await form_agent.run(
            message,  # Current message as prompt
            deps=form_state
        )

        print("\n💡 AI Analysis:")
        print(f"└─ {result.data.feedback}")
        print(f"\n📊 Progress: {result.data.progress}%")

        # Print current form state
        form_state.print_state()

        # Check if we got analysis results
        if isinstance(result.data, StartupAnalysis):
            print("\n📋 Final Analysis:")
            print(f"└─ {result.data.summary}")
            print("\n💪 Strengths:")
            for strength in result.data.strengths:
                print(f"└─ {strength}")
            print("\n⚠️ Risks:")
            for risk in result.data.risks:
                print(f"└─ {risk}")
            print("\n🎯 Recommendations:")
            for rec in result.data.recommendations:
                print(f"└─ {rec}")
            break

    # If we've reached 100% but haven't got analysis yet, perform final analysis
    if form_state.progress >= 100 and not isinstance(result.data, StartupAnalysis):
        print("\n📝 Form completed! Generating final analysis...")
        final_result: StartupAnalysis = await analyze_startup(RunContext(
            model=form_processor_model,
            usage=Usage(
                requests=0,
                request_tokens=0,
                response_tokens=0,
                total_tokens=0
            ),
            prompt="Perform final analysis",
            deps=form_state
        ))

        print("\n📋 Final Analysis:")
        print(f"└─ {final_result.summary}")
        print("\n💪 Strengths:")
        for strength in final_result.strengths:
            print(f"└─ {strength}")
        print("\n⚠️ Risks:")
        for risk in final_result.risks:
            print(f"└─ {risk}")
        print("\n🎯 Recommendations:")
        for rec in final_result.recommendations:
            print(f"└─ {rec}")


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nThank you for using the Startup Form Assistant! 👋")
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
