# Type-Safe Responses

One of the core features of Pydantic2 is the ability to define structured, type-safe responses from language models.

## The Problem with Unstructured Text

Traditional language model APIs return unstructured text, which requires parsing and validation to be useful in applications. This leads to several issues:

- Unpredictable response formats
- Error-prone manual parsing
- Difficult integration with typed systems
- Inconsistent output structure

## How Pydantic2 Solves This

Pydantic2 uses Pydantic models to define the structure and validation rules for LLM responses. The framework:

1. Prompts the model with your schema requirements
2. Processes the raw LLM output
3. Validates it against your Pydantic model
4. Returns a properly typed Python object

## Defining Response Models

Create a Pydantic model to define your expected output structure:

```python
from pydantic import BaseModel, Field
from typing import List

class MovieReview(BaseModel):
    title: str = Field(description="The title of the movie")
    rating: float = Field(ge=0, le=10, description="Rating from 0-10")
    pros: List[str] = Field(description="Positive aspects of the movie")
    cons: List[str] = Field(description="Negative aspects of the movie")
    summary: str = Field(description="Brief review summary")
```

Key benefits:

- **Self-documenting**: Field descriptions explain what each field is for
- **Validated**: Ensure values meet your requirements (e.g., rating is between 0-10)
- **Type safe**: IDE autocompletion and type checking
- **Default values**: Handle missing data gracefully

## Generating Structured Responses

Use your model with the message handler:

```python
from pydantic2 import PydanticAIClient

client = PydanticAIClient()

# Add system context
client.message_handler.add_message_system(
    "You are a movie critic. Provide detailed, balanced reviews."
)

# Add user request
client.message_handler.add_message_user(
    "Review the movie 'The Matrix'"
)

# Generate a structured movie review
review = client.generate(result_type=MovieReview)

# Access fields as attributes
print(f"Movie: {review.title}")
print(f"Rating: {review.rating}/10")
print(f"Summary: {review.summary}")

print("Pros:")
for pro in review.pros:
    print(f"- {pro}")

print("Cons:")
for con in review.cons:
    print(f"- {con}")
```

## Complex Nested Models

You can create complex nested models for more sophisticated responses:

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime

class Author(BaseModel):
    name: str = Field(description="Author's full name")
    expertise: List[str] = Field(description="Areas of expertise")

class Reference(BaseModel):
    title: str = Field(description="Title of the reference")
    url: str = Field(description="URL of the reference")
    access_date: datetime = Field(description="When the reference was accessed")

class ResearchReport(BaseModel):
    title: str = Field(description="Report title")
    authors: List[Author] = Field(description="List of authors")
    summary: str = Field(description="Executive summary")
    findings: List[str] = Field(description="Key findings")
    methodology: str = Field(description="Research methodology")
    references: List[Reference] = Field(description="Sources referenced")
    limitations: Optional[List[str]] = Field(
        default=None,
        description="Limitations of the research"
    )
```

## Handling Validation Errors

When the LLM response doesn't match your model, Pydantic2 raises a `ValidationError`:

```python
from pydantic2 import PydanticAIClient
from pydantic2.client.exceptions import ValidationError

client = PydanticAIClient()

try:
    client.message_handler.add_message_user(
        "Review the movie 'The Matrix'"
    )
    review = client.generate(result_type=MovieReview)
except ValidationError as e:
    print("Response didn't match the expected format:")
    print(e.errors)  # List of validation errors
    print(e.received_data)  # The raw data received
```

## Best Practices

1. **Be specific with field descriptions**: Clear descriptions help the model generate appropriate values
2. **Use validation constraints**: Add constraints like `ge`, `le`, `min_length`, etc.
3. **Start simple**: Begin with simpler models and add complexity gradually
4. **Include examples**: If responses are inconsistent, provide examples in your prompts
5. **Use optional fields**: Mark fields as `Optional` if they're not always required
6. **Provide default values**: Use `default` or `default_factory` for fields that might be missing

## Advanced Type Hints

Pydantic2 supports all of Pydantic's type hints:

```python
from pydantic import BaseModel, Field, HttpUrl, EmailStr
from typing import List, Dict, Optional, Union, Literal
from datetime import datetime
from enum import Enum

class Category(str, Enum):
    TECH = "technology"
    SCIENCE = "science"
    HEALTH = "health"

class ArticleSummary(BaseModel):
    title: str = Field(description="Article title")
    url: HttpUrl = Field(description="Article URL")
    publish_date: datetime = Field(description="Publication date")
    category: Category = Field(description="Article category")
    sentiment: Literal["positive", "neutral", "negative"] = Field(
        description="Overall sentiment"
    )
    word_count: int = Field(ge=0, description="Number of words")
    contact: Optional[EmailStr] = Field(default=None, description="Contact email")
    tags: List[str] = Field(default_factory=list, description="Article tags")
    metadata: Dict[str, Union[str, int, bool]] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
```

## Next Steps

- Learn about [Online Search](online-search.md)
- Explore [Budget Management](budget-management.md)
- Check [Error Handling](error-handling.md)
