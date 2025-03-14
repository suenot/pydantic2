
from pydantic2.client.prices import UniversalModelGetter


if __name__ == "__main__":
    # Example usage
    getter = UniversalModelGetter()

    # Get all models
    model = getter.get_model_by_id("openrouter/openai/gpt-4o-mini-2024-07-18")
    print(model)
