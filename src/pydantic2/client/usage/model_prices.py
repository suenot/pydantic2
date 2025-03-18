from datetime import datetime, timedelta
from pathlib import Path
import json
import requests
from typing import Optional
from peewee import (
    Model, SqliteDatabase, CharField, IntegerField,
    FloatField, DateTimeField, TextField, AutoField, BooleanField, DoesNotExist
)
from ...utils.logger import logger
import sqlite3

# Database configuration
THIS_DIR = Path(__file__).parent.parent.parent
DB_DIR = THIS_DIR / 'db'
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "models.db"

# Singleton database instance
_db = None


def get_db():
    """Get or create database connection singleton"""
    global _db
    if _db is None:
        _db = SqliteDatabase(DB_PATH)
    return _db


OPENROUTER_API_URL = "https://openrouter.ai/api/v1/models"


class BaseModel(Model):
    class Meta:
        database = get_db()


class PriceUpdate(BaseModel):
    """Track when prices were last updated."""
    id = AutoField()
    update_time = DateTimeField(default=datetime.now)
    source = CharField()  # e.g., 'openrouter'
    status = CharField()  # 'success' or 'failed'
    error_message = TextField(null=True)


class LLMModel(BaseModel):
    """Model information and pricing."""
    class Meta:
        table_name = 'models'

    id = AutoField()
    model_id = CharField(unique=True)  # Original ID from provider
    name = CharField()
    provider = CharField()
    description = TextField(null=True)
    created = IntegerField(null=True)  # Unix timestamp of model creation
    context_length = IntegerField(null=True)
    max_output_tokens = IntegerField(null=True)
    input_cost_per_token = FloatField(default=0)
    output_cost_per_token = FloatField(default=0)
    image_cost = FloatField(null=True)
    request_cost = FloatField(null=True)
    supports_vision = BooleanField(default=False)
    supports_function_calling = BooleanField(default=False)
    modality = CharField(null=True)
    tokenizer = CharField(null=True)
    instruct_type = CharField(null=True)
    raw_data = TextField(null=True)  # JSON string of raw provider data
    last_updated = DateTimeField(default=datetime.now)

    def get_input_cost(self) -> float:
        """Get input cost per token as float."""
        return float(getattr(self, 'input_cost_per_token', 0) or 0)

    def get_output_cost(self) -> float:
        """Get output cost per token as float."""
        return float(getattr(self, 'output_cost_per_token', 0) or 0)

    def get_max_tokens(self) -> Optional[int]:
        """Get maximum output tokens."""
        value = getattr(self, 'max_output_tokens', None)
        return int(value) if value is not None else None


