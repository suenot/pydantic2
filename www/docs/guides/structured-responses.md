# Structured Responses

One of the key features of Pydantic2 is the ability to get structured responses from LLMs using Pydantic models. This guide covers how to define and use structured response models.

## Defining Response Models

Response models are Pydantic models that define the structure of the response you want from the LLM. Here's a simple example:

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class MovieReview(BaseModel):
    """Model for a movie review."""
    title: str = Field(description="The title of the movie")
    director: str = Field(description="The director of the movie")
    year: int = Field(description="The year the movie was released")
    rating: float = Field(description="The rating of the movie (0-10)")
    pros: List[str] = Field(description="The pros of the movie")
    cons: List[str] = Field(description="The cons of the movie")
    summary: str = Field(description="A summary of the review")
    recommendation: Optional[bool] = Field(None, description="Whether the movie is recommended")
```

Each field in the model should have:
- A type annotation
- A description (using `Field`)
- Optional default values

## Using Response Models

To use a response model, pass it to the `Request` configuration:

```python
from pydantic2 import Request, LiteLLMClient

config = Request(
    model="openrouter/openai/gpt-4o-mini-2024-07-18",
    answer_model=MovieReview,  # Your response model
    temperature=0.7,
    max_tokens=500
)

client = LiteLLMClient(config)
```

Then, when you generate a response, it will be returned as an instance of your model:

```python
client.msg.add_message_user("Review the movie 'The Shawshank Redemption'")

response: MovieReview = client.generate_response()
```

## Accessing Response Data

You can access the fields of the response directly:

```python
print(f"Title: {response.title}")
print(f"Director: {response.director}")
print(f"Year: {response.year}")
print(f"Rating: {response.rating}/10")
print("\nPros:")
for pro in response.pros:
    print(f"- {pro}")
print("\nCons:")
for con in response.cons:
    print(f"- {con}")
print(f"\nSummary: {response.summary}")
if response.recommendation is not None:
    print(f"Recommendation: {'Recommended' if response.recommendation else 'Not recommended'}")
```

You can also convert the response to a dictionary or JSON:

```python
# Convert to dictionary
response_dict = response.model_dump()

# Convert to JSON
response_json = response.model_dump_json(indent=2)
print(response_json)
```

## Advanced Response Models

You can create more complex response models using nested models, enums, and more.

### Nested Models

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class Genre(str, Enum):
    ACTION = "action"
    COMEDY = "comedy"
    DRAMA = "drama"
    HORROR = "horror"
    SCIFI = "sci-fi"
    THRILLER = "thriller"
    OTHER = "other"

class Person(BaseModel):
    name: str = Field(description="The name of the person")
    role: str = Field(description="The role of the person")

class MovieDetails(BaseModel):
    runtime: int = Field(description="The runtime of the movie in minutes")
    budget: Optional[float] = Field(None, description="The budget of the movie in millions of dollars")
    box_office: Optional[float] = Field(None, description="The box office of the movie in millions of dollars")

class MovieReview(BaseModel):
    """Model for a detailed movie review."""
    title: str = Field(description="The title of the movie")
    director: Person = Field(description="The director of the movie")
    cast: List[Person] = Field(description="The main cast of the movie")
    year: int = Field(description="The year the movie was released")
    genres: List[Genre] = Field(description="The genres of the movie")
    rating: float = Field(description="The rating of the movie (0-10)")
    details: MovieDetails = Field(description="Additional details about the movie")
    pros: List[str] = Field(description="The pros of the movie")
    cons: List[str] = Field(description="The cons of the movie")
    summary: str = Field(description="A summary of the review")
    recommendation: Optional[bool] = Field(None, description="Whether the movie is recommended")
```

## Best Practices

Here are some best practices for defining response models:

1. **Keep it simple**: Start with simple models and add complexity as needed.
2. **Use descriptive field names**: Field names should be clear and descriptive.
3. **Add detailed descriptions**: Each field should have a detailed description.
4. **Use appropriate types**: Use the most appropriate type for each field.
5. **Set default values**: Use default values for optional fields.
6. **Use nested models**: Use nested models for complex structures.
7. **Use enums**: Use enums for fields with a fixed set of values.
8. **Add docstrings**: Add docstrings to models for better documentation.

## Complete Example

Here's a complete example of using structured responses:

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

from pydantic2 import LiteLLMClient, Request


class Genre(str, Enum):
    ACTION = "action"
    COMEDY = "comedy"
    DRAMA = "drama"
    HORROR = "horror"
    SCIFI = "sci-fi"
    THRILLER = "thriller"
    OTHER = "other"


class Person(BaseModel):
    name: str = Field(description="The name of the person")
    role: str = Field(description="The role of the person")


class MovieDetails(BaseModel):
    runtime: int = Field(description="The runtime of the movie in minutes")
    budget: Optional[float] = Field(None, description="The budget of the movie in millions of dollars")
    box_office: Optional[float] = Field(None, description="The box office of the movie in millions of dollars")


class MovieReview(BaseModel):
    """Model for a detailed movie review."""
    title: str = Field(description="The title of the movie")
    director: Person = Field(description="The director of the movie")
    cast: List[Person] = Field(description="The main cast of the movie")
    year: int = Field(description="The year the movie was released")
    genres: List[Genre] = Field(description="The genres of the movie")
    rating: float = Field(description="The rating of the movie (0-10)")
    details: MovieDetails = Field(description="Additional details about the movie")
    pros: List[str] = Field(description="The pros of the movie")
    cons: List[str] = Field(description="The cons of the movie")
    summary: str = Field(description="A summary of the review")
    recommendation: Optional[bool] = Field(None, description="Whether the movie is recommended")


def main():
    """Example using structured responses."""
    # Create a request configuration
    config = Request(
        model="openrouter/openai/gpt-4o-mini-2024-07-18",
        answer_model=MovieReview,
        temperature=0.7,
        max_tokens=1000,
        verbose=True
    )

    # Initialize the client
    client = LiteLLMClient(config)

    # Add a system message
    client.msg.add_message_system("You are a movie critic with deep knowledge of film history and techniques.")

    # Add a user message
    client.msg.add_message_user("Review the movie 'The Shawshank Redemption'")

    # Generate a response
    response: MovieReview = client.generate_response()

    # Print the structured response
    print(f"Title: {response.title}")
    print(f"Director: {response.director.name} ({response.director.role})")
    print(f"Year: {response.year}")
    print(f"Genres: {', '.join(genre.value for genre in response.genres)}")
    print(f"Rating: {response.rating}/10")

    print("\nCast:")
    for person in response.cast:
        print(f"- {person.name} ({person.role})")

    print("\nDetails:")
    print(f"- Runtime: {response.details.runtime} minutes")
    if response.details.budget:
        print(f"- Budget: ${response.details.budget} million")
    if response.details.box_office:
        print(f"- Box Office: ${response.details.box_office} million")

    print("\nPros:")
    for pro in response.pros:
        print(f"- {pro}")

    print("\nCons:")
    for con in response.cons:
        print(f"- {con}")

    print(f"\nSummary: {response.summary}")

    if response.recommendation is not None:
        print(f"Recommendation: {'Recommended' if response.recommendation else 'Not recommended'}")


if __name__ == "__main__":
    main()
```

## Next Steps

Now that you understand how to work with structured responses, check out the [Usage Tracking](usage-tracking.md) guide to learn how to track usage.
