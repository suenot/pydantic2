import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
from pydantic import BaseModel as PydanticBaseModel, Field
from peewee import (
    Model, SqliteDatabase, CharField, IntegerField,
    FloatField, DateTimeField, TextField,
    ForeignKeyField, AutoField
)

from ...client.models.base_models import Request
from ...utils.logger import logger


# Database configuration
THIS_DIR = Path(__file__).parent
DB_PATH = THIS_DIR / "litellm_usage.db"
db = SqliteDatabase(DB_PATH)


class BaseModel(Model):
    class Meta:
        database = db


class LLMModel(BaseModel):
    """Model information and pricing."""
    class Meta:
        table_name = 'models'

    name = CharField(unique=True)
    provider = CharField(null=True)
    max_tokens = IntegerField(null=True)
    input_cost_per_token = FloatField(default=0)
    output_cost_per_token = FloatField(default=0)
    total_input_tokens = IntegerField(default=0)
    total_output_tokens = IntegerField(default=0)
    last_updated = DateTimeField(default=datetime.now)


class ModelHistory(BaseModel):
    """Log of model usage."""
    class Meta:
        table_name = 'history'

    id = AutoField()
    request_id = CharField(unique=True)
    timestamp = DateTimeField(default=datetime.now)

    # Model and client information
    model = ForeignKeyField(LLMModel, backref='usage')
    client_id = CharField()
    user_id = CharField(null=True)

    # Request and response data
    config_json = TextField(null=True)
    request_raw = TextField(null=True)
    request_json = TextField(null=True)
    response_json = TextField(null=True)
    response_raw = TextField(null=True)

    # Token usage and costs
    input_tokens = IntegerField(default=0)
    output_tokens = IntegerField(default=0)
    input_cost = FloatField(default=0)
    output_cost = FloatField(default=0)
    total_cost = FloatField(default=0)

    # Status information
    status = CharField(default="progress")  # progress, success, error
    error_message = TextField(null=True)


# Pydantic models for usage data
class ModelUsageStats(PydanticBaseModel):
    """Model usage statistics in Pydantic format."""
    model_name: str = Field(..., description="Name of the model")
    provider: Optional[str] = Field(None, description="Provider of the model")
    total_input_tokens: int = Field(0, description="Total input tokens processed")
    total_output_tokens: int = Field(0, description="Total output tokens generated")
    total_cost: float = Field(0.0, description="Total cost in USD")
    last_used: datetime = Field(..., description="Last time the model was used")


class RequestRecord(PydanticBaseModel):
    """Individual request record in Pydantic format."""
    request_id: str = Field(..., description="Unique request ID")
    timestamp: datetime = Field(..., description="Time of the request")
    model_name: str = Field(..., description="Model used for the request")
    status: str = Field(..., description="Status of the request (success, error, progress)")
    input_tokens: int = Field(0, description="Number of input tokens")
    output_tokens: int = Field(0, description="Number of output tokens")
    total_cost: float = Field(0.0, description="Total cost in USD")
    error_message: Optional[str] = Field(None, description="Error message if status is error")


class RequestDetails(PydanticBaseModel):
    """Detailed information about a specific request."""
    request_id: str = Field(..., description="Unique request ID")
    timestamp: datetime = Field(..., description="Time of the request")

    # Model information
    model_name: str = Field(..., description="Name of the model used")
    model_provider: Optional[str] = Field(None, description="Provider of the model")

    # Client information
    client_id: str = Field(..., description="Client identifier")
    user_id: Optional[str] = Field(None, description="User identifier")

    # Request data
    config_json: Optional[str] = Field(None, description="Request configuration")
    request_raw: Optional[str] = Field(None, description="Raw request data")
    request_json: Optional[str] = Field(None, description="JSON request data")

    # Response data
    response_json: Optional[str] = Field(None, description="JSON response data")
    response_raw: Optional[str] = Field(None, description="Raw response data")

    # Usage statistics
    input_tokens: int = Field(0, description="Number of input tokens")
    output_tokens: int = Field(0, description="Number of output tokens")
    input_cost: float = Field(0.0, description="Cost of input tokens")
    output_cost: float = Field(0.0, description="Cost of output tokens")
    total_cost: float = Field(0.0, description="Total cost in USD")

    # Status information
    status: str = Field(..., description="Status of the request")
    error_message: Optional[str] = Field(None, description="Error message if status is error")


