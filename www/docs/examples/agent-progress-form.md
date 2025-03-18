# Progress Form Example

Example of using Progress Form to create a smart startup registration form with automatic analysis and testing.

## Complete Code Example

```python
from pydantic2.agents.progress_form import BaseProgressForm
from pydantic import BaseModel, Field
from typing import List, Optional

# 1. Define form structure
class StartupForm(BaseModel):
    """Structure for storing startup information"""
    idea_desc: str = Field(
        default="",
        description="Description of startup idea"
    )
    target_mkt: str = Field(
        default="",
        description="Target market information"
    )
    biz_model: str = Field(
        default="",
        description="Business model"
    )
    team_info: str = Field(
        default="",
        description="Team information"
    )

# 2. Define analysis format
class StartupFormResponse(BaseModel):
    """Startup analysis response format"""
    feedback: str = Field(
        description="Detailed idea analysis"
    )
    score: float = Field(
        ge=0, le=10,
        description="Overall idea score"
    )
    strengths: List[str] = Field(
        description="Key strengths"
    )
    weaknesses: List[str] = Field(
        description="Areas for improvement"
    )
    next_steps: List[str] = Field(
        description="Recommended next steps"
    )
    market_potential: Optional[float] = Field(
        ge=0, le=10,
        description="Market potential score"
    )

# 3. Create form processor
class StartupFormProcessor(BaseProgressForm):
    """Processor for startup form data"""

    def __init__(self, user_id: str):
        super().__init__(
            user_id=user_id,
            client_id="startup_form",
            form_class=StartupForm,
            verbose=True  # Enable logging
        )

        # Register analysis tool
        self.tools = [self.analyze_startup]

        # Configure test agent
        self.configure_test_agent(
            prompt="""
            You are an early-stage startup founder with an interesting idea.
            Your idea involves AI and machine learning.
            You're enthusiastic but inexperienced in business.
            Respond like a real person, occasionally making typical mistakes.
            """,
            client=self._get_test_agent_client(temperature=0.7)
        )

    def analyze_startup(
        self,
        message: str,
    ) -> StartupFormResponse:
        """Analyze startup information"""
        client = self._get_tool_client(temperature=0.7)

        # Configure analysis prompt
        client.message_handler.add_message_system(
            """
            You are an experienced startup analyst. Conduct analysis:
            1. Evaluate idea viability (0-10)
            2. Identify 3-5 key strengths
            3. Point out 2-3 areas for improvement
            4. Suggest 2-3 specific next steps
            5. Rate market potential (0-10)
            """
        )

        # Add form data for analysis
        client.message_handler.add_message_block(
            "STARTUP_INFO",
            self.current_state.form.model_dump()
        )

        try:
            # Generate analysis
            result: StartupFormResponse = client.generate(
                result_type=StartupFormResponse
            )

            # Print results
            print("\n")
            print("="*50)
            print("🎉 STARTUP ANALYSIS COMPLETE 🎉")
            print("="*50)
            print(result.model_dump_json(indent=2))
            print("="*50)

            return result
        except Exception as e:
            raise Exception(f"Analysis error: {str(e)}")

# 4. Run the dialog
def main():
    """Example usage of StartupFormProcessor"""
    processor = StartupFormProcessor(user_id="test_user")
    processor.run_test_dialog()

if __name__ == "__main__":
    main()
```

## How It Works

### 1. Form Structure
- Define fields for data collection
- Add descriptions for each field
- Set default values

### 2. Form Processor
- Initialize with required settings
- Register analysis tool
- Configure test agent

### 3. Test Agent
- Simulates real user
- Has defined "personality"
- Makes realistic mistakes

### 4. Data Analysis
- Triggers at 100% completion
- Generates structured report
- Suggests concrete actions

## Running the Example

```bash
# Run the example
python startup_form.py
```

You'll see:
1. Dialog with test agent
2. Form completion process
3. Progress tracking
4. Final analysis

## Example Output

