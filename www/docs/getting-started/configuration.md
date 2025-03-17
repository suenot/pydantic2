# Configuration

Pydantic2 provides a flexible configuration system through the `Request` class. This guide covers all the available configuration options and how to use them.

## Basic Configuration

Here's a basic example of configuring a request:

```python
from pydantic2 import Request
from your_app.models import YourResponseModel

config = Request(
    model="openrouter/openai/gpt-4o-mini-2024-07-18",
    answer_model=YourResponseModel,
    temperature=0.7,
    max_tokens=500
)
```

## All Configuration Options

The `Request` class accepts the following parameters:

### Model Settings

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | `str` | `"openrouter/openai/gpt-4o-mini-2024-07-18"` | Model identifier |
| `answer_model` | `Type[BaseModel]` | Required | Pydantic model for responses |
| `temperature` | `float` | `0.7` | Response randomness (0.0-1.0) |
| `max_tokens` | `int` | `500` | Maximum response length |
| `top_p` | `float` | `1.0` | Nucleus sampling parameter |
| `frequency_penalty` | `float` | `0.0` | Penalty for token frequency |
| `presence_penalty` | `float` | `0.0` | Penalty for token presence |

### Performance Features

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `online` | `bool` | `False` | Enable web search |
| `cache_prompt` | `bool` | `True` | Cache identical prompts |
| `max_budget` | `float` | `0.05` | Maximum cost per request in USD |
| `timeout` | `int` | `60` | Request timeout in seconds |

### User Tracking

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | `None` | User identifier for budget tracking |
| `client_id` | `str` | `"default"` | Client identifier for usage tracking |

### Debug Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `verbose` | `bool` | `False` | Detailed output |
| `logs` | `bool` | `False` | Enable logging |

## Configuration Examples

### Basic Configuration

```python
config = Request(
    model="openrouter/openai/gpt-4o-mini-2024-07-18",
    answer_model=YourResponseModel
)
```

### Advanced Configuration

```python
config = Request(
    # Model settings
    model="openrouter/openai/gpt-4o-mini-2024-07-18",
    answer_model=YourResponseModel,
    temperature=0.5,
    max_tokens=1000,
    top_p=0.9,
    frequency_penalty=0.2,
    presence_penalty=0.2,

    # Performance features
    online=True,
    cache_prompt=True,
    max_budget=0.1,
    timeout=120,

    # User tracking
    user_id="user123",
    client_id="my_app",

    # Debug options
    verbose=True,
    logs=True
)
```

### Configuration for Production

```python
config = Request(
    model="openrouter/openai/gpt-4o-mini-2024-07-18",
    answer_model=YourResponseModel,
    temperature=0.3,  # Lower temperature for more deterministic responses
    max_tokens=500,
    cache_prompt=True,  # Enable caching for better performance
    max_budget=0.05,  # Set a budget limit
    timeout=30,  # Shorter timeout for production
    verbose=False,  # Disable verbose output
    logs=True  # Keep logs enabled for debugging
)
```

### Configuration for Development

```python
config = Request(
    model="openrouter/openai/gpt-4o-mini-2024-07-18",
    answer_model=YourResponseModel,
    temperature=0.7,  # Higher temperature for more creative responses
    max_tokens=1000,  # More tokens for longer responses
    cache_prompt=False,  # Disable caching for testing
    max_budget=0.1,  # Higher budget for testing
    timeout=60,  # Longer timeout for debugging
    verbose=True,  # Enable verbose output
    logs=True  # Enable logs
)
```

## Next Steps

Now that you understand how to configure Pydantic2, check out the [Message Handling](../guides/message-handling.md) guide to learn how to work with messages.
