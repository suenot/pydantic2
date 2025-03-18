from typing import Optional, Dict, Any
from pydantic import BaseModel, ValidationError as PydanticValidationError
from pydantic_ai import Agent
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.usage import Usage
from pydantic_ai.settings import ModelSettings
from .message_handler import MessageHandler
from .usage.usage_info import UsageInfo
from .usage.model_prices import ModelPriceManager
from ..utils.logger import logger
from .exceptions import (
    BudgetExceeded, ErrorGeneratingResponse, ModelNotFound,
    InvalidConfiguration, AuthenticationError, RateLimitExceeded,
    ValidationError, NetworkError
)
import os
from dotenv import load_dotenv
import time
import uuid
import asyncio
import aiohttp
from datetime import datetime, timezone

# Load environment variables
load_dotenv()


class PydanticAIClient:
    """A simplified client for making AI requests using pydantic-ai."""

    def __init__(
        self,
        model_name: str = "openai/gpt-4o-mini-2024-07-18",
        base_url: str = "https://openrouter.ai/api/v1",
        api_key: Optional[str] = None,
        client_id: Optional[str] = None,
        user_id: Optional[str] = None,
        verbose: bool = False,
        retries: int = 3,
        online: bool = False,
        max_budget: Optional[float] = None,
        model_settings: Optional[ModelSettings] = None,
    ):
        """Initialize the client."""
        try:
            # Set verbose mode for logger
            logger.set_verbose(verbose)

            # Store original model name for price lookups
            self.base_model_name = model_name.split(':')[0]  # Remove :online suffix if present

            # Add online suffix if needed
            if online and not model_name.endswith(':online'):
                model_name = f"{model_name}:online"
                # Always show bright message for online mode regardless of verbose
                logger.success("🌐 Online search mode is enabled - AI will use real-time internet data!")

            self.model_name = model_name
            self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
            if not self.api_key:
                raise InvalidConfiguration(
                    "API key must be provided or set in OPENROUTER_API_KEY env var",
                    "api_key"
                )

            self.message_handler = MessageHandler()
            self.usage_info = UsageInfo(client_id, user_id)
            self.price_manager = ModelPriceManager()
            self.verbose = verbose
            self.retries = retries
            self.user_id = user_id
            self.max_budget = max_budget
            self.model_settings = model_settings

            # Force update prices if they haven't been fetched yet
            logger.debug("Checking model prices...")
            self.price_manager.update_from_openrouter(force=True)

            try:
                self.model = OpenAIModel(
                    model_name,
                    provider=OpenAIProvider(
                        base_url=base_url,
                        api_key=self.api_key,
                    ),
                )
            except Exception as e:
                raise ModelNotFound(model_name) from e

            logger.info(f"Initialized PydanticAIClient with model: {model_name}")
            if max_budget:
                logger.info(f"Maximum budget set to ${max_budget:.2f}")

        except Exception as e:
            if isinstance(e, (InvalidConfiguration, ModelNotFound)):
                raise
            raise InvalidConfiguration(str(e)) from e

    def clear_messages(self) -> None:
        """Clear all messages in the message handler."""
        self.message_handler.clear()
        if self.verbose:
            logger.info("Cleared all messages")

    def _calculate_token_usage(self, result) -> Usage:
        """Calculate token usage from result."""
        usage = Usage()
        if hasattr(result, 'usage'):
            result_usage = result.usage()
            usage.incr(result_usage)
            if self.verbose:
                logger.info(f"Usage - Request: {usage.request_tokens}, Response: {usage.response_tokens}, Total: {usage.total_tokens}")
        return usage

    def _calculate_cost(self, usage: Usage) -> float:
        """Calculate cost based on token usage."""
        if not usage.total_tokens:
            return 0.0

        # Use base model name for price lookup
        model_price = self.price_manager.get_model_price(self.base_model_name)
        if not model_price:
            logger.warning(f"No price information found for model {self.base_model_name}")
            return 0.0

        # Get actual float values from the model price fields
        input_cost = (usage.request_tokens or 0) * model_price.get_input_cost()
        output_cost = (usage.response_tokens or 0) * model_price.get_output_cost()
        total_cost = input_cost + output_cost

        logger.debug(f"Cost calculation - Input: ${input_cost:.4f}, Output: ${output_cost:.4f}, Total: ${total_cost:.4f}")

        return total_cost

    def _check_budget(self):
        """Check if user has exceeded their budget."""
        if self.max_budget is not None:
            current_usage = self.usage_info.get_usage_stats()
            current_cost = current_usage.get('total_cost', 0) if current_usage else 0

            logger.debug(f"Current cost: ${current_cost:.4f}, Budget limit: ${self.max_budget:.4f}")

            if current_cost >= self.max_budget:
                raise BudgetExceeded(current_cost, self.max_budget)

    def _log_request(self, request_id: str):
        """Log the request."""
        if self.usage_info:
            self.usage_info.log_request(
                model_name=self.model_name,
                raw_request=self.message_handler.format_raw_request(),
                request_id=request_id
            )

    def _log_response(self, result: Any, usage: Usage, response_time: float, request_id: str):
        """Log the response and update usage statistics."""
        if not self.usage_info:
            return

        usage_dict = {
            'prompt_tokens': usage.request_tokens or 0,
            'completion_tokens': usage.response_tokens or 0,
            'total_tokens': usage.total_tokens or 0,
            'total_cost': self._calculate_cost(usage)
        }

        self.usage_info.log_response(
            raw_response=str(result.data),
            usage_info=usage_dict,
            response_time=response_time,
            request_id=request_id
        )

        # Check budget after response
        if self.max_budget is not None and self.user_id:
            current_usage = self.usage_info.get_usage_stats()
            if current_usage and current_usage.get('total_cost', 0) > self.max_budget:
                if self.verbose:
                    logger.warning(f"User {self.user_id} has exceeded their budget limit of ${self.max_budget:.2f}")

    async def _generate_async(
        self,
        result_type: type[BaseModel],
        retries: Optional[int] = None,
    ) -> Any:
        """Async implementation of generate method."""
        request_id = str(uuid.uuid4())
        if self.verbose:
            logger.info(f"Generating response for request {request_id}")

        # Check budget before making the request
        self._check_budget()
        self.message_handler.add_model_schema(result_type)

        self._log_request(request_id)
        start_time = time.perf_counter()

        try:

            formatted_prompt = self.message_handler.get_formatted_prompt()

            if formatted_prompt:
                logger.info("Formatted prompt:")
                logger.info(formatted_prompt)

            logger.info("--------------------------------")

            agent = Agent(
                self.model,
                result_type=result_type,
                retries=retries or self.retries,
                # system_prompt=system_prompt
            )

            result = await agent.run(
                user_prompt=formatted_prompt,
                model_settings=self.model_settings,
            )

            # Clear the message handler after the response
            self.message_handler.clear()

            response_time = time.perf_counter() - start_time
            if self.verbose:
                logger.info(f"Response generated in {response_time:.3f} seconds")
                logger.debug(f"Result data: {result.data}")

            usage = self._calculate_token_usage(result)
            self._log_response(result, usage, response_time, request_id)

            # Check budget after the response
            self._check_budget()

            try:
                # Validate response against the model
                if not isinstance(result.data, result_type):
                    result_type.model_validate(result.data)
                return result.data
            except PydanticValidationError as e:
                raise ValidationError(
                    "Response validation failed",
                    model=result_type,
                    errors=e.errors()
                ) from e

        except aiohttp.ClientError as e:
            error = NetworkError(str(e))
            if self.usage_info:
                self.usage_info.log_error(
                    error_message=str(error),
                    response_time=time.perf_counter() - start_time,
                    request_id=request_id
                )

            # Clear the message handler after the response
            self.message_handler.clear()

            raise error

        except Exception as e:

            # Clear the message handler after the response
            self.message_handler.clear()

            if isinstance(e, (BudgetExceeded, ValidationError, NetworkError)):
                raise

            error = ErrorGeneratingResponse(
                "Failed to generate response",
                e,
                {
                    "request_id": request_id,
                    "model": self.model_name,
                    "response_time": time.perf_counter() - start_time
                }
            )

            if self.verbose:
                logger.error(f"Error generating response: {str(error)}")
            if self.usage_info:
                self.usage_info.log_error(
                    error_message=str(error),
                    response_time=time.perf_counter() - start_time,
                    request_id=request_id
                )
            raise error

    def generate(
        self,
        result_type: type[BaseModel],
        retries: Optional[int] = None,
    ) -> Any:
        """Synchronous version of generate method."""
        try:
            return asyncio.run(self._generate_async(result_type, retries))
        except KeyboardInterrupt:
            if self.verbose:
                logger.info("Generation interrupted by user")
            raise
        except Exception as e:
            if self.verbose:
                logger.error(f"Error in generate: {str(e)}")
            raise

    async def generate_async(
        self,
        result_type: type[BaseModel],
        retries: Optional[int] = None,
    ) -> Any:
        """Asynchronous version of generate method."""
        try:
            return await self._generate_async(result_type, retries)
        except Exception as e:
            if self.verbose:
                logger.error(f"Error in generate_async: {str(e)}")
            raise

    def get_usage_stats(self) -> Optional[Dict[str, Any]]:
        """Get usage statistics if tracking is enabled."""
        if not self.usage_info:
            return None
        stats = self.usage_info.get_usage_stats()
        if self.verbose:
            logger.info(f"Usage statistics: {stats}")
        return stats

    def print_usage_info(self):
        """Print usage information."""
        stats = self.get_usage_stats()
        if not stats:
            logger.warning("No usage statistics available")
            return

        logger.info("\nUsage Statistics:")
        logger.info(f"Total Requests: {stats['total_requests']}")
        logger.info(f"Total Tokens: {stats['total_tokens']}")
        logger.info(f"Total Cost: ${stats['total_cost']:.4f}")

        if stats.get('models'):
            logger.info("\nPer-Model Statistics:")
            for model in stats['models']:
                logger.info(f"  {model['model_name']}:")
                logger.info(f"    Requests: {model['requests']}")
                logger.info(f"    Tokens: {model['tokens']}")
                logger.info(f"    Cost: ${model['cost']:.4f}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def close(self):
        """Close all resources."""
        if hasattr(self, 'usage_info'):
            self.usage_info.close()

    def __del__(self):
        """Cleanup when the client is destroyed."""
        self.close()

    def _process_response(self, response: Any) -> str:
        """Process OpenAI API response."""
        if not response.choices:
            raise ValueError("No choices in response")

        # Use current time if created timestamp is not available
        created_ts = response.created or int(time.time())
        timestamp = datetime.fromtimestamp(created_ts, tz=timezone.utc)

        # Extract the message content
        message = response.choices[0].message
        if not message or not message.content:
            raise ValueError("No content in response message")

        return message.content
