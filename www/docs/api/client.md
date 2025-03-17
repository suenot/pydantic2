# Client API Reference

This page provides detailed information about the client API in Pydantic2.

## LiteLLMClient

The `LiteLLMClient` class is the main client for interacting with LLMs.

### Constructor

```python
def __init__(self, config: Request):
    """Initialize the LiteLLMClient with a configuration."""
```

#### Parameters

- `config` (`Request`): The configuration for the client.

### Properties

- `config` (`Request`): The configuration for the client.
- `msg` (`MessageHandler`): The message handler for the client.
- `meta` (`Meta`): The metadata for the client.
- `usage_tracker` (`UsageClass`): The usage tracker for the client.

### Methods

#### generate_response

```python
def generate_response(self) -> Any:
    """Generate a response from the LLM."""
```

Generates a response from the LLM based on the messages in the message handler.

**Returns**:
- An instance of the response model specified in the configuration.

**Example**:
```python
response = client.generate_response()
```

#### count_tokens

```python
def count_tokens(self) -> int:
    """Count the number of tokens in the prompt."""
```

Counts the number of tokens in the prompt.

**Returns**:
- The number of tokens in the prompt.

**Example**:
```python
token_count = client.count_tokens()
```

#### get_max_tokens_for_model

```python
def get_max_tokens_for_model(self) -> int:
    """Get the maximum number of tokens for the model."""
```

Gets the maximum number of tokens for the model.

**Returns**:
- The maximum number of tokens for the model.

**Example**:
```python
max_tokens = client.get_max_tokens_for_model()
```

#### calculate_cost

```python
def calculate_cost(self) -> float:
    """Calculate the cost of the request."""
```

Calculates the cost of the request.

**Returns**:
- The cost of the request in USD.

**Example**:
```python
cost = client.calculate_cost()
```

#### get_budget_info

```python
def get_budget_info(self) -> dict:
    """Get information about the budget."""
```

Gets information about the budget.

**Returns**:
- A dictionary with budget information.

**Example**:
```python
budget_info = client.get_budget_info()
```

#### print_usage_info

```python
def print_usage_info(self) -> None:
    """Print usage information."""
```

Prints usage information.

**Example**:
```python
client.print_usage_info()
```

## Request

The `Request` class represents the configuration for a request to an LLM.

### Constructor

```python
def __init__(
    self,
    model: str = "openrouter/openai/gpt-4o-mini-2024-07-18",
    answer_model: Type[BaseModel] = None,
    temperature: float = 0.7,
    max_tokens: int = 500,
    top_p: float = 1.0,
    frequency_penalty: float = 0.0,
    presence_penalty: float = 0.0,
    online: bool = False,
    cache_prompt: bool = True,
    max_budget: float = 0.05,
    timeout: int = 60,
    user_id: str = None,
    client_id: str = "default",
    verbose: bool = False,
    logs: bool = False
):
    """Initialize the Request with configuration parameters."""
```

#### Parameters

- `model` (`str`): The model identifier. Default: `"openrouter/openai/gpt-4o-mini-2024-07-18"`.
- `answer_model` (`Type[BaseModel]`): The Pydantic model for responses. Required.
- `temperature` (`float`): The temperature for response randomness (0.0-1.0). Default: `0.7`.
- `max_tokens` (`int`): The maximum number of tokens in the response. Default: `500`.
- `top_p` (`float`): The nucleus sampling parameter. Default: `1.0`.
- `frequency_penalty` (`float`): The penalty for token frequency. Default: `0.0`.
- `presence_penalty` (`float`): The penalty for token presence. Default: `0.0`.
- `online` (`bool`): Whether to enable web search. Default: `False`.
- `cache_prompt` (`bool`): Whether to cache identical prompts. Default: `True`.
- `max_budget` (`float`): The maximum cost per request in USD. Default: `0.05`.
- `timeout` (`int`): The request timeout in seconds. Default: `60`.
- `user_id` (`str`): The user identifier for budget tracking. Default: `None`.
- `client_id` (`str`): The client identifier for usage tracking. Default: `"default"`.
- `verbose` (`bool`): Whether to show detailed output. Default: `False`.
- `logs` (`bool`): Whether to enable logging. Default: `False`.

### Properties

- All parameters are available as properties.

## MessageHandler

The `MessageHandler` class handles messages for the client.

### Constructor

```python
def __init__(self, config: Request):
    """Initialize the MessageHandler with a configuration."""
```

#### Parameters

- `config` (`Request`): The configuration for the message handler.

### Methods

#### add_message_system

```python
def add_message_system(self, content: Any) -> None:
    """Add a system message."""
```

Adds a system message to the conversation.

**Parameters**:
- `content` (`Any`): The content of the message.

