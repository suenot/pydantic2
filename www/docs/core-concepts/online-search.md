# Online Search

Pydantic2 includes powerful online search capabilities, allowing AI models to access real-time information from the internet.

## Overview

By default, language models are trained on data up to their cutoff date and cannot access current information. Pydantic2's online search feature solves this limitation by enabling models to:

1. Search the internet for up-to-date information
2. Cite sources properly
3. Provide more accurate and timely responses

## Enabling Online Search

To enable online search, simply set the `online` parameter to `True` when initializing the client:

```python
from pydantic2 import PydanticAIClient

# Create client with online search enabled
client = PydanticAIClient(
    model_name="openai/gpt-4o-mini",
    online=True  # Enable internet access
)
```

## Example: Retrieving Current Information

```python
from pydantic import BaseModel, Field
from typing import List
from pydantic2 import PydanticAIClient

class NewsResponse(BaseModel):
    """Response model for news queries."""
    summary: str = Field(description="Summary of the news topic")
    key_points: List[str] = Field(description="Key points about the topic")
    sources: List[str] = Field(description="Source URLs for the information")

client = PydanticAIClient(online=True)

# Add system context
client.message_handler.add_message_system(
    "You are a news analyst. Provide current information with sources."
)

# Add user query
client.message_handler.add_message_user(
    "What are the latest developments in renewable energy?"
)

# Generate response
response: NewsResponse = client.generate(result_type=NewsResponse)

print(f"Summary: {response.summary}\n")
print("Key Points:")
for point in response.key_points:
    print(f"- {point}")
print("\nSources:")
for source in response.sources:
    print(f"- {source}")
```

## How It Works

When online search is enabled, Pydantic2:

1. Analyzes the user query to determine if online information is needed
2. Performs web searches using search APIs
3. Retrieves and processes relevant information from search results
4. Provides the processed information to the model for generating responses
5. Ensures sources are properly cited in the response

## Configuring Online Search

You can customize online search behavior:

```python
client = PydanticAIClient(
    online=True,
)
```

## Response Models with Sources

When using online search, it's best practice to include a field for sources in your response models:

```python
from pydantic import BaseModel, Field
from typing import List

class ResearchResponse(BaseModel):
    """Response with source attribution."""
    content: str = Field(description="The main response content")
    sources: List[str] = Field(
        default_factory=list,
        description="Sources of information used in the response"
    )
```

## Best Practices

1. **Be specific in prompts**: Clearly specify what information you need
2. **Include date context**: For time-sensitive information, specify when you need information from
3. **Verify sources**: Always check the provided sources for accuracy
4. **Use appropriate models**: More capable models handle online information better
5. **Balance with context**: Don't rely solely on online search for questions that could be answered from model knowledge

## Limitations

- Search results depend on the underlying search API quality
- Some websites may block scraping or have robots.txt restrictions
- Processing time increases when online search is enabled
- Not all information can be found online or accessed by the search system

## Next Steps

- Learn about [Budget Management](budget-management.md) to control costs
- Explore [Error Handling](error-handling.md) for robust applications
- Check out the [CLI Tools](../cli.md) for usage monitoring
