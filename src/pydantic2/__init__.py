from .client.pydantic_ai_client import PydanticAIClient, ModelSettings
from .utils.logger import logger as ai_logger

__version__ = "1.0.3"

__all__ = [
    "PydanticAIClient",
    "ModelSettings",
    "ai_logger"
]
