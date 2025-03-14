# Usage Tracking

Pydantic2 provides detailed usage tracking features to help you monitor and manage your LLM usage. This guide covers how to use these features.

## Basic Usage Tracking

You can track usage statistics using the `usage_tracker` property of the `LiteLLMClient`:

```python
from pydantic2 import LiteLLMClient, Request

config = Request(
    model="openrouter/openai/gpt-4o-mini-2024-07-18",
    answer_model=YourResponseModel,
    client_id="my_application"  # Important for tracking
)

client = LiteLLMClient(config)

# After making some requests, get usage statistics
usage_stats = client.usage_tracker.get_usage_stats()
print(usage_stats)
```

The `client_id` parameter is important for tracking usage across multiple requests.

## Printing Usage Information

You can print usage information after a request:

```python
client.print_usage_info()
```

This will print information about the request, including:
- Model used
- Token count
- Cost
- Response time

## Structured Usage Tracking

Pydantic2 provides structured usage tracking with Pydantic models for easy integration:

```python
from pydantic2 import LiteLLMClient, Request
import json

# Initialize client with client_id for tracking
config = Request(
    model="openrouter/openai/gpt-4o-mini-2024-07-18",
    answer_model=YourResponseModel,
    client_id="my_application",  # Important for tracking
    verbose=True
)
client = LiteLLMClient(config)

# After making some requests, get detailed usage data
usage_data = client.usage_tracker.get_client_usage_data()

# Access structured data with type hints
print(f"Total requests: {usage_data.total_requests}")
print(f"Successful requests: {usage_data.successful_requests}")
print(f"Total cost: ${usage_data.total_cost:.6f}")

# Print models used
print("\nModels used:")
for model in usage_data.models_used:
    print(f"- {model.model_name}: {model.total_input_tokens + model.total_output_tokens} tokens, ${model.total_cost:.6f}")

# Print recent requests
print("\nRecent requests:")
for req in usage_data.recent_requests:
    print(f"- {req.timestamp}: {req.model_name}, Status: {req.status}, Cost: ${req.total_cost:.6f}")

# Convert to JSON for API responses or storage
usage_json = usage_data.model_dump_json(indent=2)
print(f"\nJSON representation:\n{usage_json}")

# Get usage for a different client
other_client_usage = client.usage_tracker.get_client_usage_data(client_id="other_app")
```

## Detailed Request Tracking

You can retrieve detailed information about specific requests:

```python
from pydantic2 import LiteLLMClient, Request

# Initialize client
config = Request(
    model="openrouter/openai/gpt-4o-mini-2024-07-18",
    answer_model=YourResponseModel,
    client_id="my_application",
    verbose=True
)
client = LiteLLMClient(config)

# Make a request and get its ID
response = client.generate_response()
request_id = client.meta.request_id
print(f"Current request_id: {request_id}")

# Get detailed information about a specific request
request_details = client.usage_tracker.get_request_details(request_id=request_id)

if request_details:
    # Access structured data with type hints
    print(f"Request ID: {request_details.request_id}")
    print(f"Timestamp: {request_details.timestamp}")
    print(f"Model: {request_details.model_name} ({request_details.model_provider})")
    print(f"Status: {request_details.status}")
    print(f"Tokens: {request_details.input_tokens} input, {request_details.output_tokens} output")
    print(f"Cost: ${request_details.total_cost:.6f}")

    # Convert to JSON for API responses or storage
    details_json = request_details.model_dump_json(indent=2)
    print(f"\nJSON representation:\n{details_json}")
else:
    print("No request details found")

# You can also retrieve details for any request ID
historical_request_id = "5f01f28b-1f9a-427a-ae69-b6c4842c0ee3"
historical_details = client.usage_tracker.get_request_details(request_id=historical_request_id)
```

## Building a Usage Dashboard

You can use the structured usage data to build a dashboard for monitoring usage:

```python
from fastapi import FastAPI, Depends, HTTPException, Security, Query
from fastapi.security import APIKeyHeader
from typing import Optional, List
import uvicorn

from pydantic2 import LiteLLMClient, Request
from pydantic2.client.usage.usage_class import ClientUsageData, RequestDetails

# Initialize a shared client for tracking usage
config = Request(
    model="openrouter/openai/gpt-4o-mini-2024-07-18",
    answer_model=None,  # Not needed for tracking only
    client_id="dashboard",
    verbose=False
)
client = LiteLLMClient(config)

# Create a FastAPI app
app = FastAPI(title="LLM Usage Dashboard")

# Security - API key authentication
API_KEY = "your-secret-api-key"  # In production, use environment variables
api_key_header = APIKeyHeader(name="X-API-Key")

def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

# Endpoint for getting a summary of usage across all clients
@app.get("/usage/summary", response_model=dict)
def get_usage_summary(api_key: str = Depends(verify_api_key)):
    """Get a summary of usage across all clients."""
    # Get all clients
    clients = ["client1", "client2", "dashboard"]  # In production, get this from your database

    total_cost = 0.0
    total_tokens = 0
    client_data = {}

    for client_id in clients:
        usage = client.usage_tracker.get_client_usage_data(client_id=client_id)
        total_cost += usage.total_cost
        total_tokens += usage.total_input_tokens + usage.total_output_tokens
        client_data[client_id] = {
            "requests": usage.total_requests,
            "cost": usage.total_cost,
            "tokens": usage.total_input_tokens + usage.total_output_tokens
        }

    return {
        "total_cost": total_cost,
        "total_tokens": total_tokens,
        "clients": client_data
    }

# Endpoint for getting detailed usage for a specific client
@app.get("/usage/client/{client_id}", response_model=ClientUsageData)
def get_client_usage(
    client_id: str,
    limit: Optional[int] = Query(10, description="Limit the number of recent requests"),
    api_key: str = Depends(verify_api_key)
):
    """Get detailed usage for a specific client."""
    usage = client.usage_tracker.get_client_usage_data(client_id=client_id)

    # Limit the number of recent requests
    if limit and limit < len(usage.recent_requests):
        usage.recent_requests = usage.recent_requests[:limit]

    return usage

# Endpoint for getting usage by model
@app.get("/usage/models", response_model=List[dict])
def get_model_usage(api_key: str = Depends(verify_api_key)):
    """Get usage broken down by model."""
    # Get all clients
    clients = ["client1", "client2", "dashboard"]  # In production, get this from your database

    model_data = {}

    for client_id in clients:
        usage = client.usage_tracker.get_client_usage_data(client_id=client_id)

        for model in usage.models_used:
            if model.model_name not in model_data:
                model_data[model.model_name] = {
                    "model_name": model.model_name,
                    "model_provider": model.model_provider,
                    "total_tokens": 0,
                    "total_cost": 0.0,
                    "clients": []
                }

            model_data[model.model_name]["total_tokens"] += model.total_input_tokens + model.total_output_tokens
            model_data[model.model_name]["total_cost"] += model.total_cost

            if client_id not in model_data[model.model_name]["clients"]:
                model_data[model.model_name]["clients"].append(client_id)

    return list(model_data.values())

# Run the app
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Key Features

The usage tracking system provides several key features:

1. **Structured Data**: All usage data is returned as typed Pydantic models, ensuring:
   - Strict typing and data validation
   - Autodocumentation through type annotations and field descriptions
   - IDE integration for autocompletion and hints

2. **Detailed Statistics**: The system provides comprehensive information on:
   - Total number of requests (successful and failed)
   - Total number of tokens (input and output)
   - Overall usage cost

3. **Model Breakdown**: The system offers separate statistics for each model used:
   - Token count per model
   - Usage cost per model
   - Last usage time

4. **Request History**: The system includes information on recent requests:
   - Timestamps
   - Execution status
   - Cost of each request
   - Error messages (if any)

5. **Easy Serialization**: All data can be easily converted to JSON for:
   - API responses
   - Database storage
   - Display in web interfaces

6. **Type Safety**: All fields have strict typing, helping to avoid errors when working with data.

## Next Steps

Now that you understand how to track usage, check out the [Examples](../examples/basic-usage.md) section to see more examples of using Pydantic2.