```json
{
  "feedback": "Strong technical team with proven experience...",
  "score": 8.5,
  "strengths": [
    "Experienced technical co-founders",
    "Clear market understanding",
    "Validated customer interest"
  ],
  "weaknesses": [
    "Early stage revenue",
    "Competitive market"
  ],
  "next_steps": [
    "Expand pilot program",
    "Secure seed funding",
    "Build sales team"
  ],
  "market_potential": 9.0
}
```

## Key Features

### 1. Form Structure
- Clear field definitions
- Descriptive labels
- Default values

### 2. Analysis
- Structured output
- Score ranges
- Optional fields

### 3. Agent Configuration
- Personality customization
- Temperature settings
- System prompts

### 4. Error Handling
- Try/catch blocks
- Informative messages
- State preservation

## Advanced Configuration

### Custom Client Configuration

While Progress Form provides convenient methods like `_get_test_agent_client` and `_get_tool_client`, you can also configure your own custom client for more control:

```python
from pydantic2 import PydanticAIClient, ModelSettings

# Create custom client
custom_client = PydanticAIClient(
    model_name="openai/gpt-4o-mini-2024-07-18",
    client_id="custom_startup_analyzer",
    user_id="test_user",
    verbose=False,
    retries=3,
    online=True,
    max_budget=1,
    model_settings=ModelSettings(
        max_tokens=1000,
        temperature=0.7,
        top_p=1,
        frequency_penalty=0,
    )
)

# Use custom client in your processor
class CustomStartupFormProcessor(BaseProgressForm):
    def __init__(self, user_id: str):
        super().__init__(
            user_id=user_id,
            client_id="startup_form",
            form_class=StartupForm,
            verbose=True,
            client_agent=custom_client  # Pass custom client
        )

        # Configure test agent with custom client
        self.configure_test_agent(
            prompt="Your prompt here...",
            client=custom_client
        )

    def analyze_startup(self, message: str) -> StartupFormResponse:
        # Use custom client for analysis
        result = custom_client.generate(
            result_type=StartupFormResponse,
            messages=[
                {
                    "role": "system",
                    "content": "You are a startup analyst..."
                },
                {
                    "role": "user",
                    "content": "Analyze this startup data..."
                }
            ]
        )
        return result

```

### Benefits of custom client:
- Fine-tune model parameters
- Control API settings
- Custom retry logic
- Detailed monitoring
- Different models for different tasks

---

## Client Configuration Options

You can customize various aspects of the client:

1. **Model Selection**

```python
client = PydanticAIClient(
    model_name="openai/gpt-4o-mini-2024-07-18",  # Choose model
    model_settings=ModelSettings(
        max_tokens=2000,  # Longer responses
        temperature=0.9,  # More creative
    )
)
```

2. **Performance Settings**
```python
client = PydanticAIClient(
    retries=5,  # More retries
    timeout=30,  # Longer timeout
    online=True,  # Use online mode
    max_budget=5,  # Higher budget
)
```

3. **Logging and Monitoring**
```python
client = PydanticAIClient(
    verbose=True,  # Detailed logging
    log_level="DEBUG",
    metrics_enabled=True,
)
```

4. **Different Clients for Different Tasks**
```python
class MultiClientProcessor(BaseProgressForm):
    def __init__(self, user_id: str):
        # High temperature for creative tasks
        self.creative_client = PydanticAIClient(
            model_name="openai/gpt-4o-mini-2024-07-18",
            model_settings=ModelSettings(temperature=0.9)
        )

        # Low temperature for analytical tasks
        self.analytical_client = PydanticAIClient(
            model_name="openai/gpt-4o-mini-2024-07-18",
            model_settings=ModelSettings(temperature=0.1)
        )

        super().__init__(
            user_id=user_id,
            client_id="multi_client_form",
            form_class=StartupForm,
            client_agent=self.analytical_client
        )

    def analyze_creative(self, message: str):
        return self.creative_client.generate(...)

    def analyze_metrics(self, message: str):
        return self.analytical_client.generate(...)
```
