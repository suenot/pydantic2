![Pydantic2](https://raw.githubusercontent.com/markolofsen/pydantic2/main/assets/cover.png)

# Pydantic2 🚀

A powerful AI framework with structured Pydantic response handling, LLM integration, and advanced agent capabilities.

## Overview 🔍

Pydantic2 is designed to provide **typesafe, structured responses** through Pydantic models with a focus on reliability and flexibility. Key features:

- **Structured Pydantic responses** ✅
- **Flexible LLM client integration** 🔌
- **Budget management and usage tracking** 💰
- **Advanced message handling** 📝
- **Agent system with tools** 🛠️

### Tech Stack 🔋

- **[Pydantic](https://docs.pydantic.dev/)**: Type-safe data handling
- **[LiteLLM](https://litellm.ai/)**: Core LLM routing
- **[Instructor](https://github.com/jxnl/instructor)**: Structured outputs
- **[OpenRouter](https://openrouter.ai/)**: Default model provider
- **[SmoLAgents](https://github.com/smol-ai/smol-agents)**: Agent functionality

## Installation 📦

```bash
pip install pydantic2
```

Set up your API key:
```bash
export OPENROUTER_API_KEY=your_api_key_here
```

## Configuration 🔧

Pydantic2 uses a flexible configuration system through the `Request` class:

```python
from pydantic2 import Request

config = Request(
    # Model settings
    model="openrouter/openai/gpt-4o-mini-2024-07-18",  # Model identifier
    answer_model=YourModel,                  # Pydantic model for responses (required)
    temperature=0.7,                         # Response randomness (0.0-1.0)
    max_tokens=500,                          # Maximum response length

    # Performance features
    online=True,                            # Enable web search
    cache_prompt=True,                      # Cache identical prompts
    max_budget=0.05,                        # Maximum cost per request in USD

    # User tracking
    user_id="user123",                      # User identifier for budget tracking

    # Debug options
    verbose=True,                           # Detailed output
    logs=False                              # Enable logging
)
```

---

## Quick Start ⚡

### Basic Usage Example

```python
from pydantic import BaseModel, Field
from typing import List
import json
import uuid

from pydantic2 import LiteLLMClient, Request


# Define a custom response model
class UserDetail(BaseModel):
    """Model for extracting user details from text."""
    name: str = Field(description="The user's name")
    age: int = Field(description="The user's age")
    interests: List[str] = Field(description="List of user's interests")


def main():
    """Example using LiteLLM client with OpenAI and cost tracking."""
    # Generate a unique user_id for the example
    # In a real application, this would be the user ID from your system
    user_id = str(uuid.uuid4())
    print(f"Using user_id: {user_id}")

    # Set a budget for the user
    max_budget = 0.0001  # $0.0001 USD (very small budget)
    print(f"Setting budget: ${max_budget} USD (very small budget)")

    # Create a request configuration
    config = Request(
        model="openrouter/openai/gpt-4o-mini-2024-07-18",
        temperature=0.7,
        max_tokens=500,
        max_budget=max_budget,  # Setting a budget limit in USD
        client_id='demo',
        user_id=user_id,  # Set user_id for budgeting
        answer_model=UserDetail,  # The Pydantic model to use for the response
        verbose=False,
        logs=False,
        online=True,
    )

    # Initialize the client
    client = LiteLLMClient(config)

    client.msg.add_message_user("Describe who is David Copperfield")

    try:
        # Count tokens in the prompt before sending
        prompt_tokens = client.count_tokens()
        print(f"\nPrompt token count: {prompt_tokens}")

        # Get max tokens for the model
        max_tokens = client.get_max_tokens_for_model()
        print(f"Max tokens for model: {max_tokens}")

        # Get budget information
        budget_info = client.get_budget_info()
        print("\n=== Budget Information ===")
        for key, value in budget_info.items():
            if isinstance(value, float):
                print(f"{key}: ${value:.6f}")
            else:
                print(f"{key}: {value}")

        # Generate a response
        response: UserDetail = client.generate_response()

        # Print the structured response
        print("\nStructured Response:")
        print(json.dumps(response.model_dump(), indent=2))

        # Print model information
        print(f"\nModel used: {client.meta.model_used}")
        print(f"Response time: {client.meta.response_time_seconds:.3f} seconds")

        # Get token count directly from metadata
        token_count = client.meta.token_count
        print(f"Total token count: {token_count}")

        client.print_usage_info()

        usage_stats = client.usage_tracker.get_usage_stats()
        print(f"Usage stats: {usage_stats}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
```

---

### Django Integration Example

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers
from pydantic import BaseModel, Field
from typing import List
from pydantic2 import Request, LiteLLMClient

class FeedbackAnalysis(BaseModel):
    summary: str = Field(..., description="Summary of the feedback")
    sentiment: str = Field(..., description="Detected sentiment")
    key_points: List[str] = Field(..., description="Key points from the feedback")

class FeedbackResponseSerializer(serializers.Serializer):
    answer = FeedbackAnalysis.drf_serializer()

class FeedbackView(APIView):
    def post(self, request):
        feedback = request.data.get('feedback', '')

        client = LiteLLMClient(Request(
            model="openrouter/openai/gpt-4o-mini-2024-07-18",
            temperature=0.3,
            answer_model=FeedbackAnalysis,
            max_budget=0.01,
            user_id=request.user.id if hasattr(request, 'user') else None,
            client_id="django_feedback_app"
        ))

        client.msg.add_message_system("You are a feedback analysis expert.")
        client.msg.add_message_user(feedback)

        response: FeedbackAnalysis = client.generate_response()

        serializer = FeedbackResponseSerializer(data={
            "answer": response.model_dump()
        })
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data)
```

Key features:
- Seamless integration with Django REST framework
- Automatic serialization of Pydantic models
- Type-safe response handling
- Built-in validation
- User tracking through Django's authentication system

---

## Advanced Features

### Token Counting and Cost Estimation

```python
# Count tokens in the prompt
prompt_tokens = client.count_tokens()
print(f"Prompt token count: {prompt_tokens}")

# Get max tokens for the model
max_tokens = client.get_max_tokens_for_model()
print(f"Max tokens for model: {max_tokens}")

# Calculate cost after response
cost = client.calculate_cost()
print(f"Request cost: ${cost:.6f}")
```

### Message Handling 💬

Pydantic2 provides a flexible message handling system through the `MessageHandler` class:

```python
# Initialize client
client = LiteLLMClient(config)

# 1. System Messages - Set AI's behavior and context
client.msg.add_message_system("You are a helpful assistant.")
client.msg.add_message_system({
    "role": "expert",
    "expertise": ["python", "data analysis"]
})

# 2. User Messages - Send queries or inputs
client.msg.add_message_user("Analyze this data")
client.msg.add_message_user({
    "query": "analyze trends",
    "metrics": ["users", "revenue"]
})

# 3. Assistant Messages - Add AI responses or context
client.msg.add_message_assistant("Based on the data...")
client.msg.add_message_assistant([
    "Point 1: Growth is steady",
    "Point 2: Conversion improved"
])

# 4. Block Messages - Add structured data with tags
# Code blocks
client.msg.add_message_block("CODE", """
def hello(): print("Hello, World!")
""")

# Data structures
client.msg.add_message_block("DATA", {
    "users": [{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}],
    "metrics": {"total": 100, "active": 80}
})

# Generate response
response = client.generate_response()
```

Supported data types (automatically formatted):
- Basic types (str, int, float, bool)
- Collections (lists, dicts)
- Pandas DataFrames
- Pydantic models
- Dataclasses
- Custom objects with __str__
- JSON-serializable objects

---

### Budget Management 💰

Pydantic2 includes built-in budget management features:

```python
# Set budget in configuration
config = Request(
    model="openrouter/openai/gpt-4o-mini-2024-07-18",
    answer_model=YourModel,
    max_budget=0.05,  # Maximum $0.05 USD per request
    user_id="user123"  # Track budget by user
)

# Get budget information
budget_info = client.get_budget_info()

# Track usage
client.print_usage_info()
usage_stats = client.usage_tracker.get_usage_stats()
```

### Model Information

```python
from pydantic2.client.prices import UniversalModelGetter

# Get model information
getter = UniversalModelGetter()
model = getter.get_model_by_id("openrouter/openai/gpt-4o-mini-2024-07-18")
print(model)
```

### Structured Usage Tracking

Pydantic2 provides detailed usage tracking with structured Pydantic models for easy integration:

```python
from pydantic2 import LiteLLMClient, Request
import json

# Initialize client with client_id for tracking
config = Request(
    model="openrouter/openai/gpt-4o-mini-2024-07-18",
    answer_model=YourModel,
    client_id="my_application",  # Important for tracking
    verbose=True
)
client = LiteLLMClient(config)

# After making some requests, get detailed usage data
usage_data = client.usage_tracker.get_client_usage_data()

# Access structured data with type hints
print(f"Total requests: {usage_data.total_requests}")
print(f"Successful requests: {usage_data.successful_requests}")
print(f"Total cost: ${usage_data.total_cost:.6f}")

# Print models used
print("\nModels used:")
for model in usage_data.models_used:
    print(f"- {model.model_name}: {model.total_input_tokens + model.total_output_tokens} tokens, ${model.total_cost:.6f}")

# Print recent requests
print("\nRecent requests:")
for req in usage_data.recent_requests:
    print(f"- {req.timestamp}: {req.model_name}, Status: {req.status}, Cost: ${req.total_cost:.6f}")

# Convert to JSON for API responses or storage
usage_json = usage_data.model_dump_json(indent=2)
print(f"\nJSON representation:\n{usage_json}")

# Get usage for a different client
other_client_usage = client.usage_tracker.get_client_usage_data(client_id="other_app")
```

### Detailed Request Tracking

Pydantic2 allows you to retrieve detailed information about specific requests:

```python
from pydantic2 import LiteLLMClient, Request

# Initialize client
config = Request(
    model="openrouter/openai/gpt-4o-mini-2024-07-18",
    answer_model=YourModel,
    client_id="my_application",
    verbose=True
)
client = LiteLLMClient(config)

# Make a request and get its ID
response = client.generate_response()
request_id = client.meta.request_id
print(f"Current request_id: {request_id}")

# Get detailed information about a specific request
request_details = client.usage_tracker.get_request_details(request_id=request_id)

if request_details:
    # Access structured data with type hints
    print(f"Request ID: {request_details.request_id}")
    print(f"Timestamp: {request_details.timestamp}")
    print(f"Model: {request_details.model_name} ({request_details.model_provider})")
    print(f"Status: {request_details.status}")
    print(f"Tokens: {request_details.input_tokens} input, {request_details.output_tokens} output")
    print(f"Cost: ${request_details.total_cost:.6f}")

    # Convert to JSON for API responses or storage
    details_json = request_details.model_dump_json(indent=2)
    print(f"\nJSON representation:\n{details_json}")
else:
    print("No request details found")

# You can also retrieve details for any request ID
historical_request_id = "5f01f28b-1f9a-427a-ae69-b6c4842c0ee3"
historical_details = client.usage_tracker.get_request_details(request_id=historical_request_id)
```

Key features:
- **Structured data** with Pydantic models for both client usage and individual requests
- **Complete request details** including model information, tokens, costs, and status
- **Request content** with access to original request and response data
- **Type safety** with validation and documentation
- **Easy serialization** to JSON for APIs or storage


---


## Agent System Example

```python
from pydantic2.agents import SimpleAgent, tool
from pydantic import BaseModel, Field
from typing import List
import datetime

class AgentResponse(BaseModel):
    answer: str = Field(..., description="The main answer")
    reasoning: str = Field(..., description="The reasoning process")
    tools_used: List[str] = Field(default_factory=list)

@tool("get_time", "Get the current time")
def get_current_time() -> str:
    """Get the current time."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@tool("process_text", "Convert text to uppercase")
def process_text(text: str) -> str:
    """Process text input."""
    return text.upper()

# Create and configure the agent
agent = SimpleAgent(model_id="openrouter/openai/gpt-4o-mini")
agent.add_tools([get_current_time, process_text])

# Run the agent
result = agent.run("What time is it and convert 'hello world' to uppercase")
print(result)

# Launch Gradio UI (optional)
# agent.launch_gradio_ui()
```


## About 👥

Developed by [Unrealos Inc.](https://unrealos.com/) - We create innovative AI-powered solutions for business.

## License 📝

MIT License - see the LICENSE file for details.

## Credits ✨

- Developed by [Unrealos Inc.](https://unrealos.com/)
