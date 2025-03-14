import json
import os
import requests
from typing import Dict, Any, Optional, Tuple, Literal
from datetime import datetime, timedelta
from pydantic import BaseModel, Field


class LiteLLMModelSpec(BaseModel):
    """Model specification information from LiteLLM."""
    max_tokens: Optional[int] = Field(
        None,
        description="Legacy parameter for maximum tokens"
    )
    max_input_tokens: Optional[int] = Field(
        None,
        description="Maximum input tokens, if specified by provider"
    )
    max_output_tokens: Optional[int] = Field(
        None,
        description="Maximum output tokens, if specified by provider"
    )
    input_cost_per_token: Optional[float] = Field(
        None,
        description="Cost per input token"
    )
    output_cost_per_token: Optional[float] = Field(
        None,
        description="Cost per output token"
    )
    input_cost_per_token_batches: Optional[float] = Field(
        None,
        description="Cost per input token for batch processing"
    )
    output_cost_per_token_batches: Optional[float] = Field(
        None,
        description="Cost per output token for batch processing"
    )
    cache_read_input_token_cost: Optional[float] = Field(
        None,
        description="Cost for reading input tokens from cache"
    )
    litellm_provider: Optional[str] = Field(
        None,
        description="The provider name in LiteLLM"
    )
    mode: Optional[str] = Field(
        None,
        description="Model operation mode (chat, embedding, completion, etc.)"
    )
    supports_function_calling: Optional[bool] = Field(
        None,
        description="Whether the model supports function calling"
    )
    supports_parallel_function_calling: Optional[bool] = Field(
        None,
        description="Whether the model supports parallel function calling"
    )
    supports_vision: Optional[bool] = Field(
        None,
        description="Whether the model supports vision capabilities"
    )
    supports_audio_input: Optional[bool] = Field(
        None,
        description="Whether the model supports audio input"
    )
    supports_audio_output: Optional[bool] = Field(
        None,
        description="Whether the model supports audio output"
    )
    supports_prompt_caching: Optional[bool] = Field(
        None,
        description="Whether the model supports prompt caching"
    )
    supports_response_schema: Optional[bool] = Field(
        None,
        description="Whether the model supports response schema"
    )
    supports_system_messages: Optional[bool] = Field(
        None,
        description="Whether the model supports system messages"
    )
    supports_tool_choice: Optional[bool] = Field(
        None,
        description="Whether the model supports tool choice"
    )
    deprecation_date: Optional[str] = Field(
        None,
        description="Date when the model becomes deprecated (YYYY-MM-DD)"
    )


