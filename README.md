![Pydantic2](https://raw.githubusercontent.com/markolofsen/pydantic2/main/assets/cover.png)

# Pydantic2 🚀

A powerful AI framework with structured Pydantic response handling, LLM integration, and advanced agent capabilities.

[![Documentation](https://img.shields.io/badge/docs-pydantic.unrealos.com-blue)](https://pydantic.unrealos.com)
[![PyPI version](https://badge.fury.io/py/pydantic2.svg)](https://badge.fury.io/py/pydantic2)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

### 🔒 Security & Safety
[![Security Policy](https://img.shields.io/badge/Security-Policy-blue)](https://github.com/markolofsen/pydantic2/security/policy)
[![PyUp Safety](https://pyup.io/repos/github/markolofsen/pydantic2/shield.svg)](https://pyup.io/repos/github/markolofsen/pydantic2/)
[![Known Vulnerabilities](https://snyk.io/test/github/markolofsen/pydantic2/badge.svg)](https://snyk.io/test/github/markolofsen/pydantic2)
[![GitGuardian scan](https://img.shields.io/badge/Secrets%20Scan-GitGuardian-orange)](https://www.gitguardian.com/)

## Overview 🔍

Pydantic2 provides **typesafe, structured responses** from LLMs through Pydantic models. It simplifies working with language models while ensuring type safety and data validation.

### Key Features ✨

- **[Structured Responses](https://pydantic.unrealos.com/guides/structured-responses)** ✅
  - Type-safe responses using Pydantic models
  - Automatic validation and parsing
  - IDE support with autocompletion
  - Custom response models with field descriptions
  - Nested model support

- **[LLM Integration](https://pydantic.unrealos.com/api/client)** 🔌
  - Support for multiple LLM providers
  - Unified API for all models
  - Easy provider switching
  - Automatic retries and fallbacks
  - Streaming support

- **[Budget Control](https://pydantic.unrealos.com/guides/budget-management)** 💰
  - Built-in cost tracking
  - Budget limits per request/user
  - Usage statistics and analytics
  - Cost estimation before requests
  - Detailed usage reports

- **[Message Handling](https://pydantic.unrealos.com/guides/message-handling)** 📝
  - System and user messages
  - Conversation history
  - Structured data support
  - Support for code blocks
  - Support for JSON and DataFrame inputs

- **[Agent System](https://pydantic.unrealos.com/api/agents)** 🛠️
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

## [Installation](https://pydantic.unrealos.com/getting-started/installation) 📦

```bash
pip install pydantic2
```

Set up your API key:
```bash
export OPENROUTER_API_KEY=your_api_key_here
```

## [Quick Start](https://pydantic.unrealos.com/getting-started/quick-start) ⚡

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

### [Django Integration](https://pydantic.unrealos.com/examples/django-integration)

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

## [Configuration](https://pydantic.unrealos.com/getting-started/configuration) 🔧

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

- **Getting Started**
  - [Installation](https://pydantic.unrealos.com/getting-started/installation)
  - [Quick Start Guide](https://pydantic.unrealos.com/getting-started/quick-start)
  - [Configuration](https://pydantic.unrealos.com/getting-started/configuration)

- **Guides**
  - [Message Handling](https://pydantic.unrealos.com/guides/message-handling)
  - [Budget Management](https://pydantic.unrealos.com/guides/budget-management)
  - [Structured Responses](https://pydantic.unrealos.com/guides/structured-responses)
  - [Usage Tracking](https://pydantic.unrealos.com/guides/usage-tracking)

- **Examples**
  - [Basic Usage](https://pydantic.unrealos.com/examples/basic-usage)
  - [Django Integration](https://pydantic.unrealos.com/examples/django-integration)
  - [FastAPI Integration](https://pydantic.unrealos.com/examples/fastapi-integration)
  - [Agent System](https://pydantic.unrealos.com/examples/agent-system)

- **API Reference**
  - [Client](https://pydantic.unrealos.com/api/client)
  - [Models](https://pydantic.unrealos.com/api/models)
  - [Usage](https://pydantic.unrealos.com/api/usage)
  - [Agents](https://pydantic.unrealos.com/api/agents)

## Why Pydantic2? 🤔

- **[Type Safety](https://pydantic.unrealos.com/guides/structured-responses)**: Get structured responses with proper type hints and validation
- **Efficiency**: Reduce boilerplate code and focus on your application logic
- **[Reliability](https://pydantic.unrealos.com/guides/usage-tracking)**: Production-tested with comprehensive error handling
- **[Flexibility](https://pydantic.unrealos.com/api/client)**: Support for multiple LLM providers and frameworks
- **[Scalability](https://pydantic.unrealos.com/guides/budget-management)**: Built for both small projects and enterprise applications
- **[Cost Control](https://pydantic.unrealos.com/guides/budget-management)**: Built-in budget management and usage tracking
- **Framework Support**: Seamless integration with [Django](https://pydantic.unrealos.com/examples/django-integration), [FastAPI](https://pydantic.unrealos.com/examples/fastapi-integration), and more
- **[Developer Experience](https://pydantic.unrealos.com/getting-started/quick-start)**: Great IDE support and documentation

## Support & Community 👥

- [GitHub Issues](https://github.com/markolofsen/pydantic2/issues)
- [Documentation](https://pydantic.unrealos.com)
- [GitHub Discussions](https://github.com/markolofsen/pydantic2/discussions)
- [Contributing Guide](https://pydantic.unrealos.com/about/contributing)
- [Security Policy](https://pydantic.unrealos.com/about/security)
- [Roadmap](https://pydantic.unrealos.com/about/roadmap)

## License 📝

MIT License - see the [LICENSE](LICENSE) file for details. For more information, see our [License page](https://pydantic.unrealos.com/about/license).

## Credits ✨

Developed by [Unrealos Inc.](https://unrealos.com/) - We create innovative AI-powered solutions for business. Meet our [team](https://pydantic.unrealos.com/about/team).
