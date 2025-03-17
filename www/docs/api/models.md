# Models API Reference

This page provides detailed information about the models API in Pydantic2.

## Base Models

### Request

The `Request` class represents the configuration for a request to an LLM.

```python
class Request(BaseModel):
    """Configuration for a request to an LLM."""
    model: str = "openrouter/openai/gpt-4o-mini-2024-07-18"
    answer_model: Type[BaseModel] = None
    temperature: float = 0.7
    max_tokens: int = 500
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    online: bool = False
    cache_prompt: bool = True
    max_budget: float = 0.05
    timeout: int = 60
    user_id: str = None
    client_id: str = "default"
    verbose: bool = False
    logs: bool = False
```

#### Fields

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

### Meta

The `Meta` class represents metadata for a request.

```python
class Meta(BaseModel):
    """Metadata for a request."""
    request_id: str = None
    model_used: str = None
    response_time_seconds: float = 0.0
    token_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
```

#### Fields

- `request_id` (`str`): The ID of the request.
- `model_used` (`str`): The model used for the request.
- `response_time_seconds` (`float`): The response time in seconds.
- `token_count` (`int`): The total number of tokens used.
- `input_tokens` (`int`): The number of input tokens.
- `output_tokens` (`int`): The number of output tokens.

### FullResponse

The `FullResponse` class represents a full response from an LLM.

```python
class FullResponse(BaseModel):
    """Full response from an LLM."""
    answer: Any
    meta: Meta
```

#### Fields

- `answer` (`Any`): The answer from the LLM.
- `meta` (`Meta`): The metadata for the request.

## Usage Models

### ModelUsage

The `ModelUsage` class represents usage statistics for a specific model.

```python
class ModelUsage(BaseModel):
    """Usage statistics for a specific model."""
    model_name: str
    model_provider: str
    total_input_tokens: int
    total_output_tokens: int
    total_cost: float
    last_used: datetime
```

#### Fields

- `model_name` (`str`): The name of the model.
- `model_provider` (`str`): The provider of the model.
- `total_input_tokens` (`int`): The total number of input tokens.
- `total_output_tokens` (`int`): The total number of output tokens.
- `total_cost` (`float`): The total cost in USD.
- `last_used` (`datetime`): The last time the model was used.

### RequestSummary

The `RequestSummary` class represents a summary of a request.

```python
class RequestSummary(BaseModel):
    """Summary of a request."""
    request_id: str
    timestamp: datetime
    model_name: str
    model_provider: str
    input_tokens: int
    output_tokens: int
    total_cost: float
    status: str
    error_message: Optional[str] = None
```

#### Fields

- `request_id` (`str`): The ID of the request.
- `timestamp` (`datetime`): The timestamp of the request.
- `model_name` (`str`): The name of the model.
- `model_provider` (`str`): The provider of the model.
- `input_tokens` (`int`): The number of input tokens.
- `output_tokens` (`int`): The number of output tokens.
- `total_cost` (`float`): The total cost in USD.
- `status` (`str`): The status of the request.
- `error_message` (`Optional[str]`): The error message, if any.

### ClientUsageData

The `ClientUsageData` class represents detailed usage data for a client.

```python
class ClientUsageData(BaseModel):
    """Detailed usage data for a client."""
    client_id: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost: float
    models_used: List[ModelUsage]
    recent_requests: List[RequestSummary]
```

#### Fields

- `client_id` (`str`): The client ID.
- `total_requests` (`int`): The total number of requests.
- `successful_requests` (`int`): The number of successful requests.
- `failed_requests` (`int`): The number of failed requests.
- `total_input_tokens` (`int`): The total number of input tokens.
- `total_output_tokens` (`int`): The total number of output tokens.
- `total_cost` (`float`): The total cost in USD.
- `models_used` (`List[ModelUsage]`): A list of models used.
- `recent_requests` (`List[RequestSummary]`): A list of recent requests.

### RequestDetails

The `RequestDetails` class represents detailed information about a specific request.

```python
class RequestDetails(BaseModel):
    """Detailed information about a specific request."""
    request_id: str
    timestamp: datetime
    model_name: str
    model_provider: str
    client_id: str
    user_id: str
    config_json: str
    request_raw: str
    request_json: str
    response_json: str
    response_raw: str
    input_tokens: int
    output_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    status: str
    error_message: Optional[str] = None
```

#### Fields

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
- `error_message` (`Optional[str]`): The error message, if any.

## Model Information

### ModelInfo

The `ModelInfo` class represents information about a model.

```python
class ModelInfo(BaseModel):
    """Information about a model."""
    id: str
    name: str
    provider: str
    input_cost_per_token: float
    output_cost_per_token: float
    max_tokens: int
```

#### Fields

- `id` (`str`): The ID of the model.
- `name` (`str`): The name of the model.
- `provider` (`str`): The provider of the model.
- `input_cost_per_token` (`float`): The cost per input token in USD.
- `output_cost_per_token` (`float`): The cost per output token in USD.
- `max_tokens` (`int`): The maximum number of tokens the model can handle.

### UniversalModelGetter

The `UniversalModelGetter` class is used to get information about models.

```python
class UniversalModelGetter:
    """Class for getting information about models."""
    def get_model_by_id(self, model_id: str) -> ModelInfo:
        """Get information about a model by its ID."""
```

#### Methods

##### get_model_by_id

```python
def get_model_by_id(self, model_id: str) -> ModelInfo:
    """Get information about a model by its ID."""
```

Gets information about a model by its ID.

**Parameters**:
- `model_id` (`str`): The ID of the model.

**Returns**:
- A `ModelInfo` instance with information about the model.

**Example**:
```python
from pydantic2.client.prices import UniversalModelGetter

getter = UniversalModelGetter()
model = getter.get_model_by_id("openrouter/openai/gpt-4o-mini-2024-07-18")
print(model)
```
