from typing import List, Any
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
import yaml
from colorlog import ColoredFormatter
import logging

# Setup logging
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(ColoredFormatter(
    "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s%(reset)s",
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    },
    reset=True,
    style='%'
))
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)  # Set once and keep at DEBUG level

# load env variables
load_dotenv()


def to_flat_yaml(data: Any, section: str | None = None) -> str:
    """Convert nested data to flat YAML format with optional section header"""
    # First convert to YAML with proper indentation
    yaml_str = yaml.dump(
        data,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        indent=2,
        width=200,
        explicit_start=False,
        explicit_end=False,
        canonical=False,
        default_style='',
    )

    # Add section markers if section is provided
    if section:
        section = section.upper()
        return f"[{section}]:\n{yaml_str}\n[/{section}]"

    return yaml_str


def clean_text(text: str) -> str:
    """Clean text from special characters and HTML tags"""
    # Remove HTML tags
    soup = BeautifulSoup(text, "html.parser")
    text = soup.get_text()
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s.,!?-]', '', text)
    # Normalize whitespace
    return ' '.join(text.split()).strip()


def clean_prompt(prompt: str) -> str:
    """Clean prompt text by removing extra whitespace and empty lines, but preserve sections"""
    def clean_part(text: str) -> str:
        """Clean non-section text by removing extra whitespace and empty lines"""
        return '\n'.join(line.strip() for line in text.split('\n') if line.strip())

    # Find and preserve sections, clean everything else
    pattern = r'(\[.*?\]:.*?\[/.*?\])'
    parts = re.split(pattern, prompt, flags=re.DOTALL)

    cleaned_parts = []
    for part in parts:
        if part.strip():
            if re.match(r'\[.*?\]:.*\[/.*?\]', part, re.DOTALL):
                cleaned_parts.append(part)  # Keep section unchanged
            else:
                cleaned_parts.append(clean_part(part))  # Clean non-section text

    return '\n'.join(cleaned_parts).strip()


