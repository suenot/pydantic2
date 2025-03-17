# Message Handling

Pydantic2 provides a flexible message handling system through the `MessageHandler` class. This guide covers how to work with messages in Pydantic2.

## Message Types

Pydantic2 supports four types of messages:

1. **System Messages**: Set the AI's behavior and context
2. **User Messages**: Send queries or inputs
3. **Assistant Messages**: Add AI responses or context
4. **Block Messages**: Add structured data with tags

## Adding Messages

### System Messages

System messages are used to set the AI's behavior and context:

```python
# Add a simple system message
client.msg.add_message_system("You are a helpful assistant.")

# Add a structured system message
client.msg.add_message_system({
    "role": "expert",
    "expertise": ["python", "data analysis"]
})
```

### User Messages

User messages are used to send queries or inputs:

```python
# Add a simple user message
client.msg.add_message_user("Analyze this data")

# Add a structured user message
client.msg.add_message_user({
    "query": "analyze trends",
    "metrics": ["users", "revenue"]
})
```

### Assistant Messages

Assistant messages are used to add AI responses or context:

```python
# Add a simple assistant message
client.msg.add_message_assistant("Based on the data...")

# Add a structured assistant message
client.msg.add_message_assistant([
    "Point 1: Growth is steady",
    "Point 2: Conversion improved"
])
```

### Block Messages

Block messages are used to add structured data with tags:

```python
# Add a code block
client.msg.add_message_block("CODE", """
def hello(): print("Hello, World!")
""")

# Add a data block
client.msg.add_message_block("DATA", {
    "users": [{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}],
    "metrics": {"total": 100, "active": 80}
})
```

## Supported Data Types

Pydantic2 automatically formats various data types:

- Basic types (str, int, float, bool)
- Collections (lists, dicts)
- Pandas DataFrames
- Pydantic models
- Dataclasses
- Custom objects with __str__
- JSON-serializable objects

### Example with Pandas DataFrame

```python
import pandas as pd

# Create a DataFrame
df = pd.DataFrame({
    "name": ["John", "Jane", "Bob"],
    "age": [25, 30, 35],
    "active": [True, False, True]
})

# Add it as a block message
client.msg.add_message_block("DATA", df)
```

### Example with Pydantic Model

```python
from pydantic import BaseModel
from typing import List

class User(BaseModel):
    name: str
    age: int
    active: bool

# Create a list of users
users = [
    User(name="John", age=25, active=True),
    User(name="Jane", age=30, active=False),
    User(name="Bob", age=35, active=True)
]

# Add it as a block message
client.msg.add_message_block("USERS", users)
```

## Getting Messages

You can get all messages in the conversation:

```python
messages = client.msg.get_messages()
```

## Clearing Messages

You can clear all messages in the conversation:

```python
client.msg.clear()
```

## Complete Example

Here's a complete example of using the message handling system:

```python
from pydantic import BaseModel, Field
from typing import List
import pandas as pd

from pydantic2 import LiteLLMClient, Request


# Define a custom response model
class AnalysisResult(BaseModel):
    """Model for data analysis results."""
    summary: str = Field(description="Summary of the analysis")
    trends: List[str] = Field(description="Identified trends")
    recommendations: List[str] = Field(description="Recommendations based on the analysis")


# Create a request configuration
config = Request(
    model="openrouter/openai/gpt-4o-mini-2024-07-18",
    answer_model=AnalysisResult,
    temperature=0.7,
    max_tokens=500
)

# Initialize the client
client = LiteLLMClient(config)

# Add system message
client.msg.add_message_system("You are a data analysis expert.")

# Create a DataFrame
df = pd.DataFrame({
    "date": ["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04", "2023-01-05"],
    "users": [100, 120, 150, 130, 160],
    "revenue": [500, 600, 750, 650, 800]
})

# Add user message
client.msg.add_message_user("Analyze this data and identify trends")

# Add data block
client.msg.add_message_block("DATA", df)

# Generate a response
response: AnalysisResult = client.generate_response()

# Print the structured response
print(f"Summary: {response.summary}")
print("\nTrends:")
for trend in response.trends:
    print(f"- {trend}")
print("\nRecommendations:")
for recommendation in response.recommendations:
    print(f"- {recommendation}")
```

## Next Steps

Now that you understand how to work with messages, check out the [Budget Management](budget-management.md) guide to learn how to manage your budget.
