import json

import pytest
import pytest_asyncio

from app.clients import get_redis_client
from models.ads import ModerationResultResponse, PredictResponse
from repositories.prediction_cache import PredictionCacheStorage


@pytest_asyncio.fixture
async def redis_cache_storage():
    redis_client = get_redis_client()

    try:
        await redis_client.start()
    except Exception as e:
        pytest.skip(f"Redis недоступен для integration тестов: {e}")

    client = redis_client.get_client()
    storage = PredictionCacheStorage()

    # Чистим только ключи тестового префикса перед тестом.
    keys = await client.keys("prediction:*")
    if keys:
        await client.delete(*keys)

    try:
        yield storage, client
    finally:
        keys = await client.keys("prediction:*")
        if keys:
            await client.delete(*keys)
        await redis_client.stop()


@pytest.mark.asyncio
async def test_integration_sync_prediction_cache_set_get_and_ttl(redis_cache_storage):
    storage, client = redis_cache_storage
    item_id = 1001
    key = f"prediction:item:{item_id}"

    response = PredictResponse(is_violation=True, probability=0.88)
    await storage.set(item_id, response)

    raw = await client.get(key)
    assert raw is not None
    assert json.loads(raw) == {"is_violation": True, "probability": 0.88}

    cached = await storage.get(item_id)
    assert cached is not None
    assert cached.is_violation is True
    assert cached.probability == 0.88

    ttl = await client.ttl(key)
    assert 0 < ttl <= storage.TTL_SECONDS


@pytest.mark.asyncio
async def test_integration_async_moderation_cache_set_get_and_ttl(redis_cache_storage):
    storage, client = redis_cache_storage
    task_id = 2002
    key = f"prediction:task:{task_id}"

    result = ModerationResultResponse(
        task_id=task_id,
        status="completed",
        is_violation=False,
        probability=0.21,
        error_message=None,
    )
    await storage.set_moderation_result(result)

    raw = await client.get(key)
    assert raw is not None
    assert json.loads(raw) == {
        "task_id": task_id,
        "status": "completed",
        "is_violation": False,
        "probability": 0.21,
        "error_message": None,
    }

    cached = await storage.get_moderation_result(task_id)
    assert cached is not None
    assert cached.task_id == task_id
    assert cached.status == "completed"
    assert cached.is_violation is False
    assert cached.probability == 0.21

    ttl = await client.ttl(key)
    assert 0 < ttl <= storage.ASYNC_TTL_SECONDS
