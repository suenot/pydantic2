import pytest
from src.pydantic2 import PydanticAIClient
from src.pydantic2.client.exceptions import BudgetExceeded
from pydantic import BaseModel
from unittest.mock import patch


class ChatResponse(BaseModel):
    """Simple chat response model"""
    message: str
    confidence: float


@pytest.fixture
def client():
    """Create a test client"""
    with PydanticAIClient(
        model_name="test-model",
        client_id="test_client",
        user_id="test_user"
    ) as client:
        yield client


def test_budget_tracking():
    """Test budget exceeded error"""
    with patch('src.pydantic2.client.pydantic_ai_client.PydanticAIClient._calculate_cost') as mock_cost:
        mock_cost.return_value = 0.0002  # Higher than max_budget

        with PydanticAIClient(
            model_name="openai/gpt-4o-mini",
            client_id="test_budget",
            user_id="test_user",
            max_budget=0.0001
        ) as client:
            client.message_handler.add_message_user("Test message")

            with pytest.raises(BudgetExceeded):
                client.generate(
                    result_type=ChatResponse
                )