def format_long_text(text: str, width: int = 80) -> str:
    """Format long text with proper wrapping"""
    words = text.split()
    lines = []
    current_line = []
    current_length = 0

    for word in words:
        if current_length + len(word) + 1 <= width:
            current_line.append(word)
            current_length += len(word) + 1
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
            current_length = len(word)

    if current_line:
        lines.append(' '.join(current_line))

    return '\n  '.join(lines)


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
        """Print current state of the form with improved formatting"""
        print("\n" + "=" * 80)
        print("📊 FORM STATE")
        print("=" * 80)

        # Progress bar with percentage
        filled = "█" * (self.progress // 2)
        empty = "░" * (50 - self.progress // 2)
        print(f"\n📈 Progress: {self.progress}%")
        print(f"|{filled}{empty}|")

        # Form data with improved formatting
        print("\n📝 Form Data:")
        print("-" * 80)

        form_data = self.form.model_dump()
        for field, value in form_data.items():
            if isinstance(value, str) and value:
                print(f"\n{field.title()}:")
                print(f"  {format_long_text(value)}")
            elif isinstance(value, list) and value:
                print(f"\n{field.title()}:")
                for item in value:
                    print(f"  • {item}")
            elif value:  # For any other non-empty values
                print(f"\n{field.title()}: {value}")

        # Feedback with improved formatting
        if self.feedback:
            print("\n💭 Feedback:")
            print("-" * 80)
            print(format_long_text(self.feedback))

        # Last question with improved formatting
        if self.last_question:
            print("\n❓ Next Question:")
            print("-" * 80)
            print(format_long_text(self.last_question))

        print("=" * 80)


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
    retries=3,
    system_prompt="""
    You are a form processing assistant that helps structure and validate user information.

    For each message, you MUST:
    1. Analyze the current form state and user's answer carefully
    2. Extract relevant information from the user's answer and update appropriate form fields
    3. Calculate progress based on field completion:
       - Each non-empty field contributes equally to the total progress
       - Consider both completeness and quality of information
       - Progress should never decrease
    4. Provide clear feedback about what information is still missing or needs improvement
    5. Generate relevant follow-up questions to gather missing or unclear information
    6. Set progress to 100% only when all fields contain complete, high-quality information

    Your response MUST be a valid FormProcessorResponse with:
    - updated_form: Form with all updated fields
    - progress: integer 0-100
    - feedback: string with specific feedback
    - example: string with example of good answer
    - next_question: string with next question to ask
    """
)

# Create the analyzer agent
analyzer = Agent(
    analyzer_model,
    result_type=StartupAnalysis,
    retries=3,
    system_prompt="""
    You are an expert startup analyst with deep experience in evaluating early-stage companies.

    When analyzing a startup, focus on:
    1. Market Opportunity
       - Market size and growth potential
       - Problem significance and urgency
       - Target audience validation

    2. Product & Technology
       - Solution uniqueness
       - Technical feasibility
       - Competitive advantages

    3. Business Model
       - Revenue streams clarity
       - Pricing strategy
       - Customer acquisition costs
       - Scalability potential

    4. Execution & Traction
       - Development stage
       - Current metrics
       - Team capabilities

    Provide structured feedback including:
    - Concise summary of the business
    - Key strengths that could lead to success
    - Critical risks that need attention
    - Actionable recommendations for growth

    Be specific and practical in your analysis.
    """
)


# Create the main form agent
form_agent = Agent(
    form_processor_model,
    deps_type=FormState,
    result_type=FormProcessorResponse,
    retries=3,
    system_prompt="""
    You are a form processing assistant that helps gather and structure information.
    Your task is to:
    1. Process incoming messages and extract relevant information
    2. Update form fields based on the extracted information
    3. Track progress and provide feedback
    4. Generate appropriate follow-up questions
    5. When all fields are complete with high-quality information,
       trigger final analysis
    """
)


@form_agent.tool
async def process_message(ctx: RunContext[FormState], message: str) -> FormProcessorResponse:
    """Process user message and update form"""
    # Clean and prepare the message
    cleaned_message = clean_text(message)

    # Prepare form data with proper sections
    form_data = {
        'form': ctx.deps.form.model_dump(),
        'progress': ctx.deps.progress,
        'last_question': ctx.deps.last_question
    }

    # Convert to YAML with sections
    form_state = to_flat_yaml(form_data, section="Form State")
    user_message = to_flat_yaml(cleaned_message, section="User Message")

    # Create and clean prompt
    user_prompt = clean_prompt(f"""
    {form_state}

    {user_message}

    Instructions:
    1. Extract relevant information from the message and update appropriate fields
    2. Ensure business model focuses on revenue generation, not technical details
    3. Move technical/development information to the stage field
    4. Calculate progress based on field completion and quality
    5. Progress should never decrease
    6. Provide specific feedback on what information is still needed
    7. Generate a focused follow-up question
    """)

    logger.debug("Generated prompt structure:")
    logger.debug(user_prompt)

    # Process message
    result = await form_processor.run(user_prompt)

    # Ensure progress never decreases
    new_progress = max(ctx.deps.progress, result.data.progress)

    # Update form state
    ctx.deps.form = result.data.updated_form
    ctx.deps.progress = new_progress
    ctx.deps.last_question = result.data.next_question
    ctx.deps.feedback = result.data.feedback

    logger.debug(f"Progress updated to: {ctx.deps.progress}%")

    return result.data


@form_agent.tool
async def analyze_startup(ctx: RunContext[FormState]) -> StartupAnalysis:
    """Analyze the complete startup information"""
    # Prepare startup data
    startup_info = to_flat_yaml(ctx.deps.form.model_dump(), section="Startup Information")

    # Create and clean prompt
    user_prompt = clean_prompt(f"""
    Please analyze this startup:

    {startup_info}
    """)

    logger.debug("Generated analysis prompt:")
    logger.debug(user_prompt)

    # Get analysis from analyzer agent
    result = await analyzer.run(user_prompt)

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

        # Print final analysis with improved formatting
        print("\n" + "=" * 50)
        print("📋 STARTUP ANALYSIS")
        print("=" * 50)

        print("\n📌 Summary:")
        print("-" * 50)
        print(final_result.summary)

        print("\n💪 Key Strengths:")
        print("-" * 50)
        for strength in final_result.strengths:
            print(f"• {strength}")

        print("\n⚠️ Critical Risks:")
        print("-" * 50)
        for risk in final_result.risks:
            print(f"• {risk}")

        print("\n🎯 Action Items:")
        print("-" * 50)
        for rec in final_result.recommendations:
            print(f"• {rec}")

        print("=" * 50)


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nThank you for using the Startup Form Assistant! 👋")
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
