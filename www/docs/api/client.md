# Client API Reference

## PydanticAIClient

The main interface for interacting with language models.

```python
from pydantic2 import PydanticAIClient, ModelSettings
```

### Constructor Parameters

```python
client = PydanticAIClient(
    # Required Parameters
    model_name: str,                # Model identifier (e.g., "openai/gpt-4o-mini-2024-07-18")

    # Optional Parameters
    api_key: Optional[str] = None,  # OpenRouter API key (can be set via env var)
    base_url: str = "https://openrouter.ai/api/v1",  # API base URL

    # Usage Tracking (both required if using tracking)
    client_id: Optional[str] = None,  # Client identifier
    user_id: Optional[str] = None,    # User identifier

    # Behavior Settings
    verbose: bool = False,   # Enable detailed logging
    retries: int = 3,       # Number of retry attempts
    online: bool = False,   # Enable internet access
    max_budget: Optional[float] = None,  # Maximum budget in USD

    # Model Settings
    model_settings: Optional[ModelSettings] = None  # Model-specific parameters
)
```

### ModelSettings

Configure model-specific parameters:

```python
model_settings = ModelSettings(
    max_tokens: Optional[int] = None,     # Maximum tokens in response
    temperature: float = 0.7,             # Response randomness (0-1)
    top_p: float = 1.0,                  # Nucleus sampling parameter
    frequency_penalty: float = 0.0,       # Penalty for frequent tokens
)
```

### Methods

#### Generate Response

```python
response = client.generate(
    result_type: Type[BaseModel],  # Pydantic model for response
    model_settings: Optional[ModelSettings] = None  # Override default settings
)
```

#### Generate Response (Async)

```python
response = await client.generate_async(
    result_type: Type[BaseModel],  # Pydantic model for response
    model_settings: Optional[ModelSettings] = None  # Override default settings
)
```

#### Get Usage Statistics

```python
stats = client.get_usage_stats()
# Returns:
{
    'total_requests': int,
    'total_tokens': int,
    'total_cost': float,
    'models': List[Dict]  # Per-model statistics
}
```

#### Print Usage Information

```python
client.print_usage_info()  # Prints detailed usage statistics
```

### Context Managers

```python
# Synchronous
with PydanticAIClient() as client:
    response = client.generate(...)

# Asynchronous
async with PydanticAIClient() as client:
    response = await client.generate_async(...)
```

## MessageHandler

Build conversations through the message handler:

```python
# Access via client
handler = client.message_handler
```

### Methods

```python
# Add system message (instructions)
handler.add_message_system(content: str)

# Add user message
handler.add_message_user(content: str)

# Add assistant message (for context)
handler.add_message_assistant(content: str)

# Add structured data
handler.add_message_block(block_type: str, content: dict)

# Get all messages
messages = handler.get_messages()

# Get system prompt
system_prompt = handler.get_system_prompt()

# Get conversation
conversation = handler.get_user_prompt()

# Clear all messages
handler.clear()
```

## Exceptions

```python
from pydantic2.client.exceptions import (
    PydanticAIError,          # Base exception
    BudgetExceeded,          # Budget limit exceeded
    ErrorGeneratingResponse,  # Generation error
    ModelNotFound,           # Model not available
    InvalidConfiguration,    # Invalid client config
    ValidationError,        # Response validation failed
    NetworkError           # Network/HTTP error
)
```

### Exception Details

#### BudgetExceeded
```python
except BudgetExceeded as e:
    print(f"Budget: ${e.budget_limit:.4f}")
    print(f"Cost: ${e.current_cost:.4f}")
```

#### ValidationError
```python
except ValidationError as e:
    print(f"Message: {e.message}")
    print(f"Model: {e.model}")
    print(f"Errors: {e.errors}")
```

#### NetworkError
```python
except NetworkError as e:
    print(f"Status: {e.status_code}")
    print(f"Message: {e.message}")
    print(f"Response: {e.response}")
```

#### ErrorGeneratingResponse
```python
except ErrorGeneratingResponse as e:
    print(f"Message: {e.message}")
    print(f"Error: {e.error}")
    print(f"Details: {e.details}")
```
