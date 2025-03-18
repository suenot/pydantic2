# Model Pricing and Cost Management

Pydantic2 provides comprehensive model pricing and cost management through the `ModelPriceManager` class.

## Cost Management Architecture

```mermaid
graph TD
    subgraph Price Management
        A[Model Request] --> B[ModelPriceManager]
        B --> C[Get Model Price]
        B --> D[Check Budget]
    end

    subgraph Cost Calculation
        C --> E[Input Cost]
        C --> F[Output Cost]
        E --> G[Total Cost]
        F --> G
    end

    subgraph Budget Control
        G --> H{Check Limits}
        H -->|Within Budget| I[Allow Request]
        H -->|Exceeded| J[Block Request]
    end

    style B fill:#f96
    style C fill:#9cf
    style D fill:#f96
    style H fill:#f96
```

## Price Updates Flow

```mermaid
sequenceDiagram
    participant Manager as PriceManager #f96
    participant Cache as PriceCache #9cf
    participant DB as ModelsDB #bbf
    participant API as OpenRouter #ddd

    Note over Manager,API: Daily Price Update
    Manager->>API: Fetch Latest Prices
    API-->>Manager: Price List
    Manager->>DB: Store Prices
    Manager->>Cache: Update Cache

    Note over Manager,API: Request Processing
    Manager->>Cache: Check Price
    alt Cache Hit
        Cache-->>Manager: Return Price
    else Cache Miss
        Manager->>DB: Fetch Price
        DB-->>Manager: Price Info
        Manager->>Cache: Update Cache
    end
```

## Quick Start

```python
from pydantic2.client.usage.model_prices import ModelPriceManager

# Initialize price manager
price_manager = ModelPriceManager()

# Get model price
model_price = price_manager.get_model_price("openai/gpt-4")
print(f"Input cost per token: ${model_price.get_input_cost()}")
print(f"Output cost per token: ${model_price.get_output_cost()}")

# Check budget
budget_ok = price_manager.check_budget(
    model_name="openai/gpt-4",
    input_tokens=100,
    output_tokens=50,
    budget_limit=0.1
)
```

## Model Price Configuration

```python
from pydantic2.client.usage.model_prices import ModelPrice

# Define custom model price
custom_price = ModelPrice(
    model_id="custom/model",
    input_cost_per_token=0.0001,
    output_cost_per_token=0.0002,
    context_length=4096,
    max_output_tokens=1000
)

# Register custom model
price_manager.register_model(custom_price)
```

## Best Practices

1. **Regular Updates**: Keep model prices up to date
2. **Budget Limits**: Set appropriate budget limits per client
3. **Custom Models**: Register custom models with accurate pricing
4. **Cache Management**: Monitor and clear price cache when needed
5. **Cost Monitoring**: Track costs across different models

!!! tip "Price Updates"
    Model prices are automatically updated daily from OpenRouter. You can also trigger manual updates:
    ```python
    price_manager.update_from_openrouter()
    ```