class LiteLLMModelUpdater:
    """
    A class for fetching and saving LiteLLM model pricing data to a JSON file.
    """

    def __init__(
        self,
        api_url: str = (
            "https://raw.githubusercontent.com/BerriAI/litellm/main/"
            "model_prices_and_context_window.json"
        )
    ):
        """
        Initialize the LiteLLMModelUpdater.

        Args:
            api_url: The URL of the LiteLLM model pricing JSON.
        """
        self.api_url = api_url
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.default_filename = "litellm_models.json"

    def fetch_models(self) -> Dict[str, Any]:
        """
        Fetch model data from the LiteLLM GitHub repository.

        Returns:
            The JSON response containing model pricing data.

        Raises:
            requests.RequestException: If the request fails.
        """
        response = requests.get(self.api_url)
        response.raise_for_status()

        return response.json()

    def save_to_json(self, data: Dict[str, Any]) -> str:
        """
        Save the model data to a JSON file in the current directory with a
        consistent format including update timestamp.

        Args:
            data: The API response data to save.

        Returns:
            The path to the saved file.
        """
        # Create structured response with update timestamp
        structured_data = {
            "updated_at": datetime.now().isoformat(),
            "response": data
        }

        file_path = os.path.join(
            self.current_dir,
            'data',
            self.default_filename
        )

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(structured_data, f, indent=2, ensure_ascii=False)

        return file_path

    def should_update(self) -> Tuple[bool, Optional[str]]:
        """
        Check if models data should be updated (if 24 hours have passed).

        Returns:
            Tuple of (should_update, reason)
        """
        file_path = os.path.join(self.current_dir, self.default_filename)

        if not os.path.exists(file_path):
            return True, "No existing data file found"

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if "updated_at" not in data:
                return True, "No update timestamp in existing file"

            last_update = datetime.fromisoformat(data["updated_at"])
            now = datetime.now()
            hours_since_update = (now - last_update).total_seconds() / 3600

            if now - last_update >= timedelta(hours=24):
                return True, f"Last update was {hours_since_update:.1f} hours ago"
            else:
                return False, f"Last update was {hours_since_update:.1f} hours ago"

        except Exception as e:
            return True, f"Error reading existing file: {str(e)}"

    def update_models(self, force: bool = False) -> Tuple[str, bool]:
        """
        Fetch model data from the LiteLLM repository and save it to a JSON file if needed.

        Args:
            force: Force update even if 24 hours haven't passed.

        Returns:
            Tuple of (file_path, was_updated)
        """
        file_path = os.path.join(self.current_dir, self.default_filename)

        should_update, reason = self.should_update()

        if not (should_update or force):
            return file_path, False

        try:
            data = self.fetch_models()
            file_path = self.save_to_json(data)
            return file_path, True
        except Exception as e:
            raise Exception(f"Failed to update models: {str(e)}")

    def get_models(self) -> Dict[str, LiteLLMModelSpec]:
        """
        Get a dictionary of LiteLLM models with their specifications.

        This method will load models from the cached JSON file if it exists and
        is less than 24 hours old. Otherwise, it will fetch fresh data from the API.

        Returns:
            Dictionary mapping model names to LiteLLMModelSpec objects
        """
        file_path = os.path.join(self.current_dir, self.default_filename)

        # Check if we need to update
        should_update, reason = self.should_update()

        if should_update:
            try:
                data = self.fetch_models()
                self.save_to_json(data)
            except Exception as e:
                # If update fails but we have existing data, use that
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        data = data.get("response", {})
                else:
                    raise Exception(
                        f"Failed to get models: {str(e)}"
                    )
        else:
            # Use existing data
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data = data.get("response", {})

        # Convert the raw data to Pydantic models
        models = {}
        for model_id, model_data in data.items():
            if model_id == "sample_spec":
                continue  # Skip the sample specification
            try:
                models[model_id] = LiteLLMModelSpec(**model_data)
            except Exception as e:
                # Skip models with invalid data
                print(f"Error parsing model {model_id}: {str(e)}")
                continue

        return models

    def get_model_by_id(self, model_id: str) -> Optional[LiteLLMModelSpec]:
        """
        Get a specific model by its ID.

        Args:
            model_id: The ID of the model to retrieve.

        Returns:
            The model specification if found, None otherwise.
        """
        models = self.get_models()
        return models.get(model_id)

    def get_models_by_provider(self, provider: str) -> Dict[str, LiteLLMModelSpec]:
        """
        Get all models from a specific provider.

        Args:
            provider: The provider name to filter by.

        Returns:
            Dictionary of models from the specified provider.
        """
        models = self.get_models()
        return {
            model_id: model_spec
            for model_id, model_spec in models.items()
            if model_spec.litellm_provider == provider
        }

    def get_models_by_mode(self, mode: str) -> Dict[str, LiteLLMModelSpec]:
        """
        Get all models with a specific mode.

        Args:
            mode: The mode to filter by (chat, embedding, completion, etc.).

        Returns:
            Dictionary of models with the specified mode.
        """
        models = self.get_models()
        return {
            model_id: model_spec
            for model_id, model_spec in models.items()
            if model_spec.mode == mode
        }

    def get_models_with_capability(
        self,
        capability: Literal[
            "function_calling",
            "parallel_function_calling",
            "vision",
            "audio_input",
            "audio_output",
            "prompt_caching",
            "response_schema",
            "system_messages",
            "tool_choice"
        ]
    ) -> Dict[str, LiteLLMModelSpec]:
        """
        Get all models with a specific capability.

        Args:
            capability: The capability to filter by.

        Returns:
            Dictionary of models with the specified capability.
        """
        models = self.get_models()
        capability_attr = f"supports_{capability}"

        return {
            model_id: model_spec
            for model_id, model_spec in models.items()
            if getattr(model_spec, capability_attr, False)
        }


if __name__ == "__main__":
    # Example usage
    updater = LiteLLMModelUpdater()

    updater.update_models()
    models = updater.get_models()

    # Print a few example models
    for model_id, model_spec in list(models.items())[:5]:
        print(f"\nModel: {model_id}")
        print(model_spec.model_dump_json(indent=2))
