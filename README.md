# Pydantic2 🚀

A powerful Python framework for building AI applications with structured responses, powered by Pydantic AI and OpenRouter.

![Pydantic2](https://raw.githubusercontent.com/markolofsen/pydantic2/main/assets/cover.png)


[![Documentation](https://img.shields.io/badge/docs-pydantic.unrealos.com-blue)](https://pydantic.unrealos.com)
[![PyPI version](https://badge.fury.io/py/pydantic2.svg)](https://badge.fury.io/py/pydantic2)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Security Policy](https://img.shields.io/badge/Security-Policy-blue)](https://github.com/markolofsen/pydantic2/security/policy)
[![PyUp Safety](https://pyup.io/repos/github/markolofsen/pydantic2/shield.svg)](https://pyup.io/repos/github/markolofsen/pydantic2/)
[![Known Vulnerabilities](https://snyk.io/test/github/markolofsen/pydantic2/badge.svg)](https://snyk.io/test/github/markolofsen/pydantic2)
[![GitGuardian scan](https://img.shields.io/badge/Secrets%20Scan-GitGuardian-orange)](https://www.gitguardian.com/)


## Features 🌟

- **🔒 Type-Safe Responses**: Built on Pydantic AI for robust type validation
- **🌐 Online Search**: Real-time internet access for up-to-date information
- **💰 Budget Control**: Built-in cost tracking and budget management
- **📊 Usage Monitoring**: Detailed token and cost tracking
- **🔄 Async Support**: Both sync and async interfaces
- **🛡️ Error Handling**: Comprehensive exception system
- **🎨 Colored Logging**: Beautiful console output with detailed logs
- **🔍 Database Viewer**: Built-in CLI tools to inspect models and usage databases

---

## Installation 📦

```bash
pip install pydantic2
```

Set your API key:
```bash
export OPENROUTER_API_KEY=your_api_key_here
```

## Quick Start ⚡

```python
from typing import List
from pydantic import BaseModel, Field
from pydantic2 import PydanticAIClient


class ChatResponse(BaseModel):
    """Response format for chat messages."""
    message: str = Field(description="The chat response message")
    sources: List[str] = Field(default_factory=list, description="Sources used in the response")
    confidence: float = Field(ge=0, le=1, description="Confidence score of the response")


def main():
    # Initialize client with usage tracking using context manager
    with PydanticAIClient(
        model_name="openai/gpt-4o-mini-2024-07-18",
        client_id="test_client",
        user_id="test_user",
        verbose=False,
        retries=3,
        online=True,
        # max_budget=0.0003
    ) as client:
        try:
            # Set up the conversation with system message
            client.message_handler.add_message_system(
                "You are a helpful AI assistant. Be concise but informative."
            )

            # Add user message
            client.message_handler.add_message_user("What is the capital of France?")

            # Add structured data block (optional)
            client.message_handler.add_message_block(
                "CONTEXT",
                {
                    "topic": "Geography",
                    "region": "Europe",
                    "country": "France"
                }
            )

            # Generate response (synchronously)
            response: ChatResponse = client.generate(
                result_type=ChatResponse
            )

            # Print the response
            print("\nAI Response:")
            print(response.model_dump_json(indent=2))

            # Print usage statistics
            stats = client.get_usage_stats()
            if stats:
                print("\nUsage Statistics:")
                print(f"Total Requests: {stats.get('total_requests', 0)}")
                print(f"Total Cost: ${stats.get('total_cost', 0):.4f}")

        except Exception as e:
            print(f"\nError: {str(e)}")


if __name__ == "__main__":
    main()
```

---

## CLI Tools 🔍

Pydantic2 stores model information and usage statistics in SQLite databases. To help you interact with these databases, the library includes built-in CLI tools:

```bash
# View models database in browser (http://localhost:8001)
pydantic2 --view-models

# View usage database in browser (http://localhost:8002)
pydantic2 --view-usage

# View both databases simultaneously
pydantic2 --view-all

# Show CLI help
pydantic2 --help
```

The databases are automatically created and maintained as you use the library:

1. **Models Database**: Stores information about models, parameters, and capabilities
2. **Usage Database**: Tracks requests, tokens, costs, and usage statistics

---

## Key Features 🔑

### Type-Safe Responses

```python
from pydantic import BaseModel, Field
from typing import List

class Analysis(BaseModel):
    summary: str = Field(description="Brief summary")
    key_points: List[str] = Field(description="Main points")
    sentiment: float = Field(ge=-1, le=1, description="Sentiment score")
```

### Online Search Mode

```python
client = PydanticAIClient(
    model_name="openai/gpt-4o-mini",
    online=True  # Enables real-time internet access
)
```

### Budget Management

```python
client = PydanticAIClient(
    max_budget=1.0,  # Set $1 limit
    verbose=True     # See detailed cost tracking
)

try:
    response = client.generate(...)
except BudgetExceeded as e:
    print(f"Budget exceeded: ${e.current_cost:.4f} / ${e.budget_limit:.4f}")
```

### Async Support

```python
async def get_analysis():
    async with PydanticAIClient() as client:
        return await client.generate_async(
            result_type=Analysis,
            user_prompt="Analyze this text..."
        )
```

### Error Handling

```python
from pydantic2.client.exceptions import (
    BudgetExceeded, ValidationError, NetworkError, PydanticAIError
)

try:
    response = client.generate(...)
except BudgetExceeded as e:
    print(f"Budget limit reached: ${e.budget_limit:.4f}")
except ValidationError as e:
    print(f"Invalid response format: {e.errors}")
except NetworkError as e:
    print(f"Network error ({e.status_code}): {e.message}")
except PydanticAIError as e:
    print(f"Other error: {e}")
```

### Usage Tracking

```python
stats = client.get_usage_stats()
print(f"Total Requests: {stats['total_requests']}")
print(f"Total Tokens: {stats['total_tokens']}")
print(f"Total Cost: ${stats['total_cost']:.4f}")
```

---

## Advanced Usage 🔧

### Custom Response Models

```python
class ProductAnalysis(BaseModel):
    name: str = Field(description="Product name")
    pros: List[str] = Field(description="Advantages")
    cons: List[str] = Field(description="Disadvantages")
    rating: float = Field(ge=0, le=10, description="Overall rating")
    recommendation: str = Field(description="Buy/Hold/Sell recommendation")

client = PydanticAIClient(online=True)
analysis = client.generate(
    result_type=ProductAnalysis,
    user_prompt="Analyze the latest iPhone"
)
```

### Message Handling

```python
# Add system context
client.message_handler.add_message_system(
    "You are a professional product analyst."
)

# Add user message
client.message_handler.add_message_user(
    "What are the pros and cons of Product X?"
)

# Generate structured response
response = client.generate(result_type=ProductAnalysis)
```

---

## Support & Community 👥

- [GitHub Issues](https://github.com/markolofsen/pydantic2/issues)
- [Documentation](https://pydantic.unrealos.com)
- [GitHub Discussions](https://github.com/markolofsen/pydantic2/discussions)

## License 📝

MIT License - see the [LICENSE](LICENSE) file for details. For more information, see our [License page](https://raw.githubusercontent.com/markolofsen/pydantic2/refs/heads/main/LICENSE)

## Credits ✨

Developed by [Unrealos Inc.](https://unrealos.com/) - We create innovative AI-powered solutions for business. Meet our [team](https://pydantic.unrealos.com/about/team).
