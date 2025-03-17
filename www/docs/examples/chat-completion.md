# Chat Completion Example

This example demonstrates how to use Pydantic2 for chat completions with structured responses.

## Basic Chat Example

```python
from pydantic import BaseModel, Field
from pydantic2 import PydanticAIClient

class ChatResponse(BaseModel):
    message: str = Field(description="The chat response message")
    confidence: float = Field(ge=0, le=1, description="Confidence score")

# Initialize client
client = PydanticAIClient(
    model_name="openai/gpt-4o-mini",
    client_id="my_chat_app",
    user_id="user123"
)

# Set up the conversation
client.message_handler.add_message_system(
    "You are a helpful AI assistant. Be concise but informative."
)

# Add a user message
client.message_handler.add_message_user(
    "What is the capital of France?"
)

# Generate response
response: ChatResponse = client.generate(
    result_type=ChatResponse
)

print(f"AI: {response.message}")
print(f"Confidence: {response.confidence}")
```

## Multi-turn Conversation

```python
from pydantic import BaseModel, Field
from pydantic2 import PydanticAIClient

class ChatResponse(BaseModel):
    message: str = Field(description="The chat response message")

client = PydanticAIClient(
    model_name="openai/gpt-4o-mini",
    client_id="travel_advisor",
    user_id="traveler456"
)

# Initialize the conversation
client.message_handler.add_message_system(
    "You are a travel advisor helping plan a trip."
)

# First exchange
client.message_handler.add_message_user(
    "I'm planning a trip to Europe this summer."
)
response1 = client.generate(result_type=ChatResponse)
print(f"AI: {response1.message}")

# Add response to history
client.message_handler.add_message_assistant(response1.message)

# Second exchange
client.message_handler.add_message_user(
    "Which cities would you recommend in France?"
)
response2 = client.generate(result_type=ChatResponse)
print(f"AI: {response2.message}")
```

## Chat with Structured Data

```python
from typing import List
from pydantic import BaseModel, Field
from pydantic2 import PydanticAIClient

class TravelResponse(BaseModel):
    message: str = Field(description="Travel advice")
    places: List[str] = Field(description="Recommended places")
    budget: float = Field(description="Estimated daily budget in EUR")

client = PydanticAIClient(
    model_name="openai/gpt-4o-mini",
    client_id="travel_planner",
    user_id="traveler789"
)

# Set up conversation
client.message_handler.add_message_system(
    "You are a travel advisor for European destinations."
)

# Add user query
client.message_handler.add_message_user(
    "I want to visit Paris for 3 days."
)

# Add user preferences
client.message_handler.add_message_block(
    "PREFERENCES",
    {
        "budget_level": "medium",
        "interests": ["art", "food"],
        "travel_style": "relaxed"
    }
)

# Generate structured response
response: TravelResponse = client.generate(result_type=TravelResponse)

print(f"Advice: {response.message}\n")
print("Recommended Places:")
for place in response.places:
    print(f"- {place}")
print(f"\nEstimated daily budget: €{response.budget:.2f}")
```

## Next Steps

- Check out [Basic Usage](basic-usage.md) examples
- Learn about [Error Handling](../core-concepts/error-handling.md)
- Explore [Budget Management](../core-concepts/budget-management.md)
