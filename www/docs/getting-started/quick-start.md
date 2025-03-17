# Quick Start

This guide will help you get started with Pydantic2 quickly. We'll cover the basics of setting up a client, defining a response model, and generating a response.

## Basic Example

Here's a simple example that demonstrates the core functionality of Pydantic2:

```python
from pydantic import BaseModel, Field
from typing import List
import json

from pydantic2 import LiteLLMClient, Request


# Define a custom response model
class UserDetail(BaseModel):
    """Model for extracting user details from text."""
    name: str = Field(description="The user's name")
    age: int = Field(description="The user's age")
    interests: List[str] = Field(description="List of user's interests")


# Create a request configuration
config = Request(
    model="openrouter/openai/gpt-4o-mini-2024-07-18",  # Model identifier
    temperature=0.7,                                   # Response randomness
    max_tokens=500,                                    # Maximum response length
    answer_model=UserDetail,                           # Pydantic model for responses
    verbose=True                                       # Show detailed output
)

# Initialize the client
client = LiteLLMClient(config)

# Add a message to the conversation
client.msg.add_message_user("Describe who is David Copperfield")

# Generate a response
response: UserDetail = client.generate_response()

# Print the structured response
print(json.dumps(response.model_dump(), indent=2))
```

## Step-by-Step Explanation

### 1. Define a Response Model

First, define a Pydantic model that represents the structure of the response you want:

```python
from pydantic import BaseModel, Field
from typing import List

class UserDetail(BaseModel):
    """Model for extracting user details from text."""
    name: str = Field(description="The user's name")
    age: int = Field(description="The user's age")
    interests: List[str] = Field(description="List of user's interests")
```

The model should inherit from `BaseModel` and define the fields you want to extract. Each field should have a type annotation and a description.

### 2. Configure the Request

Next, create a `Request` object with your desired configuration:

```python
from pydantic2 import Request

config = Request(
    model="openrouter/openai/gpt-4o-mini-2024-07-18",  # Model identifier
    temperature=0.7,                                   # Response randomness
    max_tokens=500,                                    # Maximum response length
    answer_model=UserDetail,                           # Pydantic model for responses
    verbose=True                                       # Show detailed output
)
```

Key parameters:
- `model`: The identifier of the LLM model to use
- `answer_model`: Your Pydantic model for structured responses
- `temperature`: Controls randomness (0.0-1.0)
- `max_tokens`: Maximum length of the response
- `verbose`: Whether to show detailed output

### 3. Initialize the Client

Create a `LiteLLMClient` with your configuration:

```python
from pydantic2 import LiteLLMClient

client = LiteLLMClient(config)
```

### 4. Add Messages

Add messages to the conversation:

```python
client.msg.add_message_user("Describe who is David Copperfield")
```

You can add different types of messages:
- `add_message_user()`: Add a user message
- `add_message_system()`: Add a system message
- `add_message_assistant()`: Add an assistant message
- `add_message_block()`: Add a block message with a tag

### 5. Generate a Response

Generate a response and get it in your structured format:

```python
response: UserDetail = client.generate_response()
```

The response will be an instance of your Pydantic model.

### 6. Use the Response

You can access the fields of the response directly:

```python
print(f"Name: {response.name}")
print(f"Age: {response.age}")
print(f"Interests: {', '.join(response.interests)}")
```

Or convert it to a dictionary or JSON:

```python
# Convert to dictionary
response_dict = response.model_dump()

# Convert to JSON
response_json = response.model_dump_json(indent=2)
print(response_json)
```

## Next Steps

Now that you've seen the basics, check out the [Configuration](configuration.md) guide to learn more about the available configuration options.
