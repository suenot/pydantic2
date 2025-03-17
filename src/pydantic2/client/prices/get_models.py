import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field

from src.pydantic2.client.prices.prices_openrouter import OpenRouterModelUpdater, OpenRouterModel


class UniversalModelPricing(BaseModel):
    """Universal pricing information for a model."""
    input_price: float = Field(
        description="Cost per input/prompt token in USD"
    )
    output_price: float = Field(
        description="Cost per output/completion token in USD"
    )
    image_price: Optional[float] = Field(
        None, description="Cost per image in USD (if applicable)"
    )
    request_price: Optional[float] = Field(
        None, description="Cost per request in USD (if applicable)"
    )


class UniversalModel(BaseModel):
    """Universal model representation with standardized fields."""
    id: str = Field(description="Unique model identifier")
    name: str = Field(description="Human-readable model name")
    provider: str = Field(
        description="Model provider (openrouter, etc.)"
    )
    description: Optional[str] = Field(None, description="Model description")
    context_length: Optional[int] = Field(
        None, description="Maximum context length"
    )
    max_output_tokens: Optional[int] = Field(
        None, description="Maximum output tokens"
    )
    pricing: Optional[UniversalModelPricing] = Field(
        None, description="Pricing information"
    )
    supports_vision: Optional[bool] = Field(
        None, description="Whether model supports vision"
    )
    supports_function_calling: Optional[bool] = Field(
        None,
        description="Whether model supports function calling"
    )
    raw_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Original raw data from provider"
    )


class ModelProvider(BaseModel):
    """Container for models from a specific provider."""
    provider: str = Field(description="Provider name")
    models: List[UniversalModel] = Field(
        description="List of models from this provider"
    )
    updated_at: datetime = Field(description="When the models were last updated")


class UniversalModelResponse(BaseModel):
    """Response containing models from all providers."""
    providers: List[ModelProvider] = Field(
        description="List of providers with their models"
    )
    all_models: List[UniversalModel] = Field(
        description="Combined list of all models"
    )


class UniversalModelGetter:
    """
    A class for getting models from OpenRouter in a standardized format.
    """

    def __init__(self):
        """Initialize the model getter with OpenRouter updater."""
        self.openrouter_updater = OpenRouterModelUpdater()
        self.current_dir = os.path.dirname(os.path.abspath(__file__))

    def _convert_openrouter_model(self, model: OpenRouterModel) -> UniversalModel:
        """Convert an OpenRouter model to the universal format."""
        pricing = None
        if model.pricing:
            try:
                # Convert string prices to float
                prompt_price = float(model.pricing.prompt.strip('$'))
                completion_price = float(model.pricing.completion.strip('$'))
                image_price = None
                request_price = None

                if model.pricing.image:
                    image_price = float(model.pricing.image.strip('$'))
                if model.pricing.request:
                    request_price = float(model.pricing.request.strip('$'))

                pricing = UniversalModelPricing(
                    input_price=prompt_price,
                    output_price=completion_price,
                    image_price=image_price,
                    request_price=request_price
                )
            except (ValueError, AttributeError):
                # If price conversion fails, leave pricing as None
                pass

        # Check for vision support based on architecture
        supports_vision = False
        if model.architecture and model.architecture.modality:
            supports_vision = "image" in model.architecture.modality

        # Get context length from model or top provider
        context_length = model.context_length
        if not context_length and model.top_provider:
            context_length = model.top_provider.context_length

        # Get max output tokens from top provider
        max_output_tokens = None
        if model.top_provider:
            max_output_tokens = model.top_provider.max_completion_tokens

        return UniversalModel(
            id=model.id,
            name=model.name,
            provider="openrouter",
            description=model.description,
            context_length=context_length,
            max_output_tokens=max_output_tokens,
            pricing=pricing,
            supports_vision=supports_vision,
            supports_function_calling=None,  # OpenRouter doesn't specify this
            raw_data=model.model_dump()
        )

    def get_models(self, force_update: bool = False) -> UniversalModelResponse:
        """
        Get models from OpenRouter in a standardized format.

        Args:
            force_update: Whether to force an update of the model data.

        Returns:
            A UniversalModelResponse containing models from OpenRouter.
        """
        # Get OpenRouter models
        openrouter_path, openrouter_updated = self.openrouter_updater.update_models(
            force=force_update
        )
        openrouter_models = self.openrouter_updater.get_models()

        # Convert to universal format
        universal_models = [
            self._convert_openrouter_model(model) for model in openrouter_models
        ]

        # Create provider container
        openrouter_provider = ModelProvider(
            provider="openrouter",
            models=universal_models,
            updated_at=datetime.now()
        )

        return UniversalModelResponse(
            providers=[openrouter_provider],
            all_models=universal_models
        )

    def get_model_by_id(self, model_id: str) -> Optional[UniversalModel]:
        """
        Get a specific model by its ID.

        Args:
            model_id: The ID of the model to retrieve.

        Returns:
            The model if found, None otherwise.
        """
        models = self.get_models()

        # Try to find the model with the exact ID first
        for model in models.all_models:
            if model.id == model_id:
                return model

        # If not found, try to match with provider prefix
        if "/" in model_id:
            provider, base_id = model_id.split("/", 1)

            # If it's an OpenRouter model with nested provider (e.g., openrouter/openai/gpt-4)
            if provider == "openrouter" and "/" in base_id:
                _, model_name = base_id.split("/", 1)

                # Try to find the model by its name in OpenRouter models
                for model in models.providers[0].models:
                    if model.name == model_name or model.id == model_name:
                        return model

        # If still not found, try to find by the last part of the ID
        base_name = model_id.split("/")[-1]
        for model in models.all_models:
            if model.id == base_name or model.name == base_name:
                return model

        return None

    def get_models_by_provider(self, provider: str) -> List[UniversalModel]:
        """
        Get all models from a specific provider.

        Args:
            provider: The provider name to filter by.

        Returns:
            List of models from the specified provider.
        """
        models = self.get_models()
        return [model for model in models.all_models if model.provider == provider]

    def get_models_with_capability(self, capability: str) -> List[UniversalModel]:
        """
        Get all models with a specific capability.

        Args:
            capability: The capability to filter by (vision, function_calling).

        Returns:
            List of models with the specified capability.
        """
        models = self.get_models()

        if capability == "vision":
            return [
                model for model in models.all_models
                if model.supports_vision
            ]
        elif capability == "function_calling":
            return [
                model for model in models.all_models
                if model.supports_function_calling
            ]

        return []


if __name__ == "__main__":
    # Example usage
    getter = UniversalModelGetter()

    # Get all models
    all_models = getter.get_models()

    # Print a few example models
    for model in all_models.all_models[:5]:
        print(f"\nModel: {model.id}")
        print(f"Provider: {model.provider}")
        print(f"Context Length: {model.context_length}")
        if model.pricing:
            print(f"Input Price: ${model.pricing.input_price}")
            print(f"Output Price: ${model.pricing.output_price}")