**Example**:
```python
client.msg.add_message_system("You are a helpful assistant.")
```

#### add_message_user

```python
def add_message_user(self, content: Any) -> None:
    """Add a user message."""
```

Adds a user message to the conversation.

**Parameters**:
- `content` (`Any`): The content of the message.

**Example**:
```python
client.msg.add_message_user("What is the capital of France?")
```

#### add_message_assistant

```python
def add_message_assistant(self, content: Any) -> None:
    """Add an assistant message."""
```

Adds an assistant message to the conversation.

**Parameters**:
- `content` (`Any`): The content of the message.

**Example**:
```python
client.msg.add_message_assistant("The capital of France is Paris.")
```

#### add_message_block

```python
def add_message_block(self, tag: str, content: Any) -> None:
    """Add a block message with a tag."""
```

Adds a block message with a tag to the conversation.

**Parameters**:
- `tag` (`str`): The tag for the block.
- `content` (`Any`): The content of the message.

**Example**:
```python
client.msg.add_message_block("CODE", "def hello(): print('Hello, World!')")
```

#### get_messages

```python
def get_messages(self) -> List[dict]:
    """Get all messages in the conversation."""
```

Gets all messages in the conversation.

**Returns**:
- A list of dictionaries representing the messages.

**Example**:
```python
messages = client.msg.get_messages()
```

#### clear

```python
def clear(self) -> None:
    """Clear all messages in the conversation."""
```

Clears all messages in the conversation.

**Example**:
```python
client.msg.clear()
```

## Meta

The `Meta` class represents metadata for a request.

### Properties

- `request_id` (`str`): The ID of the request.
- `model_used` (`str`): The model used for the request.
- `response_time_seconds` (`float`): The response time in seconds.
- `token_count` (`int`): The total number of tokens used.
- `input_tokens` (`int`): The number of input tokens.
- `output_tokens` (`int`): The number of output tokens.

## UsageClass

The `UsageClass` class tracks usage statistics.

### Methods

#### get_usage_stats

```python
def get_usage_stats(self) -> dict:
    """Get usage statistics."""
```

Gets usage statistics.

**Returns**:
- A dictionary with usage statistics.

**Example**:
```python
usage_stats = client.usage_tracker.get_usage_stats()
```

#### get_client_usage_data

```python
def get_client_usage_data(self, client_id: str = None) -> ClientUsageData:
    """Get detailed usage data for a client."""
```

Gets detailed usage data for a client.

**Parameters**:
- `client_id` (`str`, optional): The client ID. If not provided, uses the client ID from the configuration.

**Returns**:
- A `ClientUsageData` instance with detailed usage data.

**Example**:
```python
usage_data = client.usage_tracker.get_client_usage_data()
```

#### get_request_details

```python
def get_request_details(self, request_id: str) -> RequestDetails:
    """Get detailed information about a specific request."""
```

Gets detailed information about a specific request.

**Parameters**:
- `request_id` (`str`): The request ID.

**Returns**:
- A `RequestDetails` instance with detailed information about the request.

**Example**:
```python
request_details = client.usage_tracker.get_request_details(request_id)
```

## ClientUsageData

The `ClientUsageData` class represents detailed usage data for a client.

### Properties

- `client_id` (`str`): The client ID.
- `total_requests` (`int`): The total number of requests.
- `successful_requests` (`int`): The number of successful requests.
- `failed_requests` (`int`): The number of failed requests.
- `total_input_tokens` (`int`): The total number of input tokens.
- `total_output_tokens` (`int`): The total number of output tokens.
- `total_cost` (`float`): The total cost in USD.
- `models_used` (`List[ModelUsage]`): A list of models used.
- `recent_requests` (`List[RequestSummary]`): A list of recent requests.

## RequestDetails

The `RequestDetails` class represents detailed information about a specific request.

### Properties

- `request_id` (`str`): The request ID.
- `timestamp` (`datetime`): The timestamp of the request.
- `model_name` (`str`): The name of the model.
- `model_provider` (`str`): The provider of the model.
- `client_id` (`str`): The client ID.
- `user_id` (`str`): The user ID.
- `config_json` (`str`): The configuration as JSON.
- `request_raw` (`str`): The raw request.
- `request_json` (`str`): The request as JSON.
- `response_json` (`str`): The response as JSON.
- `response_raw` (`str`): The raw response.
- `input_tokens` (`int`): The number of input tokens.
- `output_tokens` (`int`): The number of output tokens.
- `input_cost` (`float`): The cost of input tokens.
- `output_cost` (`float`): The cost of output tokens.
- `total_cost` (`float`): The total cost.
- `status` (`str`): The status of the request.
- `error_message` (`str`): The error message, if any.
