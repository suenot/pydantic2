from pydantic2.usage.usage_logger import UsageLogger
from pydantic2.models.base_models import Request
from pydantic import BaseModel


class DummyModel(BaseModel):
    pass


def test_usage_logger():
    """Test that usage logger can be initialized and returns stats."""
    logger = UsageLogger(Request(
        client_id='demo',
        answer_model=DummyModel,
        temperature=0.7,
        max_tokens=1000,
        max_budget=10.0
    ))

    # Get usage stats and verify they can be serialized to JSON
    stats = logger.get_usage_stats()
    assert stats is not None
    json_stats = stats.model_dump_json(indent=2)
    assert isinstance(json_stats, str)
    assert len(json_stats) > 0
