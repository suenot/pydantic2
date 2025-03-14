from pydantic import BaseModel, Field
from typing import List
import json
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

    client_id = 'demo'
    # Create a request configuration
    config = Request(
        model="openrouter/openai/gpt-4o-mini-2024-07-18",
        temperature=0.7,
        max_tokens=500,
        max_budget=max_budget,  # Setting a budget limit in USD
        client_id=client_id,
        user_id=user_id,  # Set user_id for budgeting
        answer_model=UserDetail,  # The Pydantic model to use for the response
        verbose=False,
        logs=False,
        online=True,
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
        print(json.dumps(response.model_dump(), indent=2))

        # Print model information
        print(f"\nModel used: {client.meta.model_used}")
        print(f"Response time: {client.meta.response_time_seconds:.3f} seconds")

        # Get token count directly from metadata
        token_count = client.meta.token_count
        print(f"Total token count: {token_count}")

        client.print_usage_info()

        usage_stats = client.usage_tracker.get_usage_stats()
        print(f"Usage stats: {usage_stats}")

        # print by client_id
        client_usage_data = client.usage_tracker.get_client_usage_data(client_id=client_id)
        print(client_usage_data.model_dump_json(indent=2))

        # get current request_id
        request_id = "5f01f28b-1f9a-427a-ae69-b6c4842c0ee3"
        print(f"Current request_id: {request_id}")

        # get request_id usage data
        request_id_usage_data = client.usage_tracker.get_request_details(request_id=request_id)
        if request_id_usage_data:
            print(request_id_usage_data.model_dump_json(indent=2))
        else:
            print("No request details found")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
