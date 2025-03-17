from typing import List
from pydantic import BaseModel, Field
from src.pydantic2.client.pydantic_ai_client import PydanticAIClient
import asyncio
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()


class ChatResponse(BaseModel):
    """Response format for chat messages."""
    message: str = Field(description="The chat response message")
    sources: List[str] = Field(default_factory=list, description="Sources used in the response")
    confidence: float = Field(ge=0, le=1, description="Confidence score of the response")


async def main():

    THIS_DIR = Path(__file__).parent
    # Initialize client with usage tracking
    client = PydanticAIClient(
        model_name="openai/gpt-4o-mini-2024-07-18",
        usage_db_path=str(THIS_DIR / "chat_usage.db"),
    )

    # Set up the conversation
    client.add_message(
        "You are a helpful AI assistant. Be concise but informative.",
        role="system"
    )

    # Add some example messages
    client.add_message("What is the capital of France?", role="user")

    # Generate response
    response: ChatResponse = await client.generate(
        result_type=ChatResponse,
        system_prompt="You are a helpful AI assistant. Be concise but informative."
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
        print(f"Total Requests: {stats['total_requests']}")
        print(f"Total Cost: ${stats['total_price']:.4f}")

    # Get model information
    model_info = client.get_model_info()
    if model_info:
        print("\nModel Information:")
        print(f"Input Price per Token: ${model_info.get('input_price_per_token', 0):.6f}")
        print(f"Output Price per Token: ${model_info.get('output_price_per_token', 0):.6f}")
        max_tokens = model_info.get('max_tokens')
        if max_tokens:
            print(f"Max Tokens: {max_tokens}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nChat session ended by user.")
    except Exception as e:
        print(f"\nError: {str(e)}")
