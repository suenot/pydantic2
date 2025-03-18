# Configuration

Learn how to configure the Pydantic2 client for your needs.

## Quick Start

```python
from pydantic2 import PydanticAIClient, ModelSettings

client = PydanticAIClient(
    model_name="openai/gpt-4o-mini",  # Required: Model identifier
    client_id="my_app",               # Required for usage tracking
    user_id="user123"                 # Required for usage tracking
)
```

## Configuration Parameters

### Essential Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `model_name` | str | Yes | Model identifier (e.g., "openai/gpt-4o-mini") |
| `client_id` | str | Yes | Your application identifier |
| `user_id` | str | Yes | End-user identifier |
| `api_key` | str | No* | OpenRouter API key (can be set via env var) |

> API key can be set via `OPENROUTER_API_KEY` environment variable

### Optional Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_url` | str | "https://openrouter.ai/api/v1" | API endpoint |
| `verbose` | bool | False | Enable detailed logging |
| `retries` | int | 3 | Number of retry attempts |
| `online` | bool | False | Enable internet access |
| `max_budget` | float | None | Maximum budget in USD |

### Model Settings

Configure model behavior using `ModelSettings`:

```python
client = PydanticAIClient(
    model_name="openai/gpt-4o-mini",
    model_settings=ModelSettings(
        max_tokens=100,        # Maximum response length
        temperature=0.7,       # Response randomness (0-1)
        top_p=1.0,            # Nucleus sampling parameter
        frequency_penalty=0.0  # Penalty for repetition
    )
)
```

## Usage Tracking

### Understanding Identifiers

- **client_id**: Identifies your application
  ```python
  client_id="my_trading_bot"  # Tracks usage per application
  ```

- **user_id**: Identifies end-users
  ```python
  user_id="user123"  # Tracks usage per user
  ```

Both identifiers are required for usage tracking and budget management.

### Usage Statistics

```python
# Get overall stats
stats = client.get_usage_stats()
print(f"Total cost: ${stats['total_cost']:.4f}")

# Get user-specific stats
user_stats = client.get_usage_stats(user_id="user123")
print(f"User cost: ${user_stats['total_cost']:.4f}")
```

## Environment Variables

```bash
# Set common configuration values
export OPENROUTER_API_KEY="your-api-key"
```

## Message Handling

For detailed information about building conversations and managing messages, see the [Message Handling](../core-concepts/message-handling.md) guide.

## Error Handling

```python
from pydantic2.client.exceptions import BudgetExceeded, NetworkError

try:
    response: MyModel = client.generate(result_type=MyModel)
except BudgetExceeded as e:
    print(f"Budget exceeded: ${e.current_cost:.4f} / ${e.budget_limit:.4f}")
except NetworkError as e:
    print(f"Network error: {e.message}")
```

## Next Steps

- Try [Basic Usage Examples](../examples/basic-usage.md)
- Learn about [Budget Management](../core-concepts/budget-management.md)
- Explore [Error Handling](../core-concepts/error-handling.md)
