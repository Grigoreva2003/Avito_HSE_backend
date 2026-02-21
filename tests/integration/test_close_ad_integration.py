import pytest
import pytest_asyncio

from app.clients import get_redis_client
from models.ads import ModerationResultResponse, PredictResponse
from repositories import AdRepository, ModerationResultRepository, SellerRepository
from repositories.prediction_cache import PredictionCacheStorage
from services.moderation import ModerationService
from database import get_database


@pytest.mark.integration
@pytest.mark.asyncio
class TestCloseAdIntegration:
    @pytest_asyncio.fixture(autouse=True)
    async def setup_db(self):
        db = get_database()
        await db.connect()
        try:
            yield
        finally:
            await db.disconnect()

    @pytest_asyncio.fixture(autouse=True)
    async def setup_redis(self):
        redis_client = get_redis_client()
        started_here = False
        try:
            if not redis_client.is_started():
                await redis_client.start()
                started_here = True
        except Exception as e:
            pytest.skip(f"Redis недоступен: {e}")

        client = redis_client.get_client()
        keys = await client.keys("prediction:*")
        if keys:
            await client.delete(*keys)

        try:
            yield
        finally:
            keys = await client.keys("prediction:*")
            if keys:
                await client.delete(*keys)
            if started_here:
                await redis_client.stop()

    async def test_close_ad_removes_from_postgres_and_redis(self):
        seller_repo = SellerRepository()
        ad_repo = AdRepository()
        moderation_repo = ModerationResultRepository()
        cache = PredictionCacheStorage()
        service = ModerationService()

        seller = await seller_repo.create(name="Seller for close", is_verified=True)
        ad = await ad_repo.create(
            seller_id=seller.id,
            name="Ad to close",
            description="Description",
            category=1,
            images_qty=1,
        )
        moderation = await moderation_repo.create(item_id=ad.id, status="completed")

        await cache.set(ad.id, PredictResponse(is_violation=False, probability=0.2))
        await cache.set_moderation_result(
            ModerationResultResponse(
                task_id=moderation.id,
                status="completed",
                is_violation=False,
                probability=0.2,
                error_message=None,
            )
        )

        assert await cache.get(ad.id) is not None
        assert await cache.get_moderation_result(moderation.id) is not None

        await service.close_ad(ad.id)

        assert await ad_repo.get_by_id(ad.id) is None
        assert await moderation_repo.get_by_id(moderation.id) is None
        assert await cache.get(ad.id) is None
        assert await cache.get_moderation_result(moderation.id) is None

        await seller_repo.delete(seller.id)
