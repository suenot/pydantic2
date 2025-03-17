from typing import List
from pydantic import BaseModel, Field
from src.pydantic2 import PydanticAIClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ChatResponse(BaseModel):
    """Response format for chat messages."""
    message: str = Field(description="The chat response message")
    sources: List[str] = Field(default_factory=list, description="Sources used in the response")
    confidence: float = Field(ge=0, le=1, description="Confidence score of the response")


def main():
    # Initialize client with usage tracking using context manager
    with PydanticAIClient(
        model_name="openai/gpt-4o-mini-2024-07-18",
        client_id="test_client",
        user_id="test_user",
        verbose=True,
        retries=3,
        online=True,
        max_budget=0.0003
    ) as client:
        try:
            # Set up the conversation with system message
            client.message_handler.add_message_system(
                "You are a helpful AI assistant. Be concise but informative."
            )

            # Add user message
            client.message_handler.add_message_user("What is the capital of France?")

            # Add structured data block (optional)
            client.message_handler.add_message_block(
                "CONTEXT",
                {
                    "topic": "Geography",
                    "region": "Europe",
                    "country": "France"
                }
            )

            # Generate response (synchronously)
            response: ChatResponse = client.generate(
                result_type=ChatResponse
            )

            # Print the response
            print("\nAI Response:")
            print(f"Message: {response.message}")
            print(f"Confidence: {response.confidence:.2f}")
            if response.sources:
                print("Sources:")
                for source in response.sources:
                    print(f"- {source}")

            # Print usage statistics
            stats = client.get_usage_stats()
            if stats:
                print("\nUsage Statistics:")
                print(f"Total Requests: {stats.get('total_requests', 0)}")
                print(f"Total Cost: ${stats.get('total_cost', 0):.4f}")

        except Exception as e:
            print(f"\nError: {str(e)}")


if __name__ == "__main__":
    main()
