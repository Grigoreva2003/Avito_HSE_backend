from unittest.mock import AsyncMock, patch

import pytest

from services.exceptions import AdNotFoundError
from services.moderation import ModerationService


@pytest.mark.asyncio
async def test_close_ad_deletes_postgres_and_redis_data():
    with patch("services.moderation.AdRepository") as mock_ad_repo_cls, \
         patch("services.moderation.ModerationResultRepository") as mock_mod_repo_cls, \
         patch("services.moderation.PredictionCacheStorage") as mock_cache_cls:
        mock_ad_repo = AsyncMock()
        mock_ad_repo.get_by_id.return_value = object()
        mock_ad_repo.delete.return_value = True
        mock_ad_repo_cls.return_value = mock_ad_repo

        mock_mod_repo = AsyncMock()
        mock_mod_repo.get_task_ids_by_item_id.return_value = [11, 12]
        mock_mod_repo.delete_by_item_id.return_value = 2
        mock_mod_repo_cls.return_value = mock_mod_repo

        mock_cache = AsyncMock()
        mock_cache_cls.return_value = mock_cache

        service = ModerationService()
        await service.close_ad(100)

        mock_ad_repo.get_by_id.assert_awaited_once_with(100, include_seller=False)
        mock_mod_repo.get_task_ids_by_item_id.assert_awaited_once_with(100)
        mock_mod_repo.delete_by_item_id.assert_awaited_once_with(100)
        mock_ad_repo.delete.assert_awaited_once_with(100)
        mock_cache.delete.assert_awaited_once_with(100)
        assert mock_cache.delete_moderation_result.await_count == 2
        mock_cache.delete_moderation_result.assert_any_await(11)
        mock_cache.delete_moderation_result.assert_any_await(12)


@pytest.mark.asyncio
async def test_close_ad_raises_not_found():
    with patch("services.moderation.AdRepository") as mock_ad_repo_cls:
        mock_ad_repo = AsyncMock()
        mock_ad_repo.get_by_id.return_value = None
        mock_ad_repo_cls.return_value = mock_ad_repo

        service = ModerationService()

        with pytest.raises(AdNotFoundError):
            await service.close_ad(99999)
