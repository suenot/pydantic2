# Welcome to Pydantic2

A powerful Python framework for building AI applications with structured responses, powered by Pydantic AI and OpenRouter.

![Pydantic2](https://raw.githubusercontent.com/markolofsen/pydantic2/main/assets/cover.png)

## Quick Links

- [Installation](getting-started/installation.md)
- [Quick Start](getting-started/quick-start.md)
- [Configuration](getting-started/configuration.md)
- [Message Handling](core-concepts/message-handling.md)
- [Type-Safe Responses](core-concepts/type-safe-responses.md)
- [Usage & Cost](core-concepts/usage/info.md)

## Core Features

- Type-safe responses from AI models
- Automatic validation and parsing
- Comprehensive usage tracking
- Budget management
- Error handling
- Online search capabilities

For more details, check out our [Core Concepts](core-concepts/message-handling.md) section.

![Pydantic2](https://raw.githubusercontent.com/markolofsen/pydantic2/main/assets/cover.png)


[![Documentation](https://img.shields.io/badge/docs-pydantic.unrealos.com-blue)](https://pydantic.unrealos.com)
[![PyPI version](https://badge.fury.io/py/pydantic2.svg)](https://badge.fury.io/py/pydantic2)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Security Policy](https://img.shields.io/badge/Security-Policy-blue)](https://github.com/markolofsen/pydantic2/security/policy)
[![PyUp Safety](https://pyup.io/repos/github/markolofsen/pydantic2/shield.svg)](https://pyup.io/repos/github/markolofsen/pydantic2/)
[![Known Vulnerabilities](https://snyk.io/test/github/markolofsen/pydantic2/badge.svg)](https://snyk.io/test/github/markolofsen/pydantic2)
[![GitGuardian scan](https://img.shields.io/badge/Secrets%20Scan-GitGuardian-orange)](https://www.gitguardian.com/)


## Introduction

Pydantic2 combines the power of large language models with structured outputs using Pydantic. This framework allows you to:

- Define structured output formats using Pydantic models
- Connect to various LLM providers through a unified interface
- Track usage and costs
- Enable internet search capabilities
- Manage response budgets
- Handle errors gracefully
- View and analyze usage data through built-in tools

## Key Features

- **🔒 Type-Safe Responses**: Built on Pydantic AI for robust type validation
- **🌐 Online Search**: Real-time internet access for up-to-date information
- **💰 Budget Control**: Built-in cost tracking and budget management
- **📊 Usage Monitoring**: Detailed token and cost tracking
- **🔄 Async Support**: Both sync and async interfaces
- **🛡️ Error Handling**: Comprehensive exception system
- **🎨 Colored Logging**: Beautiful console output with detailed logs
- **🔍 Database Viewer**: Built-in CLI tools to inspect models and usage databases

## Quick Example

```python
from typing import List
from pydantic import BaseModel, Field
from pydantic2 import PydanticAIClient, ModelSettings

# Define your response model
class ChatResponse(BaseModel):
    message: str = Field(description="The chat response message")
    sources: List[str] = Field(default_factory=list, description="Sources used")
    confidence: float = Field(ge=0, le=1, description="Confidence score")

# Initialize client
client = PydanticAIClient(
    model_name="openai/gpt-4o-mini-2024-07-18",
    client_id="my_app",           # Required for usage tracking
    user_id="user123",           # Required for usage tracking
    verbose=True,
    online=True,                 # Enable internet access
    max_budget=10.0,            # Set $10 budget limit
    model_settings=ModelSettings(
        max_tokens=1000,
        temperature=0.7,
        top_p=1,
        frequency_penalty=0,
    )
)

# Add context
client.message_handler.add_message_system(
    "You are a helpful AI assistant. Be concise but informative."
)

# Add user message
client.message_handler.add_message_user(
    "What is the capital of France?"
)

# Generate response
response: ChatResponse = client.generate(
    result_type=ChatResponse
)

print(f"Message: {response.message}")
print(f"Sources: {response.sources}")
print(f"Confidence: {response.confidence}")

# Get usage statistics
stats = client.get_usage_stats()
print(f"Total cost: ${stats.get('total_cost', 0):.4f}")
```

## Getting Started

- [Installation](getting-started/installation.md) - How to install Pydantic2
- [Quick Start](getting-started/quick-start.md) - Get up and running in minutes
- [Configuration](getting-started/configuration.md) - Configure Pydantic2 for your needs

## Core Concepts

- [Type-Safe Responses](core-concepts/type-safe-responses.md) - Structure AI outputs with Pydantic
- [Online Search](core-concepts/online-search.md) - Enable real-time internet access
- [Budget Management](core-concepts/budget-management.md) - Control your API costs
- [Error Handling](core-concepts/error-handling.md) - Handle exceptions gracefully

## CLI Tools

- [Database Viewing](cli.md) - View and analyze your usage and models databases

## Examples

- [Basic Usage](examples/basic-usage.md) - Simple examples to get started
- [Chat Completion](examples/chat-completion.md) - Create chatbot applications

## Contributing

We welcome contributions! See the project repository on [GitHub](https://github.com/markolofsen/pydantic2) for more information.
