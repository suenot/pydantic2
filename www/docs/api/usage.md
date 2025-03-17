# Usage Tracking API

Pydantic2 provides comprehensive usage tracking and analytics capabilities.

## Overview

The usage tracking system:
1. Records all API requests and responses
2. Tracks token usage and costs
3. Stores data in a local SQLite database
4. Provides usage statistics and reporting

## Requirements

To enable usage tracking, you must provide both:
- `client_id`: Identifier for your application
- `user_id`: Identifier for the end user

```python
from pydantic2 import PydanticAIClient

client = PydanticAIClient(
    model_name="openai/gpt-4o-mini-2024-07-18",
    client_id="my_app",      # Required for tracking
    user_id="user123"       # Required for tracking
)
```

## Accessing Usage Data

### Get Usage Statistics

```python
# Get overall statistics
stats = client.get_usage_stats()
print(f"Total Requests: {stats['total_requests']}")
print(f"Total Tokens: {stats['total_tokens']}")
print(f"Total Cost: ${stats['total_cost']:.4f}")

# Print detailed information
client.print_usage_info()

# Get per-model statistics
for model in stats['models']:
    print(f"\nModel: {model['model_name']}")
    print(f"Requests: {model['requests']}")
    print(f"Tokens: {model['tokens']}")
    print(f"Cost: ${model['cost']:.4f}")
```

### View Usage Database

Use the built-in CLI tool:
```bash
# View usage database in browser (http://localhost:8002)
pydantic2 --view-usage
```

## Database Schema

The usage database (`usage.db`) contains the following table:

### UsageLog

| Column | Type | Description |
|--------|------|-------------|
| id | AutoField | Unique identifier |
| client_id | CharField | Client identifier |
| user_id | CharField | User identifier |
| request_id | CharField | Request identifier |
| model_name | CharField | Model used |
| raw_request | TextField | Raw request data |
| raw_response | TextField | Raw response data |
| error_message | TextField | Error message (if any) |
| prompt_tokens | IntegerField | Tokens in prompt |
| completion_tokens | IntegerField | Tokens in completion |
| total_tokens | IntegerField | Total tokens used |
| total_cost | FloatField | Total cost in USD |
| response_time | FloatField | Response time in seconds |
| status | CharField | Request status |
| created_at | DateTimeField | Creation timestamp |
| updated_at | DateTimeField | Last update timestamp |

## Model Pricing

Model prices are automatically fetched from OpenRouter and stored in a local database (`models.db`).

### Viewing Model Prices

Use the CLI tool:
```bash
# View models database in browser (http://localhost:8001)
pydantic2 --view-models
```

### Price Updates

- Prices are automatically updated when initializing `PydanticAIClient`
- Updates occur if the last update was more than 24 hours ago
- Force updates by initializing with `force_update=True`

## Budget Management

Set budget limits and monitor usage:

```python
client = PydanticAIClient(
    client_id="my_app",
    user_id="user123",
    max_budget=1.0  # $1.00 USD limit
)

try:
    response = client.generate(...)
except BudgetExceeded as e:
    print(f"Budget exceeded: ${e.current_cost:.4f} / ${e.budget_limit:.4f}")
```

## Best Practices

1. Always provide `client_id` and `user_id` for accurate tracking
2. Monitor usage regularly using `get_usage_stats()`
3. Set appropriate budget limits for your use case
4. Use the CLI tools to analyze detailed usage patterns
5. Handle `BudgetExceeded` exceptions gracefully
