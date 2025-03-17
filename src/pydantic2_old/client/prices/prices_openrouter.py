import json
import os
import requests
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
from pydantic import BaseModel, Field


class ModelArchitecture(BaseModel):
    """Model architecture information."""
    modality: str = Field(description="The modality of the model (e.g., 'text->text', 'text+image->text')")
    tokenizer: str = Field(description="The tokenizer used by the model")
    instruct_type: Optional[str] = Field(None, description="The instruction type of the model")


class ModelPricing(BaseModel):
    """Model pricing information."""
    prompt: str = Field(description="Cost per prompt token")
    completion: str = Field(description="Cost per completion token")
    image: str = Field(description="Cost per image")
    request: str = Field(description="Cost per request")
    input_cache_read: str = Field(description="Cost for input cache read")
    input_cache_write: str = Field(description="Cost for input cache write")
    web_search: str = Field(description="Cost for web search")
    internal_reasoning: str = Field(description="Cost for internal reasoning")


class TopProvider(BaseModel):
    """Information about the top provider for a model."""
    context_length: Optional[int] = Field(None, description="Maximum context length")
    max_completion_tokens: Optional[int] = Field(None, description="Maximum completion tokens")
    is_moderated: Optional[bool] = Field(None, description="Whether the model is moderated")


class OpenRouterModel(BaseModel):
    """Representation of a model from the OpenRouter API."""
    id: str = Field(description="The model ID")
    name: str = Field(description="The model name")
    created: int = Field(description="Creation timestamp")
    description: str = Field(description="Model description")
    context_length: Optional[int] = Field(None, description="Maximum context length")
    architecture: Optional[ModelArchitecture] = Field(None, description="Model architecture information")
    pricing: Optional[ModelPricing] = Field(None, description="Model pricing information")
    top_provider: Optional[TopProvider] = Field(None, description="Information about the top provider")
    per_request_limits: Optional[Any] = Field(None, description="Per-request limits")


class OpenRouterResponse(BaseModel):
    """Response from the OpenRouter API."""
    data: List[OpenRouterModel] = Field(description="List of available models")


class OpenRouterModelUpdater:
    """
    A class for fetching and saving OpenRouter model data to a JSON file.
    """

    def __init__(self, api_url: str = "https://openrouter.ai/api/v1/models"):
        """
        Initialize the OpenRouterModelUpdater.

        Args:
            api_url: The URL of the OpenRouter API endpoint.
        """
        self.api_url = api_url
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.default_filename = "openrouter_models.json"

    def fetch_models(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Fetch model data from the OpenRouter API.

        Args:
            headers: Optional headers to include in the request.

        Returns:
            The JSON response from the API.

        Raises:
            requests.RequestException: If the request fails.
        """
        default_headers = {
            "Content-Type": "application/json",
        }

        if headers:
            default_headers.update(headers)

        response = requests.get(self.api_url, headers=default_headers)
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
        Check if models data should be updated (if 24 hours have passed since last update).

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

    def update_models(
        self,
        force: bool = False,
        headers: Optional[Dict[str, str]] = None
    ) -> Tuple[str, bool]:
        """
        Fetch model data from the OpenRouter API and save it to a JSON file if needed.

        Args:
            force: Force update even if 24 hours haven't passed.
            headers: Optional headers to include in the request.

        Returns:
            Tuple of (file_path, was_updated)
        """
        file_path = os.path.join(self.current_dir, self.default_filename)

        should_update, reason = self.should_update()

        if not (should_update or force):
            return file_path, False

        try:
            data = self.fetch_models(headers)
            file_path = self.save_to_json(data)
            return file_path, True
        except Exception as e:
            raise Exception(f"Failed to update models: {str(e)}")

    def get_models(self) -> List[OpenRouterModel]:
        """
        Get a list of OpenRouter models.

        This method will load models from the cached JSON file if it exists and
        is less than 24 hours old. Otherwise, it will fetch fresh data from the API.

        Returns:
            List of OpenRouterModel objects
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
                    raise Exception(f"Failed to get models: {str(e)}")
        else:
            # Use existing data
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data = data.get("response", {})

        # Parse the response using Pydantic
        response = OpenRouterResponse(data=data.get("data", []))
        return response.data


if __name__ == "__main__":
    # Example usage
    updater = OpenRouterModelUpdater()

    updater.update_models()
    models = updater.get_models()
    for model in models:
        print(model.model_dump_json(indent=2))
