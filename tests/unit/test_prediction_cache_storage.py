import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.ads import PredictResponse, ModerationResultResponse
from repositories.prediction_cache import PredictionCacheStorage


@pytest.mark.asyncio
async def test_prediction_cache_set_and_get():
    storage = PredictionCacheStorage()
    fake_redis = MagicMock()
    fake_redis.get = AsyncMock(return_value=json.dumps({"is_violation": True, "probability": 0.77}))
    fake_redis.set = AsyncMock()

    fake_client = MagicMock()
    fake_client.is_started.return_value = True
    fake_client.get_client.return_value = fake_redis

    with patch("repositories.prediction_cache.get_redis_client", return_value=fake_client):
        response = PredictResponse(is_violation=True, probability=0.77)
        await storage.set(100, response)
        cached = await storage.get(100)

    fake_redis.set.assert_awaited_once_with(
        "prediction:item:100",
        json.dumps({"is_violation": True, "probability": 0.77}),
        ex=storage.TTL_SECONDS,
    )
    fake_redis.get.assert_awaited_once_with("prediction:item:100")
    _, kwargs = fake_redis.set.call_args
    assert kwargs["ex"] == storage.TTL_SECONDS
    assert cached is not None
    assert cached.is_violation is True
    assert cached.probability == 0.77


@pytest.mark.asyncio
async def test_prediction_cache_returns_none_if_redis_not_started():
    storage = PredictionCacheStorage()

    fake_client = MagicMock()
    fake_client.is_started.return_value = False

    with patch("repositories.prediction_cache.get_redis_client", return_value=fake_client):
        cached = await storage.get(100)
        await storage.set(100, PredictResponse(is_violation=False, probability=0.12))

    assert cached is None
    fake_client.get_client.assert_not_called()


@pytest.mark.asyncio
async def test_async_moderation_result_cache_set_and_get():
    storage = PredictionCacheStorage()
    fake_redis = MagicMock()
    fake_redis.get = AsyncMock(
        return_value=json.dumps(
            {
                "task_id": 22,
                "status": "completed",
                "is_violation": False,
                "probability": 0.13,
                "error_message": None,
            }
        )
    )
    fake_redis.set = AsyncMock()

    fake_client = MagicMock()
    fake_client.is_started.return_value = True
    fake_client.get_client.return_value = fake_redis

    with patch("repositories.prediction_cache.get_redis_client", return_value=fake_client):
        result = ModerationResultResponse(
            task_id=22,
            status="completed",
            is_violation=False,
            probability=0.13,
            error_message=None,
        )
        await storage.set_moderation_result(result)
        cached = await storage.get_moderation_result(22)

    fake_redis.set.assert_awaited_once_with(
        "prediction:task:22",
        json.dumps(
            {
                "task_id": 22,
                "status": "completed",
                "is_violation": False,
                "probability": 0.13,
                "error_message": None,
            }
        ),
        ex=storage.ASYNC_TTL_SECONDS,
    )
    fake_redis.get.assert_awaited_once_with("prediction:task:22")
    _, kwargs = fake_redis.set.call_args
    assert kwargs["ex"] == storage.ASYNC_TTL_SECONDS
    assert cached is not None
    assert cached.task_id == 22
    assert cached.status == "completed"


@pytest.mark.asyncio
async def test_prediction_cache_delete_by_item_id():
    storage = PredictionCacheStorage()
    fake_redis = MagicMock()
    fake_redis.delete = AsyncMock()
    fake_client = MagicMock()
    fake_client.is_started.return_value = True
    fake_client.get_client.return_value = fake_redis

    with patch("repositories.prediction_cache.get_redis_client", return_value=fake_client):
        await storage.delete(100)

    fake_redis.delete.assert_awaited_once_with("prediction:item:100")


@pytest.mark.asyncio
async def test_prediction_cache_delete_moderation_result_by_task_id():
    storage = PredictionCacheStorage()
    fake_redis = MagicMock()
    fake_redis.delete = AsyncMock()
    fake_client = MagicMock()
    fake_client.is_started.return_value = True
    fake_client.get_client.return_value = fake_redis

    with patch("repositories.prediction_cache.get_redis_client", return_value=fake_client):
        await storage.delete_moderation_result(22)

    fake_redis.delete.assert_awaited_once_with("prediction:task:22")
