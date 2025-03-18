# Usage and Cost Management

Pydantic2 provides comprehensive usage tracking and cost management capabilities through two main components:

## Overview

1. [Model Pricing](model-pricing.md)
   - Model price management
   - Budget control
   - Cost calculation
   - Price updates

2. [Request Tracking](request-tracking.md)
   - Request lifecycle
   - Usage monitoring
   - Performance tracking
   - Usage analysis

## Quick Links

- [Model Pricing Documentation](model-pricing.md)
- [Request Tracking Documentation](request-tracking.md)
- [CLI Tools](../../cli.md)

## Basic Example

```python
from pydantic2 import PydanticAIClient

# Initialize client with usage tracking
client = PydanticAIClient(
    model_name="openai/gpt-4",
    client_id="my_app",
    user_id="user123",
    max_budget=10.0  # Optional budget limit
)

# Make API calls...
response = client.generate(...)

# Get usage statistics
stats = client.get_usage_stats()
print(f"Total cost: ${stats['total_cost']:.4f}")
```

!!! tip "Detailed Documentation"
    See [Model Pricing](model-pricing.md) and [Request Tracking](request-tracking.md) for detailed information about each component.
