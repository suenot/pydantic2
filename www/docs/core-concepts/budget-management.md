# Budget Management

Pydantic2 provides built-in budget management capabilities to help control API costs.

## Requirements

To enable budget management and usage tracking, you **must** provide both:
- `client_id`: Identifier for your application
- `user_id`: Identifier for the end user

Without these identifiers, usage tracking and budget management will not function.

## Basic Setup

```python
from pydantic2 import PydanticAIClient

client = PydanticAIClient(
    model_name="openai/gpt-4o-mini-2024-07-18",
    client_id="my_app",      # Required for tracking
    user_id="user123",       # Required for tracking
    max_budget=10.0          # Optional: Set $10 limit
)
```

## Tracking Usage

Once configured, you can monitor usage:

```python
# Get current usage statistics
stats = client.get_usage_stats()
print(f"Total cost: ${stats.get('total_cost', 0):.4f}")

# Print detailed usage information
client.print_usage_info()
```

## Budget Limits

When `max_budget` is set:

1. Each request checks the current total cost
2. If a request would exceed the budget, `BudgetExceeded` is raised
3. The budget is checked both before and after each request

```python
try:
    response: MyModel = client.generate(result_type=MyModel)
except BudgetExceeded as e:
    print(f"Budget limit reached: {e}")
```

## Usage Database

Usage data is stored in a local SQLite database, tracking:

- Token counts
- Costs per request
- Model usage
- Response times
- Success/error status

View the database using the CLI tool:
```bash
pydantic2 --view-usage
```

## Per-Model Statistics

Get detailed statistics per model:

```python
stats = client.get_usage_stats()
for model in stats.get('models', []):
    print(f"Model: {model['model_name']}")
    print(f"Requests: {model['requests']}")
    print(f"Tokens: {model['tokens']}")
    print(f"Cost: ${model['cost']:.4f}")
```

## Best Practices

1. Always provide `client_id` and `user_id` for accurate tracking
2. Set appropriate budget limits for your use case
3. Monitor usage regularly using `get_usage_stats()`
4. Use the CLI tools to analyze detailed usage patterns
5. Handle `BudgetExceeded` exceptions gracefully
