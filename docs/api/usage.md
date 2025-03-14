# Usage API Reference

This page provides detailed information about the usage API in Pydantic2.

## UsageClass

The `UsageClass` class is the main class for tracking usage statistics.

### Constructor

```python
def __init__(self, config: Request):
    """Initialize the UsageClass with a configuration."""
```

#### Parameters

- `config` (`Request`): The configuration for the usage tracker.

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

#### log_request

```python
def log_request(
    self,
    request_id: str,
    model_name: str,
    model_provider: str,
    client_id: str,
    user_id: str,
    config_json: str,
    request_raw: str,
    request_json: str,
    response_json: str,
    response_raw: str,
    input_tokens: int,
    output_tokens: int,
    input_cost: float,
    output_cost: float,
    status: str,
    error_message: str = None
) -> None:
    """Log a request."""
```

Logs a request.

**Parameters**:
- `request_id` (`str`): The ID of the request.
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
- `status` (`str`): The status of the request.
- `error_message` (`str`, optional): The error message, if any.

**Example**:
```python
client.usage_tracker.log_request(
    request_id="123",
    model_name="gpt-4",
    model_provider="openai",
    client_id="my_app",
    user_id="user123",
    config_json="{}",
    request_raw="",
    request_json="{}",
    response_json="{}",
    response_raw="",
    input_tokens=10,
    output_tokens=20,
    input_cost=0.0001,
    output_cost=0.0002,
    status="success"
)
```

## UsageLogger

The `UsageLogger` class is a simpler class for logging usage statistics.

### Constructor

```python
def __init__(self, config: Request):
    """Initialize the UsageLogger with a configuration."""
```

#### Parameters

- `config` (`Request`): The configuration for the usage logger.

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
usage_stats = logger.get_usage_stats()
```

#### log_request

```python
def log_request(
    self,
    request_id: str,
    model_name: str,
    model_provider: str,
    client_id: str,
    user_id: str,
    input_tokens: int,
    output_tokens: int,
    input_cost: float,
    output_cost: float,
    status: str,
    error_message: str = None
) -> None:
    """Log a request."""
```

Logs a request.

**Parameters**:
- `request_id` (`str`): The ID of the request.
- `model_name` (`str`): The name of the model.
- `model_provider` (`str`): The provider of the model.
- `client_id` (`str`): The client ID.
- `user_id` (`str`): The user ID.
- `input_tokens` (`int`): The number of input tokens.
- `output_tokens` (`int`): The number of output tokens.
- `input_cost` (`float`): The cost of input tokens.
- `output_cost` (`float`): The cost of output tokens.
- `status` (`str`): The status of the request.
- `error_message` (`str`, optional): The error message, if any.

**Example**:
```python
logger.log_request(
    request_id="123",
    model_name="gpt-4",
    model_provider="openai",
    client_id="my_app",
    user_id="user123",
    input_tokens=10,
    output_tokens=20,
    input_cost=0.0001,
    output_cost=0.0002,
    status="success"
)
```

## Usage Models

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