class ClientUsageData(PydanticBaseModel):
    """Complete client usage data in Pydantic format."""
    client_id: str = Field(..., description="Client identifier")
    total_requests: int = Field(0, description="Total number of requests")
    successful_requests: int = Field(0, description="Number of successful requests")
    failed_requests: int = Field(0, description="Number of failed requests")
    total_input_tokens: int = Field(0, description="Total input tokens")
    total_output_tokens: int = Field(0, description="Total output tokens")
    total_cost: float = Field(0.0, description="Total cost in USD")
    models_used: List[ModelUsageStats] = Field(
        default_factory=list,
        description="Statistics per model"
    )
    recent_requests: List[RequestRecord] = Field(
        default_factory=list,
        description="Recent request records"
    )


def initialize_db():
    """Initialize the database and create tables if they don't exist."""
    logger.debug(f"Initializing database at {DB_PATH}")
    db.connect(reuse_if_open=True)

    # Create tables with all fields
    db.create_tables([LLMModel, ModelHistory])

    return db


class UsageClass:
    """
    Simplified usage class for tracking LLM model usage.
    This class writes usage data to a SQLite database.
    """

    def __init__(self, config: Request):
        """Initialize the usage class."""
        self.config = config
        self.db = initialize_db()
        self._current_request_id = None

        # Get client_id from config or generate a new one
        self.client_id = getattr(config, 'client_id', None) or str(uuid.uuid4())
        self.user_id = getattr(config, 'user_id', None)

        logger.info(f"UsageClass initialized for client: {self.client_id}")

    def start_request(self) -> Optional[str]:
        """
        Start tracking a request.

        Returns:
            request_id: The ID of the created request
        """
        # Skip if no client_id
        if not self.client_id:
            logger.warning("No client_id provided, skipping database logging")
            return None

        try:
            # Generate a unique request ID
            request_id = str(uuid.uuid4())
            self._current_request_id = request_id

            # Get or create model record
            model_name = self.config.model
            model = self._get_or_create_model(model_name)

            # Prepare request data
            config_json = None
            request_raw = None
            request_json = None

            # Save request configuration
            if hasattr(self.config, 'model_dump_json'):
                try:
                    config_json = self.config.model_dump_json()
                except Exception:
                    config_json = str(self.config)

            # Save request data
            if hasattr(self.config, 'messages'):
                request_raw = str(self.config.messages)
                try:
                    import json
                    request_json = json.dumps(self.config.messages)
                except Exception:
                    pass

            # Create a new usage record
            ModelHistory.create(
                request_id=request_id,
                model=model,
                client_id=self.client_id,
                user_id=self.user_id,
                config_json=config_json,
                request_raw=request_raw,
                request_json=request_json,
                status="progress"
            )

            logger.info(f"Started request tracking with ID: {request_id}")
            return request_id
        except Exception as e:
            logger.error(f"Failed to start request tracking: {e}")
            return None

    def log_error(self, error_msg: str) -> bool:
        """
        Log an error for the current request.

        Args:
            error_msg: Error message

        Returns:
            bool: True if successful, False otherwise
        """
        # Skip if no client_id or request_id
        if not self.client_id or not self._current_request_id:
            return False

        try:
            # Update the history record with error status
            query = ModelHistory.update(
                error_message=error_msg,
                status="error",
                timestamp=datetime.now()
            ).where(ModelHistory.request_id == self._current_request_id)

            rows_updated = query.execute()

            if rows_updated:
                req_id = self._current_request_id
                logger.info(f"Updated request {req_id} with error status")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to log error: {e}")
            return False
        finally:
            # Reset the current request ID
            self._current_request_id = None

    def log_success(
        self,
        response_json: Dict[str, Any],
        usage_info: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Log a successful request with token and cost information.

        Args:
            response_data: The response data
            meta: Metadata from the client
            usage_info: Optional usage information from get_usage_info()
            raw_llm_response: Optional raw LLM response

        Returns:
            bool: True if successful, False otherwise
        """
        # Skip if no client_id or request_id
        if not self.client_id or not self._current_request_id:
            return False

        try:
            # Initialize values
            input_tokens = 0
            output_tokens = 0
            input_cost = 0.0
            output_cost = 0.0
            total_cost = 0.0

            # Use usage_info if provided
            if usage_info:
                # Get token counts
                input_tokens = usage_info.get('prompt_tokens', 0)
                output_tokens = usage_info.get('completion_tokens', 0)

                # Get costs
                input_cost = usage_info.get('prompt_cost_usd', 0.0)
                output_cost = usage_info.get('completion_cost_usd', 0.0)
                total_cost = usage_info.get('cost_usd', 0.0)

                logger.info(f"Usage: tokens={input_tokens}/{output_tokens}")

            # Update the history record
            query = ModelHistory.update(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                input_cost=input_cost,
                output_cost=output_cost,
                total_cost=total_cost,
                status="success",
                response_json=response_json,
                timestamp=datetime.now()
            ).where(ModelHistory.request_id == self._current_request_id)

            rows_updated = query.execute()

            if not rows_updated:
                req_id = self._current_request_id
                logger.warning(f"No record found for request {req_id}")
                return False

            # Update the model token counts
            try:
                req_id = self._current_request_id
                history = ModelHistory.get(ModelHistory.request_id == req_id)
                model = history.model
                self._update_model_token_counts(model, input_tokens, output_tokens)
            except Exception as e:
                logger.warning(f"Failed to update model token counts: {e}")

            logger.info(f"Request success: ${total_cost:.6f}")
            return True
        except Exception as e:
            logger.error(f"Failed to log success: {e}")
            return False
        finally:
            # Reset the current request ID
            self._current_request_id = None

    def get_usage_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get usage statistics for a user or client.

        Args:
            user_id: User ID to filter by (optional)

        Returns:
            Dict with usage statistics
        """
        # Skip if no client_id
        if not self.client_id:
            return {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "error": "No client_id provided"
            }

        try:
            query = ModelHistory.select()

            # Apply filters
            if user_id:
                query = query.where(ModelHistory.user_id == user_id)
            else:
                query = query.where(ModelHistory.client_id == self.client_id)

            # Calculate statistics
            total_requests = query.count()
            successful_requests = query.where(ModelHistory.status == "success").count()
            failed_requests = query.where(ModelHistory.status == "error").count()

            # Sum costs and tokens
            total_cost = 0.0
            total_input_tokens = 0
            total_output_tokens = 0

            for record in query.where(ModelHistory.status == "success"):
                total_cost += record.total_cost
                total_input_tokens += record.input_tokens
                total_output_tokens += record.output_tokens

            # Return statistics
            return {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "total_tokens": total_input_tokens + total_output_tokens,
                "total_cost": total_cost
            }
        except Exception as e:
            logger.error(f"Failed to get usage statistics: {e}")
            return {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "error": str(e)
            }

    def get_client_usage_data(
        self,
        client_id: Optional[str] = None,
        limit_recent: int = 10
    ) -> ClientUsageData:
        """
        Get detailed usage data for a client in Pydantic format.

        Args:
            client_id: Client ID to get data for (defaults to current client_id)
            limit_recent: Maximum number of recent requests to include

        Returns:
            ClientUsageData: Pydantic model with detailed usage information
        """
        # Use current client_id if none provided
        client_id = client_id or self.client_id

        if not client_id:
            # Return empty data if no client_id
            return ClientUsageData(
                client_id="unknown",
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                total_input_tokens=0,
                total_output_tokens=0,
                total_cost=0.0,
                models_used=[],
                recent_requests=[]
            )

        try:
            # Get all requests with model information in a single query
            base_query = (
                ModelHistory
                .select(ModelHistory, LLMModel)
                .join(LLMModel)
                .where(ModelHistory.client_id == client_id)
            )

            # Calculate basic statistics
            total_requests = base_query.count()
            successful_requests = (
                base_query.where(ModelHistory.status == "success").count()
            )
            failed_requests = (
                base_query.where(ModelHistory.status == "error").count()
            )

            # Get model usage statistics in a single query
            model_stats = {}
            for record in base_query.where(ModelHistory.status == "success"):
                model_name = record.model.name
                if model_name not in model_stats:
                    model_stats[model_name] = {
                        "model_name": model_name,
                        "provider": record.model.provider,
                        "total_input_tokens": 0,
                        "total_output_tokens": 0,
                        "total_cost": 0.0,
                        "last_used": record.timestamp
                    }

                stats = model_stats[model_name]
                stats["total_input_tokens"] += record.input_tokens
                stats["total_output_tokens"] += record.output_tokens
                stats["total_cost"] += record.total_cost

                # Update last used timestamp if more recent
                if record.timestamp > stats["last_used"]:
                    stats["last_used"] = record.timestamp

            # Convert model stats to Pydantic models
            models_used = [ModelUsageStats(**stats) for stats in model_stats.values()]

            # Get recent requests with model information in a single query
            recent_query = (
                base_query
                .order_by(ModelHistory.timestamp.desc())
                .limit(limit_recent)
            )

            recent_requests = []
            total_input_tokens = 0
            total_output_tokens = 0
            total_cost = 0.0

            for record in recent_query:
                recent_requests.append(RequestRecord(
                    request_id=record.request_id,
                    timestamp=record.timestamp,
                    model_name=record.model.name,
                    status=record.status,
                    input_tokens=record.input_tokens,
                    output_tokens=record.output_tokens,
                    total_cost=record.total_cost,
                    error_message=record.error_message
                ))

                # Update totals for successful requests
                if record.status == "success":
                    total_input_tokens += record.input_tokens
                    total_output_tokens += record.output_tokens
                    total_cost += record.total_cost

            # Create and return the complete usage data
            return ClientUsageData(
                client_id=client_id,
                total_requests=total_requests,
                successful_requests=successful_requests,
                failed_requests=failed_requests,
                total_input_tokens=total_input_tokens,
                total_output_tokens=total_output_tokens,
                total_cost=total_cost,
                models_used=models_used,
                recent_requests=recent_requests
            )

        except Exception as e:
            logger.error(f"Failed to get client usage data: {e}")
            # Return minimal data with error information
            return ClientUsageData(
                client_id=client_id,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                total_input_tokens=0,
                total_output_tokens=0,
                total_cost=0.0,
                models_used=[],
                recent_requests=[]
            )

    def _get_or_create_model(self, model_name: str) -> LLMModel:
        """
        Get or create a model record.

        Args:
            model_name: Name of the model

        Returns:
            LLMModel: The model record
        """
        try:
            model = LLMModel.get(LLMModel.name == model_name)
            return model
        except Exception:
            # Extract provider from model name if available
            provider = None
            if "/" in model_name:
                parts = model_name.split("/")
                if len(parts) >= 2:
                    provider = parts[0]

            # Create a new model record
            return LLMModel.create(
                name=model_name,
                provider=provider,
                last_updated=datetime.now()
            )

    def _get_current_usage(self) -> Optional[ModelHistory]:
        """
        Get the current usage record.

        Returns:
            ModelHistory: The current usage record
        """
        if not self._current_request_id:
            return None

        try:
            return ModelHistory.get(ModelHistory.request_id == self._current_request_id)
        except Exception:
            return None

    def _update_model_token_counts(self, model, input_tokens, output_tokens):
        """Update token counters in the model."""
        if not model:
            return None

        # Update values using Peewee update query
        query = LLMModel.update(
            total_input_tokens=LLMModel.total_input_tokens + input_tokens,
            total_output_tokens=LLMModel.total_output_tokens + output_tokens,
            last_updated=datetime.now()
        ).where(LLMModel.name == model.name)

        query.execute()
        return model

    def get_request_details(self, request_id: str) -> Optional[RequestDetails]:
        """
        Get detailed information about a specific request by its ID.

        Args:
            request_id: The unique ID of the request to retrieve

        Returns:
            Optional[RequestDetails]: Pydantic model with request details if found,
                                   None if request not found or error occurred
        """
        try:
            # Get request with model information in a single query
            query = (
                ModelHistory
                .select(ModelHistory, LLMModel)
                .join(LLMModel)
                .where(ModelHistory.request_id == request_id)
            )

            # Get the record
            record = query.get()

            # Create and return the request details
            return RequestDetails(
                request_id=record.request_id,
                timestamp=record.timestamp,
                model_name=record.model.name,
                model_provider=record.model.provider,
                client_id=record.client_id,
                user_id=record.user_id,
                config_json=record.config_json,
                request_raw=record.request_raw,
                request_json=record.request_json,
                response_json=record.response_json,
                response_raw=record.response_raw,
                input_tokens=record.input_tokens,
                output_tokens=record.output_tokens,
                input_cost=record.input_cost,
                output_cost=record.output_cost,
                total_cost=record.total_cost,
                status=record.status,
                error_message=record.error_message
            )

        except Exception as e:
            logger.error(f"Failed to get request details for {request_id}: {e}")
            return None
