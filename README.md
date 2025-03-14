![Pydantic2](https://raw.githubusercontent.com/markolofsen/pydantic2/main/assets/cover.png)

# Pydantic2 🚀

A powerful AI framework with structured Pydantic response handling, LLM integration, and advanced agent capabilities.

[![Documentation](https://img.shields.io/badge/docs-pydantic2.unrealos.com-blue)](https://pydantic.unrealos.com)
[![PyPI version](https://badge.fury.io/py/pydantic2.svg)](https://badge.fury.io/py/pydantic2)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview 🔍

Pydantic2 provides **typesafe, structured responses** from LLMs through Pydantic models. It simplifies working with language models while ensuring type safety and data validation.

### Key Features ✨

- **Structured Responses** ✅
  - Type-safe responses using Pydantic models
  - Automatic validation and parsing
  - IDE support with autocompletion
  - Custom response models with field descriptions
  - Nested model support

- **LLM Integration** 🔌
  - Support for multiple LLM providers
  - Unified API for all models
  - Easy provider switching
  - Automatic retries and fallbacks
  - Streaming support

- **Budget Control** 💰
  - Built-in cost tracking
  - Budget limits per request/user
  - Usage statistics and analytics
  - Cost estimation before requests
  - Detailed usage reports

- **Message Handling** 📝
  - System and user messages
  - Conversation history
  - Structured data support
  - Support for code blocks
  - Support for JSON and DataFrame inputs

- **Agent System** 🛠️
  - Custom tools and functions
  - Gradio UI integration
  - Extensible framework
  - Tool decorators
  - Memory management

### Tech Stack 🔋

- **[Pydantic](https://docs.pydantic.dev/)**: Type-safe data handling
- **[LiteLLM](https://litellm.ai/)**: Core LLM routing
- **[Instructor](https://github.com/jxnl/instructor)**: Structured outputs
- **[OpenRouter](https://openrouter.ai/)**: Default model provider
- **[SmoLAgents](https://github.com/smol-ai/smol-agents)**: Agent functionality

## Installation 📦

```bash
pip install pydantic2
```

Set up your API key:
```bash
export OPENROUTER_API_KEY=your_api_key_here
```

## Quick Start ⚡

### Basic Example

```python
from pydantic import BaseModel, Field
from typing import List
from pydantic2 import LiteLLMClient, Request

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

### Django Integration

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from pydantic import BaseModel, Field
from typing import List
from pydantic2 import Request, LiteLLMClient

class FeedbackAnalysis(BaseModel):
    summary: str = Field(..., description="Summary of the feedback")
    sentiment: str = Field(..., description="Detected sentiment")
    key_points: List[str] = Field(..., description="Key points from the feedback")

class FeedbackView(APIView):
    def post(self, request):
        feedback = request.data.get('feedback', '')

        client = LiteLLMClient(Request(
            model="openrouter/openai/gpt-4o-mini-2024-07-18",
            answer_model=FeedbackAnalysis,
            max_budget=0.01,
            user_id=request.user.id
        ))

        response = client.generate_response(prompt=feedback)
        return Response(response.model_dump())
```

## Configuration 🔧

```python
from pydantic2 import Request

config = Request(
    # Model settings
    model="openrouter/openai/gpt-4o-mini-2024-07-18",
    answer_model=YourModel,
    temperature=0.7,
    max_tokens=500,

    # Performance features
    online=True,
    cache_prompt=True,
    max_budget=0.05,

    # User tracking
    user_id="user123",
    client_id="my_app"
)
```

## Documentation 📚

Full documentation is available at [https://pydantic.unrealos.com](https://pydantic.unrealos.com)

### Key Topics

- [Installation](https://pydantic.unrealos.com/getting-started/installation)
- [Quick Start Guide](https://pydantic.unrealos.com/getting-started/quick-start)
- [Basic Usage](https://pydantic.unrealos.com/examples/basic-usage)
- [Django Integration](https://pydantic.unrealos.com/examples/django-integration)
- [FastAPI Integration](https://pydantic.unrealos.com/examples/fastapi-integration)
- [Agent System](https://pydantic.unrealos.com/examples/agent-system)
- [Message Handling](https://pydantic.unrealos.com/guides/message-handling)
- [Budget Management](https://pydantic.unrealos.com/guides/budget-management)

## Why Pydantic2? 🤔

- **Type Safety**: Get structured responses with proper type hints and validation
- **Efficiency**: Reduce boilerplate code and focus on your application logic
- **Reliability**: Production-tested with comprehensive error handling
- **Flexibility**: Support for multiple LLM providers and frameworks
- **Scalability**: Built for both small projects and enterprise applications
- **Cost Control**: Built-in budget management and usage tracking
- **Framework Support**: Seamless integration with Django, FastAPI, and more
- **Developer Experience**: Great IDE support and documentation

## Support & Community 👥

- [GitHub Issues](https://github.com/markolofsen/pydantic2/issues)
- [Documentation](https://pydantic.unrealos.com)
- [GitHub Discussions](https://github.com/markolofsen/pydantic2/discussions)
- Email: [info@unrealos.com](mailto:info@unrealos.com)

## License 📝

MIT License - see the [LICENSE](LICENSE) file for details.

## Credits ✨

Developed by [Unrealos Inc.](https://unrealos.com/) - We create innovative AI-powered solutions for business.
