import pytest
import pytest_asyncio

from database import get_database
from repositories import ModerationResultRepository, SellerRepository, AdRepository


@pytest.mark.integration
@pytest.mark.asyncio
class TestModerationResultsRepository:
    """Integration-тесты репозитория moderation_results в PostgreSQL."""

    @pytest_asyncio.fixture(autouse=True)
    async def ensure_database_pool(self):
        db = get_database()
        await db.connect()
        try:
            yield
        finally:
            await db.disconnect()

    async def test_create_and_get_by_id(self):
        seller_repo = SellerRepository()
        ad_repo = AdRepository()
        moderation_repo = ModerationResultRepository()

        seller = await seller_repo.create(name="repo seller", is_verified=False)
        ad = await ad_repo.create(
            seller_id=seller.id,
            name="repo ad",
            description="repo desc",
            category=1,
            images_qty=0,
        )

        result = await moderation_repo.create(item_id=ad.id, status="pending")
        fetched = await moderation_repo.get_by_id(result.id)

        assert fetched is not None
        assert fetched.id == result.id
        assert fetched.item_id == ad.id
        assert fetched.status == "pending"

        await ad_repo.delete(ad.id)
        await seller_repo.delete(seller.id)

    async def test_get_task_ids_and_delete_by_item_id(self):
        seller_repo = SellerRepository()
        ad_repo = AdRepository()
        moderation_repo = ModerationResultRepository()

        seller = await seller_repo.create(name="repo seller 2", is_verified=True)
        ad = await ad_repo.create(
            seller_id=seller.id,
            name="repo ad 2",
            description="repo desc 2",
            category=2,
            images_qty=1,
        )

        first = await moderation_repo.create(item_id=ad.id, status="pending")
        second = await moderation_repo.create(item_id=ad.id, status="failed")

        task_ids = await moderation_repo.get_task_ids_by_item_id(ad.id)
        assert first.id in task_ids
        assert second.id in task_ids

        deleted_count = await moderation_repo.delete_by_item_id(ad.id)
        assert deleted_count >= 2
        assert await moderation_repo.get_by_id(first.id) is None
        assert await moderation_repo.get_by_id(second.id) is None

        await ad_repo.delete(ad.id)
        await seller_repo.delete(seller.id)