class ModelPriceManager:
    def __init__(self, force_update: bool = False):
        """Initialize the model price manager.

        Args:
            force_update: Force update of model prices even if they were recently updated
        """
        self.db = get_db()
        if self.db.is_closed():
            self.db.connect()
        self.db.create_tables([LLMModel, PriceUpdate], safe=True)

        # Update prices during initialization if needed
        try:
            if force_update or self.should_update_models():
                self.update_from_openrouter()
        except Exception as e:
            logger.error(f"Failed to update model prices during initialization: {e}")

        logger.info("Model price manager initialized")

    def should_update_models(self) -> bool:
        """Check if models should be updated based on last update time."""
        try:
            latest_update = PriceUpdate.select().where(
                PriceUpdate.status == 'success'
            ).order_by(PriceUpdate.update_time.desc()).first()

            if not latest_update:
                return True

            one_day_ago = datetime.now() - timedelta(days=1)
            return latest_update.update_time < one_day_ago
        except DoesNotExist:
            return True

    def update_from_openrouter(self, force: bool = False):
        """Update model prices from OpenRouter."""
        if not force and not self.should_update_models():
            logger.info("Models are up to date (last update less than 24 hours ago)")
            return

        logger.info("Updating models from OpenRouter...")
        update_record = None

        try:
            # Create update record
            update_record = PriceUpdate.create(
                source='openrouter',
                status='in_progress'
            )

            # Fetch models from OpenRouter API
            headers = {}

            response = requests.get(OPENROUTER_API_URL, headers=headers)
            response.raise_for_status()
            data = response.json()

            for model_data in data.get("data", []):
                # Extract architecture info
                architecture = model_data.get('architecture', {})
                modality = architecture.get('modality')
                tokenizer = architecture.get('tokenizer')
                instruct_type = architecture.get('instruct_type')

                # Extract pricing info
                pricing = model_data.get('pricing', {})
                input_cost = float(pricing.get('prompt', 0))
                output_cost = float(pricing.get('completion', 0))
                image_cost = float(pricing.get('image', 0))
                request_cost = float(pricing.get('request', 0))

                # Get max tokens from top provider
                top_provider = model_data.get('top_provider', {})
                max_output_tokens = top_provider.get('max_completion_tokens')

                # Get or create model
                model, created = LLMModel.get_or_create(
                    model_id=model_data['id'],
                    defaults={
                        'name': model_data['name'],
                        'provider': model_data['id'].split('/')[0],
                        'description': model_data.get('description'),
                        'created': model_data.get('created'),
                        'context_length': model_data.get('context_length'),
                        'max_output_tokens': max_output_tokens,
                        'input_cost_per_token': input_cost,
                        'output_cost_per_token': output_cost,
                        'image_cost': image_cost if image_cost else None,
                        'request_cost': request_cost if request_cost else None,
                        'supports_vision': 'image' in (modality or ''),
                        'supports_function_calling': False,  # Need to determine this from capabilities
                        'modality': modality,
                        'tokenizer': tokenizer,
                        'instruct_type': instruct_type,
                        'raw_data': json.dumps(model_data),
                        'last_updated': datetime.now()
                    }
                )
                model: LLMModel = model

                # If model exists, update its fields
                if not created:
                    updates = {
                        LLMModel.name: model_data['name'],
                        LLMModel.description: model_data.get('description'),
                        LLMModel.created: model_data.get('created'),
                        LLMModel.context_length: model_data.get('context_length'),
                        LLMModel.max_output_tokens: max_output_tokens,
                        LLMModel.input_cost_per_token: input_cost,
                        LLMModel.output_cost_per_token: output_cost,
                        LLMModel.image_cost: image_cost if image_cost else None,
                        LLMModel.request_cost: request_cost if request_cost else None,
                        LLMModel.supports_vision: 'image' in (modality or ''),
                        LLMModel.modality: modality,
                        LLMModel.tokenizer: tokenizer,
                        LLMModel.instruct_type: instruct_type,
                        LLMModel.raw_data: json.dumps(model_data),
                        LLMModel.last_updated: datetime.now()
                    }
                    query = LLMModel.update(updates).where(LLMModel.id == model.id)
                    query.execute()

            # Update success status
            update_record.status = 'success'
            update_record.save()
            logger.info("Models updated successfully")

        except Exception as e:
            if update_record:
                update_record.status = 'failed'
                update_record.error_message = str(e)
                update_record.save()
            logger.error(f"Error updating models: {e}")
            raise

    def get_model_price(self, model_id: str) -> Optional[LLMModel]:
        """Get pricing information for a specific model."""
        try:
            model: LLMModel = LLMModel.get(LLMModel.model_id == model_id)
            return model
        except Exception:
            return None

    def list_models(self):
        """List all available models with their prices."""
        return list(LLMModel.select().dicts())

    def get_models_by_provider(self, provider: str):
        """Get all models from a specific provider."""
        return list(LLMModel.select().where(LLMModel.provider == provider).dicts())

    def get_last_update_status(self):
        """Get information about the last price update."""
        try:
            last_update: PriceUpdate = PriceUpdate.select().order_by(PriceUpdate.update_time.desc()).first()
            if last_update:
                return {
                    'update_time': last_update.update_time,
                    'source': last_update.source,
                    'status': last_update.status,
                    'error_message': last_update.error_message
                }
        except DoesNotExist:
            pass
        return None

    def close(self):
        """Close the database connection."""
        if self.db and not self.db.is_closed():
            try:
                self.db.close()
            except sqlite3.Error:
                pass


if __name__ == "__main__":
    # Example usage
    manager = ModelPriceManager()

    # Update models from OpenRouter
    manager.update_from_openrouter(force=True)

    # Print all models
    print("\nAvailable models:")
    for model in manager.list_models():
        print(f"\nModel: {model['name']}")
        print(f"Provider: {model['provider']}")
        print(f"Input cost: ${model['input_cost_per_token']}")
        print(f"Output cost: ${model['output_cost_per_token']}")

    manager.close()
