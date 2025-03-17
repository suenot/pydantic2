# Basic Usage Examples

This page provides simple examples to help you get started with Pydantic2.

## Simple Text Generation

```python
from pydantic import BaseModel, Field
from pydantic2 import PydanticAIClient

class Summary(BaseModel):
    content: str = Field(description="Summarized content")

client = PydanticAIClient(
    model_name="openai/gpt-4o-mini",
    client_id="my_app",      # Required for tracking
    user_id="user123"       # Required for tracking
)

# Add message
client.message_handler.add_message_user(
    "Summarize the benefits of exercise."
)

response: Summary = client.generate(result_type=Summary)
print(response.content)
```

## Structured Output

```python
from typing import List
from pydantic import BaseModel, Field
from pydantic2 import PydanticAIClient

class MovieRecommendation(BaseModel):
    title: str = Field(description="Movie title")
    year: int = Field(description="Year of release")
    genre: List[str] = Field(description="Movie genres")
    summary: str = Field(description="Brief movie summary")
    rating: float = Field(ge=0, le=10, description="Rating out of 10")

client = PydanticAIClient(
    model_name="openai/gpt-4o-mini",
    client_id="my_app",
    user_id="user123"
)

# Add system context
client.message_handler.add_message_system(
    "You are a movie expert. Provide detailed recommendations."
)

# Add user request
client.message_handler.add_message_user(
    "Recommend a classic science fiction movie."
)

recommendation = client.generate(result_type=MovieRecommendation)

print(f"Title: {recommendation.title} ({recommendation.year})")
print(f"Genres: {', '.join(recommendation.genre)}")
print(f"Rating: {recommendation.rating}/10")
print(f"Summary: {recommendation.summary}")
```

## Message Builder Pattern

```python
from pydantic import BaseModel, Field
from pydantic2 import PydanticAIClient

class Recipe(BaseModel):
    name: str = Field(description="Recipe name")
    ingredients: list[str] = Field(description="List of ingredients")
    instructions: list[str] = Field(description="Step-by-step instructions")
    prep_time: int = Field(description="Preparation time in minutes")
    serves: int = Field(description="Number of servings")

client = PydanticAIClient(
    model_name="openai/gpt-4o-mini",
    client_id="my_recipe_app",
    user_id="chef123"
)

# Build the conversation
client.message_handler.add_message_system(
    "You are a professional chef specializing in simple recipes."
)

client.message_handler.add_message_user(
    "I need a quick pasta recipe."
)

# Add context about ingredients
client.message_handler.add_message_block(
    "AVAILABLE_INGREDIENTS",
    ["pasta", "olive oil", "garlic", "tomatoes", "cheese"]
)

# Generate the recipe
recipe = client.generate(result_type=Recipe)

print(f"# {recipe.name}")
print(f"Prep time: {recipe.prep_time} min | Serves: {recipe.serves}\n")

print("## Ingredients")
for item in recipe.ingredients:
    print(f"- {item}")

print("\n## Instructions")
for i, step in enumerate(recipe.instructions, 1):
    print(f"{i}. {step}")
```

## Context Manager Usage

```python
from pydantic import BaseModel, Field
from pydantic2 import PydanticAIClient

class Answer(BaseModel):
    content: str = Field(description="Answer content")

# Using context manager for auto-cleanup
with PydanticAIClient(
    model_name="openai/gpt-4o-mini",
    verbose=True
) as client:
    # First query
    client.message_handler.add_message_user("What is Python?")
    response1 = client.generate(result_type=Answer)
    print(f"Answer 1: {response1.content}\n")

    # Add response to conversation
    client.message_handler.add_message_assistant(response1.content)

    # Second query
    client.message_handler.add_message_user("What are its main applications?")
    response2 = client.generate(result_type=Answer)
    print(f"Answer 2: {response2.content}")

    # Get usage stats before exiting context
    stats = client.get_usage_stats()
    print(f"\nTotal cost: ${stats.get('total_cost', 0):.4f}")
```

## Budget-Aware Usage

```python
from pydantic import BaseModel, Field
from pydantic2 import PydanticAIClient
from pydantic2.client.exceptions import BudgetExceeded

class Analysis(BaseModel):
    content: str = Field(description="Analysis content")

# Set a tight budget
client = PydanticAIClient(max_budget=0.01)  # $0.01 USD

try:
    # Try to generate a response (might exceed budget)
    client.message_handler.add_message_user(
        "Provide a detailed analysis of global economic trends."
    )
    response: Analysis = client.generate(result_type=Analysis)
    print(response.content)

except BudgetExceeded as e:
    print(f"Budget exceeded! Limit: ${e.budget_limit:.4f}, Cost: ${e.current_cost:.4f}")

    # Fall back to a smaller request
    smaller_client = PydanticAIClient(max_budget=0.01)
    smaller_client.message_handler.add_message_user(
        "Summarize current economic trends in one paragraph."
    )
    smaller_response = smaller_client.generate(result_type=Analysis)
    print(f"Fallback analysis: {smaller_response.content}")
```

## Next Steps

- Try [Chat Completion](chat-completion.md) examples
- Learn about [Error Handling](../core-concepts/error-handling.md)
- Explore [Budget Management](../core-concepts/budget-management.md)
