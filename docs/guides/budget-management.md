# Budget Management

Pydantic2 includes built-in budget management features to help you control costs when working with LLMs. This guide covers how to use these features.

## Setting a Budget

You can set a budget limit for each request in the `Request` configuration:

```python
from pydantic2 import Request, LiteLLMClient

config = Request(
    model="openrouter/openai/gpt-4o-mini-2024-07-18",
    answer_model=YourResponseModel,
    max_budget=0.05,  # Maximum $0.05 USD per request
    user_id="user123"  # Track budget by user
)

client = LiteLLMClient(config)
```

The `max_budget` parameter sets the maximum cost in USD for each request. If a request would exceed this budget, it will be rejected.

## User-Based Budget Tracking

You can track budgets by user by setting the `user_id` parameter:

```python
config = Request(
    model="openrouter/openai/gpt-4o-mini-2024-07-18",
    answer_model=YourResponseModel,
    max_budget=0.05,
    user_id="user123"  # Track budget by user
)
```

This allows you to track and limit spending on a per-user basis.

## Getting Budget Information

You can get information about the current budget:

```python
budget_info = client.get_budget_info()
print(budget_info)
```

The `budget_info` dictionary contains the following information:

- `max_budget`: The maximum budget for the request
- `estimated_cost`: The estimated cost of the request
- `remaining_budget`: The remaining budget after the request
- `budget_exceeded`: Whether the budget would be exceeded

## Calculating Costs

You can calculate the cost of a request after it has been made:

```python
cost = client.calculate_cost()
print(f"Request cost: ${cost:.6f}")
```

## Token Counting

You can count the tokens in a prompt before sending it:

```python
prompt_tokens = client.count_tokens()
print(f"Prompt token count: {prompt_tokens}")
```

You can also get the maximum number of tokens for the model:

```python
max_tokens = client.get_max_tokens_for_model()
print(f"Max tokens for model: {max_tokens}")
```

## Usage Tracking

You can track usage statistics:

```python
# Print usage information
client.print_usage_info()

# Get usage statistics
usage_stats = client.usage_tracker.get_usage_stats()
print(usage_stats)
```

## Complete Example

Here's a complete example of using the budget management features:

```python
from pydantic import BaseModel, Field
from typing import List
import uuid

from pydantic2 import LiteLLMClient, Request


# Define a custom response model
class UserDetail(BaseModel):
    """Model for extracting user details from text."""
    name: str = Field(description="The user's name")
    age: int = Field(description="The user's age")
    interests: List[str] = Field(description="List of user's interests")


def main():
    """Example using LiteLLM client with OpenAI and cost tracking."""
    # Generate a unique user_id for the example
    # In a real application, this would be the user ID from your system
    user_id = str(uuid.uuid4())
    print(f"Using user_id: {user_id}")

    # Set a budget for the user
    max_budget = 0.0001  # $0.0001 USD (very small budget)
    print(f"Setting budget: ${max_budget} USD (very small budget)")

    # Create a request configuration
    config = Request(
        model="openrouter/openai/gpt-4o-mini-2024-07-18",
        temperature=0.7,
        max_tokens=500,
        max_budget=max_budget,  # Setting a budget limit in USD
        client_id='demo',
        user_id=user_id,  # Set user_id for budgeting
        answer_model=UserDetail,  # The Pydantic model to use for the response
        verbose=True
    )

    # Initialize the client
    client = LiteLLMClient(config)

    client.msg.add_message_user("Describe who is David Copperfield")

    try:
        # Count tokens in the prompt before sending
        prompt_tokens = client.count_tokens()
        print(f"\nPrompt token count: {prompt_tokens}")

        # Get max tokens for the model
        max_tokens = client.get_max_tokens_for_model()
        print(f"Max tokens for model: {max_tokens}")

        # Get budget information
        budget_info = client.get_budget_info()
        print("\n=== Budget Information ===")
        for key, value in budget_info.items():
            if isinstance(value, float):
                print(f"{key}: ${value:.6f}")
            else:
                print(f"{key}: {value}")

        # Generate a response
        response: UserDetail = client.generate_response()

        # Print the structured response
        print("\nStructured Response:")
        print(response.model_dump())

        # Calculate cost after response
        cost = client.calculate_cost()
        print(f"\nRequest cost: ${cost:.6f}")

        # Print usage information
        client.print_usage_info()

        # Get usage statistics
        usage_stats = client.usage_tracker.get_usage_stats()
        print(f"Usage stats: {usage_stats}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
```

## Best Practices

Here are some best practices for budget management:

1. **Set reasonable budgets**: Start with a small budget and increase it as needed.
2. **Track usage by user**: Use the `user_id` parameter to track usage by user.
3. **Monitor costs**: Regularly check usage statistics to monitor costs.
4. **Use token counting**: Count tokens before sending requests to estimate costs.
5. **Handle budget exceptions**: Catch exceptions when the budget is exceeded.

## Next Steps

Now that you understand how to manage your budget, check out the [Structured Responses](structured-responses.md) guide to learn how to work with structured responses.
