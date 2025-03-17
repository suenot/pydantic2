# Welcome to Pydantic2

<figure markdown>
  ![Pydantic2](https://raw.githubusercontent.com/markolofsen/pydantic2/main/assets/cover.png)
</figure>

Pydantic2 is a powerful library for working with Large Language Models (LLMs) that provides structured responses using Pydantic models. It simplifies the process of interacting with LLMs while ensuring type safety and data validation.

## Features

### 🚀 Structured Responses
- Define response structures using Pydantic models
- Automatic validation and parsing of LLM responses
- Type safety and IDE support

### 📊 Usage Tracking
- Built-in usage statistics
- Cost tracking and budgeting
- Detailed request history

### 🤖 Agent System
- Simple yet powerful agent framework
- Built-in tools for common tasks
- Easy to extend with custom tools

### 🔌 Framework Integration
- Seamless integration with FastAPI
- Django integration support
- Easy to integrate with other frameworks

### 💼 Enterprise Ready
- Production-grade performance
- Comprehensive security features
- Detailed documentation

## Quick Start

### Installation

```bash
pip install pydantic2
```

### Basic Usage

```python
from pydantic import BaseModel, Field
from typing import List

class MovieReview(BaseModel):
    title: str = Field(description="The title of the movie")
    rating: float = Field(description="The rating of the movie")
    pros: List[str] = Field(description="The pros of the movie")
    cons: List[str] = Field(description="The cons of the movie")

client = LiteLLMClient(Request(
    model="openrouter/openai/gpt-4o-mini-2024-07-18",
    answer_model=MovieReview
))

response = client.generate_response(
    prompt="Review the movie 'Inception'"
)

print(f"Title: {response.title}")
print(f"Rating: {response.rating}/5")
print("Pros:", ", ".join(response.pros))
print("Cons:", ", ".join(response.cons))
```

## Why Pydantic2?

- **Type Safety**: Get structured responses with proper type hints and validation
- **Efficiency**: Reduce boilerplate code and focus on your application logic
- **Reliability**: Production-tested with comprehensive error handling
- **Flexibility**: Support for multiple LLM providers and frameworks
- **Scalability**: Built for both small projects and enterprise applications

## Getting Started

- [Installation Guide](getting-started/installation.md)
- [Quick Start Guide](getting-started/quick-start.md)
- [Configuration Guide](getting-started/configuration.md)

## Examples

- [Basic Usage](examples/basic-usage.md)
- [Django Integration](examples/django-integration.md)
- [FastAPI Integration](examples/fastapi-integration.md)
- [Agent System](examples/agent-system.md)

## Community

- [GitHub Repository](https://github.com/markolofsen/pydantic2)
- [Issue Tracker](https://github.com/markolofsen/pydantic2/issues)
- [Contributing Guide](about/contributing.md)

## Support

For support and questions:
- Email: [info@unrealos.com](mailto:info@unrealos.com)
- GitHub Discussions: [Pydantic2 Discussions](https://github.com/markolofsen/pydantic2/discussions)

## License

Pydantic2 is released under the MIT License. See the [License](about/license.md) page for more details.
