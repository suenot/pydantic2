# Basic Usage Example

This example demonstrates how to use Pydantic2 for structured responses from LLMs.

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
    user_id = str(uuid.uuid4())

    # Create a request configuration
    config = Request(
        model="openrouter/openai/gpt-4o-mini-2024-07-18",
        temperature=0.7,
        max_tokens=500,
        max_budget=0.0001,  # $0.0001 USD (very small budget)
        client_id='demo',
        user_id=user_id,
        answer_model=UserDetail,
        verbose=False,
        logs=False,
        online=True,
    )

    # Initialize the client
    client = LiteLLMClient(config)

    client.msg.add_message_user("Describe who is David Copperfield")

    try:
        # Generate a response
        response: UserDetail = client.generate_response()

        # Print the structured response
        print(json.dumps(response.model_dump(), indent=2))

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
```

## Step-by-Step Explanation

### 1. Define a Response Model

First, we define a Pydantic model that represents the structure of the response we want:

```python
class UserDetail(BaseModel):
    """Model for extracting user details from text."""
    name: str = Field(description="The user's name")
    age: int = Field(description="The user's age")
    interests: List[str] = Field(description="List of user's interests")
```

### 2. Configure the Request

Next, we create a `Request` object with our desired configuration:

```python
config = Request(
    model="openrouter/openai/gpt-4o-mini-2024-07-18",
    temperature=0.7,
    max_tokens=500,
    max_budget=0.0001,  # $0.0001 USD (very small budget)
    client_id='demo',
    user_id=user_id,
    answer_model=UserDetail,
    verbose=False,
    logs=False,
    online=True,
)
```

### 3. Initialize the Client

We create a `LiteLLMClient` with our configuration:

```python
client = LiteLLMClient(config)
```

### 4. Add a Message

We add a message to the conversation:

```python
client.msg.add_message_user("Describe who is David Copperfield")
```

### 5. Generate a Response

We generate a response and get it in our structured format:

```python
response: UserDetail = client.generate_response()
```

### 6. Access the Response

We can access the fields of the response directly or convert it to JSON:

```python
print(json.dumps(response.model_dump(), indent=2))
```

## Expected Output

The output of this example will look something like this:

```
Using user_id: 123e4567-e89b-12d3-a456-426614174000
Setting budget: $0.000100 USD (very small budget)

Prompt token count: 12
Max tokens for model: 4096

=== Budget Information ===
max_budget: $0.000100
estimated_cost: $0.000012
remaining_budget: $0.000088
budget_exceeded: False

Structured Response:
{
  "name": "David Copperfield",
  "age": 67,
  "interests": [
    "Magic",
    "Illusions",
    "Performance art",
    "Collecting rare artifacts",
    "Philanthropy"
  ]
}

Model used: openrouter/openai/gpt-4o-mini-2024-07-18
Response time: 1.234 seconds
Total token count: 56

=== Usage Information ===
Model: openrouter/openai/gpt-4o-mini-2024-07-18
Input tokens: 12
Output tokens: 44
Total tokens: 56
Cost: $0.000056
```

## Next Steps

Now that you've seen a basic example, check out the [Django Integration](django-integration.md) example to learn how to integrate Pydantic2 with Django.
