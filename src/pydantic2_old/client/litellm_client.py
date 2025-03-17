import time
import os
from typing import TypeVar, Dict, Optional, Tuple, Any
import instructor
from litellm import completion
from litellm.utils import register_model
from litellm.utils import token_counter, get_max_tokens
from litellm.cost_calculator import cost_per_token, completion_cost
from litellm.budget_manager import BudgetManager
from pydantic import BaseModel

from ..utils.logger import logger
from .prices.get_models import UniversalModelGetter
from .models.base_models import Request, Meta
from .usage.usage_class import UsageClass
from .usage.usage_info import UsageInfo
from .message_handler import MessageHandler

T = TypeVar('T', bound=BaseModel)


class LiteLLMClient:
    """
    A simplified LiteLLM client that uses the instructor library for function calling.
    This client handles making requests to language models and parsing responses.
    Default provider is OpenRouter for accessing multiple models through one API.
    """

    def __init__(self, config: Request):
        """
        Initialize the LiteLLM client with configuration.

        Args:
            config: Request with model, messages, and other parameters
        """
        # Store configuration
        self.config = config

        # Initialize message handler
        self.msg = MessageHandler()

        # Set OpenRouter as default if API key is available
        if (os.environ.get("OPENROUTER_API_KEY")
                and not config.model.startswith("openrouter/")):
            self.config.model = f"openrouter/{config.model}"
            logger.info(f"Using OpenRouter for model: {self.config.model}")

        # Initialize metadata
        self.meta = Meta(
            request_timestamp=time.time(),
            model_used=config.model,
            cache_hit=None,
            response_time_seconds=None,
            token_count=None
        )

        # Set up instructor client with LiteLLM
        try:
            self.client = instructor.from_litellm(completion)
            logger.info("Instructor client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize instructor client: {e}")
            self.client = None

        # Store the last response for cost calculation
        self.last_response = None

        # Initialize usage tracker
        self.usage_tracker = UsageClass(config)

        # Initialize usage info handler
        self.usage_info = UsageInfo(self)

        # Configure LiteLLM settings
        if config.verbose:
            logger.info(f"Setting verbose mode: {config.verbose}")

        # Initialize budget manager if user_id is provided
        self.budget_manager = BudgetManager(project_name="litellm_client")

        if config.user_id:
            # Create budget for user if not exists and max_budget is set
            if (config.max_budget
                    and not self.budget_manager.is_valid_user(config.user_id)):
                self.budget_manager.create_budget(
                    total_budget=config.max_budget,
                    user=config.user_id,
                    duration="monthly"  # Default to monthly budget
                )
                logger.info(
                    f"Created budget for user {config.user_id}: ${config.max_budget}"
                )

        # Register model pricing information if available
        self._register_model_pricing(config.model)

        # Make sure messages are not empty
        if not self.config.messages:
            # Try to get messages from message handler
            messages = self.msg.get_messages(self.config.answer_model)
            if messages:
                # Convert to the expected type if needed
                # Note: Type compatibility issue is ignored here
                self.config.messages = messages  # type: ignore
                logger.info(
                    f"Using messages from message handler: {self.config.messages}"
                )

            # If still empty, raise error
            if not self.config.messages:
                raise ValueError("Messages cannot be empty")

        logger.info("LiteLLMClientSimplified initialized")

    def _register_model_pricing(self, model_name: str) -> None:
        """
        Register model pricing information with LiteLLM for accurate cost calculation.

        Args:
            model_name: The name of the model to register
        """
        try:
            # Initialize the universal model getter
            model_getter = UniversalModelGetter()

            # Try to get model information directly with the full model name
            model_info = model_getter.get_model_by_id(model_name)

            # If we found model information and it has pricing data
            if model_info is None or model_info.pricing is None:
                raise ValueError(f"Model {model_name} not found")

            # Create model cost dictionary for registration
            model_cost_dict = {
                model_name: {
                    "input_cost_per_token": model_info.pricing.input_price,
                    "output_cost_per_token": model_info.pricing.output_price,
                    "max_tokens": (
                        model_info.context_length or 4096  # Default if not specified
                    ),
                    "litellm_provider": model_info.provider,
                    "mode": "chat"  # Default to chat mode
                }
            }

            # Register the model with LiteLLM
            register_model(model_cost_dict)
            logger.info(
                f"Registered model pricing for {model_name}: "
                f"Input: ${model_info.pricing.input_price}, "
                f"Output: ${model_info.pricing.output_price}"
            )

        except Exception as e:
            logger.warning(f"Error registering model pricing: {str(e)}")

    @classmethod
    def register_all_models(cls) -> None:
        """
        Register all available models from the UniversalModelGetter with LiteLLM.
        This is useful for batch registration of models.
        """
        try:
            # Initialize the universal model getter
            model_getter = UniversalModelGetter()

            # Get all models
            all_models = model_getter.get_models()

            # Create a combined model cost dictionary
            model_cost_dict = {}

            # Add each model with pricing information to the dictionary
            for model in all_models.all_models:
                if model.pricing is not None:
                    model_id = model.id

                    # Add provider prefix if not already present
                    if model.provider and "/" not in model_id:
                        model_id = f"{model.provider}/{model_id}"

                    model_cost_dict[model_id] = {
                        "input_cost_per_token": model.pricing.input_price,
                        "output_cost_per_token": model.pricing.output_price,
                        "max_tokens": model.context_length or 4096,
                        "litellm_provider": model.provider,
                        "mode": "chat"
                    }

            # Register all models at once
            if model_cost_dict:
                register_model(model_cost_dict)
                logger.info(f"Registered {len(model_cost_dict)} models with LiteLLM")
            else:
                logger.warning("No models with pricing information found to register")

        except Exception as e:
            logger.warning(f"Error registering all models: {str(e)}")

    def generate_response(self) -> T:
        """
        Generate a structured response using LiteLLM and instructor.

        Returns:
            A structured response of type T (the answer_model specified in config)
        """
        # Start tracking the request in the database
        self.usage_tracker.start_request()

        # Start timing the request
        start_time = time.time()

        # Check budget if budget manager is enabled
        if self.budget_manager and self.config.user_id:
            current_cost = self.budget_manager.get_current_cost(
                user=self.config.user_id
            )
            total_budget = self.budget_manager.get_total_budget(
                user=self.config.user_id
            )

            # Project cost for this request
            try:
                projected_cost = self.budget_manager.projected_cost(
                    model=self.config.model,
                    messages=self.config.messages,
                    user=self.config.user_id
                )
                logger.info(f"Projected cost for this request: ${projected_cost:.6f}")

                # Check if this request would exceed the budget
                if current_cost + projected_cost > total_budget:
                    error_msg = (
                        f"Budget exceeded for user {self.config.user_id}. "
                        f"Current cost: ${current_cost:.6f}, "
                        f"Projected cost: ${projected_cost:.6f}, "
                        f"Total budget: ${total_budget:.6f}"
                    )
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                logger.info(
                    f"Budget check passed. Current: ${current_cost:.6f}, "
                    f"Projected: ${projected_cost:.6f}, "
                    f"Total: ${total_budget:.6f}"
                )
            except Exception as e:
                # If the error is related to budget exceeded, raise it
                if "Budget exceeded" in str(e):
                    raise
                logger.success(
                    f"Could not project cost: {str(e)}. "
                    f"Proceeding without budget check."
                )

        # Prepare model name (add :online suffix if needed)
        model_name = self.config.model
        if self.config.online and not model_name.endswith(":online"):
            model_name = f"{model_name}:online"
            logger.success(f"Using online model: {model_name}")

        # Prepare fallback models
        models_to_try = [model_name] + (self.config.fallbacks or [])

        # Try each model in sequence until one succeeds
        last_error = None
        for model in models_to_try:
            try:
                logger.info(f"Sending request to model: {model}")

                # Add JSON instruction if not present
                messages = self.config.messages.copy()
                if not any(m.get("role") == "system" for m in messages):
                    messages.insert(0, {
                        "role": "system",
                        "content": "Return your response as valid JSON."
                    })

                # Check if we have a valid instructor client and output class
                if not self.client:
                    logger.warning(
                        "Instructor client is not initialized, trying to initialize it again"
                    )
                    try:
                        self._init_instructor()
                        if not self.client:
                            logger.error("Failed to initialize instructor client")
                            raise ValueError("Failed to initialize instructor client")
                    except Exception as e:
                        logger.error(
                            f"Error initializing instructor client: {str(e)}"
                        )
                        raise ValueError(
                            f"Failed to initialize instructor client: {str(e)}"
                        )

                if not self.config.answer_model:
                    logger.error("No answer model provided")
                    raise ValueError("No answer model provided")

                # Use instructor for structured output
                logger.info("Using instructor for structured output")
                try:
                    messages = self.msg.get_messages(self.config.answer_model)

                    # Get raw completion first
                    raw_response = completion(
                        model=model,
                        messages=messages,
                    )

                    # Store for cost calculation
                    self.last_response = raw_response

                    # Extract the response content
                    if hasattr(raw_response, 'choices') and raw_response.choices:
                        content = raw_response.choices[0].message.content
                    else:
                        raise ValueError("No content in response")

                    # Parse the content into the answer model
                    if self.config.answer_model:
                        response = self.config.answer_model.model_validate_json(content)
                    else:
                        raise ValueError("No answer model specified")

                    # Update metadata
                    self.meta.model_used = model
                    response_time = time.time() - start_time
                    self.meta.response_time_seconds = round(response_time, 3)

                    # Update token count if available
                    if hasattr(raw_response, 'usage'):
                        usage = raw_response.usage
                        if hasattr(usage, 'total_tokens'):
                            self.meta.token_count = usage.total_tokens
                        elif isinstance(usage, dict) and 'total_tokens' in usage:
                            self.meta.token_count = usage['total_tokens']

                    # Log success
                    usage_info = self.get_usage_info()
                    self.usage_tracker.log_success(
                        response_json=response.model_dump(),
                        usage_info=usage_info
                    )

                    return response

                except Exception as e:
                    logger.error(f"Error processing response: {str(e)}")
                    raise

            except Exception as e:
                logger.warning(f"Error with model {model}: {str(e)}")
                last_error = e
                continue

        # If we get here, all models failed
        error_msg = f"All models failed. Last error: {str(last_error)}"
        logger.error(error_msg)

        # Log error in the database
        self.usage_tracker.log_error(error_msg)

        raise ValueError(error_msg)

    def get_budget_info(self) -> Dict[str, Any]:
        """
        Get budget information for the current user.

        Returns:
            Dictionary with budget information
        """
        if not self.budget_manager or not self.config.user_id:
            return {
                "budget_enabled": False,
                "reason": "Budget manager not enabled or user_id not provided"
            }

        try:
            user = self.config.user_id
            current_cost = self.budget_manager.get_current_cost(user=user)
            total_budget = self.budget_manager.get_total_budget(user=user)

            return {
                "budget_enabled": True,
                "user_id": user,
                "current_cost": current_cost,
                "total_budget": total_budget,
                "remaining_budget": total_budget - current_cost,
                "budget_used_percent": (current_cost / total_budget) * 100
                if total_budget > 0 else 0
            }
        except Exception as e:
            return {
                "budget_enabled": True,
                "error": str(e)
            }

    def count_tokens(self, text: Optional[str] = None) -> int:
        """
        Count tokens for a given text or the current messages.

        Args:
            text: Optional text to count tokens for. If None, uses the current messages.

        Returns:
            Number of tokens in the text or messages
        """
        if text is not None:
            return token_counter(model=self.config.model, text=text)
        elif self.config.messages:
            return token_counter(model=self.config.model, messages=self.config.messages)
        else:
            return 0

    def get_token_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int
    ) -> Tuple[float, float]:
        """
        Get the cost per token for prompt and completion.

        Args:
            prompt_tokens: Number of tokens in the prompt
            completion_tokens: Number of tokens in the completion

        Returns:
            Tuple of (prompt_cost, completion_cost) in USD
        """
        return cost_per_token(
            model=self.config.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens
        )

    def calculate_cost(self) -> float:
        """
        Calculate the cost of the last completion call.

        Returns:
            Cost in USD for the last completion call
        """
        if self.last_response:
            return completion_cost(completion_response=self.last_response)
        elif self.config.messages:
            # Estimate cost based on messages if no response yet
            prompt_text = " ".join([m.get("content", "") for m in self.config.messages])
            return completion_cost(
                model=self.config.model,
                prompt=prompt_text,
                completion=""  # No completion yet
            )
        return 0.0

    def get_max_tokens_for_model(self) -> int:
        """
        Get the maximum number of tokens allowed for the current model.

        Returns:
            Maximum number of tokens for the model
        """
        # Extract the base model name if using openrouter
        model_name = self.config.model
        if model_name.startswith("openrouter/"):
            model_name = model_name.split("/", 1)[1]

        max_tokens = get_max_tokens(model_name)
        return max_tokens if max_tokens is not None else 0

    def get_usage_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get usage statistics from the database.

        Args:
            user_id: Optional user ID to filter by

        Returns:
            Dictionary with usage statistics
        """
        return self.usage_tracker.get_usage_stats(user_id)

    def get_usage_info(self) -> Dict[str, Any]:
        """
        Get comprehensive usage information for the last request.

        Returns:
            Dictionary with token counts, costs, and other usage information
        """
        return self.usage_info.get_usage_info()

    def print_usage_info(self) -> None:
        """
        Print usage information for the last request.
        """
        self.usage_info.print_usage_info()

    def update_cost(
        self,
        completion_obj: Optional[Any] = None,
    ):
        """Update cost tracking"""
        if self.budget_manager and self.config.user_id:
            try:
                # Используем стандартный метод update_cost с доступными параметрами
                if completion_obj is not None:
                    self.budget_manager.update_cost(
                        completion_obj=completion_obj,
                        user=self.config.user_id
                    )
                # Если нет completion_obj, но есть другие параметры, логируем это
                else:
                    logger.info("Manual cost update not supported. Use completion_obj parameter.")
            except Exception as e:
                logger.error(f"Error updating cost: {str(e)}")

    def _init_instructor(self):
        """Initialize instructor client if available"""
        try:
            # Проверяем, что модуль instructor импортирован
            import instructor

            # Проверяем, что completion доступен
            if completion is None:
                logger.error("LiteLLM completion is not available")
                self.client = None
                return

            # Инициализируем клиент
            self.client = instructor.from_litellm(completion)

            # Проверяем, что клиент был успешно инициализирован
            if self.client is None:
                logger.error("Failed to initialize instructor client")
                return

            # Проверяем, что у клиента есть необходимые атрибуты
            if (not hasattr(self.client, 'chat')
                    or not hasattr(self.client.chat, 'completions')):
                logger.error(
                    "Instructor client does not have chat.completions attribute"
                )
                self.client = None
                return

            if not hasattr(self.client.chat.completions, 'create'):
                logger.error(
                    "Instructor client does not have chat.completions.create method"
                )
                self.client = None
                return

            logger.info("Instructor client initialized successfully")

        except ImportError:
            logger.warning("Instructor not installed. Run 'pip install instructor'")
            self.client = None
        except Exception as e:
            logger.error(f"Error initializing instructor client: {str(e)}")
            self.client = None
