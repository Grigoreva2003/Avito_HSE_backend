from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.ads import PredictResponse
from services.moderation import ModerationService


@pytest.mark.asyncio
async def test_simple_predict_uses_cache_before_db_and_model():
    cached_response = PredictResponse(is_violation=True, probability=0.91)

    with patch("services.moderation.PredictionCacheStorage") as mock_cache_cls, \
         patch("services.moderation.AdRepository") as mock_repo_cls:
        mock_cache = AsyncMock()
        mock_cache.get.return_value = cached_response
        mock_cache_cls.return_value = mock_cache

        mock_repo = AsyncMock()
        mock_repo_cls.return_value = mock_repo

        service = ModerationService()
        service._model_manager = MagicMock()

        result = await service.predict_violation_by_item_id(100)

        assert result == cached_response
        mock_cache.get.assert_awaited_once_with(100)
        mock_repo.get_by_id.assert_not_called()
        service._model_manager.predict.assert_not_called()


@pytest.mark.asyncio
async def test_simple_predict_reads_db_and_caches_on_miss():
    ad = SimpleNamespace(
        seller_id=1,
        seller_is_verified=False,
        images_qty=0,
        description="spam",
        category=1,
    )

    with patch("services.moderation.PredictionCacheStorage") as mock_cache_cls, \
         patch("services.moderation.AdRepository") as mock_repo_cls:
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None
        mock_cache_cls.return_value = mock_cache

        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = ad
        mock_repo_cls.return_value = mock_repo

        service = ModerationService()
        service._model_manager = MagicMock()
        service._model_manager.is_available.return_value = True
        service._model_manager.predict.return_value = (False, 0.11)

        result = await service.predict_violation_by_item_id(100)

        assert result.is_violation is False
        assert result.probability == 0.11
        mock_repo.get_by_id.assert_awaited_once_with(100, include_seller=True)
        mock_cache.set.assert_awaited_once()
