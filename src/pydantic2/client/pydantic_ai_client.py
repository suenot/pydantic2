from typing import Optional, Dict, Any
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIModel
from .message_handler import MessageHandler
from .prices.prices_openrouter import OpenRouterPrices
from .usage.usage_info import UsageInfo
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class PydanticAIClient:
    """A simplified client for making AI requests using pydantic-ai."""

    def __init__(
        self,
        model_name: str = "openai/gpt-4o-mini-2024-07-18",
        base_url: str = "https://openrouter.ai/api/v1",
        api_key: Optional[str] = None,
        usage_db_path: Optional[str] = None
    ):
        """Initialize the client.

        Args:
            model_name: The model to use (default: gpt-4o-mini)
            base_url: The API base URL (default: OpenRouter)
            api_key: Optional API key (defaults to OPENROUTER_API_KEY env var)
            usage_db_path: Optional path to SQLite usage database
        """
        self.model_name = model_name
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            raise ValueError("API key must be provided or set in OPENROUTER_API_KEY env var")

        # Initialize components
        self.message_handler = MessageHandler()
        self.prices = OpenRouterPrices()
        self.usage_info = UsageInfo(usage_db_path) if usage_db_path else None

        # Initialize OpenAI model with provider
        self.model = OpenAIModel(
            model_name,
            provider=OpenAIProvider(
                base_url=base_url,
                api_key=self.api_key,
            ),
        )

    def clear_messages(self) -> None:
        """Clear all messages in the message handler."""
        self.message_handler.clear()

    def add_message(
        self,
        content: Any,
        role: str = "user",
        tag: Optional[str] = None
    ) -> None:
        """Add a message to the conversation.

        Args:
            content: The message content (can be str, dict, list, etc.)
            role: The role of the message ("user", "assistant", or "system")
            tag: Optional tag for block messages
        """
        if tag:
            self.message_handler.add_message_block(tag, content)
        elif role == "user":
            self.message_handler.add_message_user(content)
        elif role == "assistant":
            self.message_handler.add_message_assistant(content)
        elif role == "system":
            self.message_handler.add_message_system(content)
        else:
            raise ValueError(f"Invalid role: {role}")

    async def generate(
        self,
        result_type: type[BaseModel],
        system_prompt: Optional[str] = None,
        retries: int = 3
    ) -> Any:
        """Generate a response using the model.

        Args:
            result_type: The Pydantic model type for the response
            system_prompt: Optional system prompt to use
            retries: Number of retries on failure

        Returns:
            The generated response as an instance of result_type
        """
        # Create agent with the specified result type
        agent = Agent(
            self.model,
            result_type=result_type,
            retries=retries,
            system_prompt=system_prompt if system_prompt else ""
        )

        # Get formatted messages and combine them into a single prompt
        messages = self.message_handler.get_messages(result_type)
        prompt = "\n".join(str(msg.get("content", "")) for msg in messages)

        # Generate response
        result = await agent.run(prompt)

        # Update usage if tracking enabled
        if self.usage_info and hasattr(result, 'usage'):
            model_info = self.prices.get_model_info(self.model_name)
            if model_info:
                # Get token counts from usage info
                usage = result.usage
                request_tokens = getattr(usage, 'request_tokens', 0) or 0
                response_tokens = getattr(usage, 'response_tokens', 0) or 0

                self.usage_info.add_usage(
                    model=self.model_name,
                    prompt_tokens=request_tokens,
                    completion_tokens=response_tokens,
                    prompt_price=model_info.input_price_per_token * request_tokens,
                    completion_price=model_info.output_price_per_token * response_tokens
                )

        return result.data

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        model_info = self.prices.get_model_info(self.model_name)
        if model_info:
            return model_info.model_dump()
        return {}

    def get_usage_stats(self) -> Optional[Dict[str, Any]]:
        """Get usage statistics if tracking is enabled."""
        if not self.usage_info:
            return None
        return self.usage_info.get_usage_stats()
