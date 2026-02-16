"""
Тесты для асинхронной модерации через Kafka.
"""

import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from http import HTTPStatus

from services.exceptions import AdNotFoundError, ModerationResultNotFoundError
from services.async_moderation import AsyncModerationService

ITEM_ID = 100
TASK_ID = 123
NOT_FOUND_ITEM_ID = 99999
INVALID_ITEM_ID = -1


class TestAsyncPredict:
    """Тесты для /async_predict на основе веток обработчика в routers/ads.py."""

    @staticmethod
    def _patch_submit():
        return patch(
            "routers.ads.AsyncModerationService.submit_moderation_request",
            new_callable=AsyncMock,
        )

    def test_async_predict_returns_correct_response(self, app_client: TestClient):
        """Успешный сценарий: 200 + task_id/status/message."""
        with self._patch_submit() as mock_submit:
            mock_submit.return_value = TASK_ID

            response = app_client.post("/async_predict", json={"item_id": ITEM_ID})

            assert response.status_code == HTTPStatus.OK
            assert response.json() == {
                "task_id": TASK_ID,
                "status": "pending",
                "message": "Moderation request accepted",
            }
            mock_submit.assert_awaited_once_with(ITEM_ID)

    @pytest.mark.parametrize(
        "item_id, side_effect, expected_status, detail_part, expected_awaited",
        [
            (
                NOT_FOUND_ITEM_ID,
                AdNotFoundError("ad not found"),
                HTTPStatus.NOT_FOUND,
                "не найдено",
                NOT_FOUND_ITEM_ID,
            ),
            (
                INVALID_ITEM_ID,
                None,
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "detail",
                None,
            ),
            (
                ITEM_ID,
                RuntimeError("unexpected error"),
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "внутренняя ошибка сервера",
                ITEM_ID,
            ),
        ],
    )
    def test_async_predict_error_branches(
        self,
        app_client: TestClient,
        item_id: int,
        side_effect,
        expected_status: HTTPStatus,
        detail_part: str,
        expected_awaited: int | None,
    ):
        """Компактная проверка веток ошибок: 404 / 422 / 500."""
        with self._patch_submit() as mock_submit:
            if side_effect is not None:
                mock_submit.side_effect = side_effect

            response = app_client.post("/async_predict", json={"item_id": item_id})

            assert response.status_code == expected_status
            data = response.json()

            if expected_status == HTTPStatus.UNPROCESSABLE_ENTITY:
                assert detail_part in data
            else:
                assert detail_part in data["detail"].lower()

            if expected_awaited is None:
                mock_submit.assert_not_called()
            else:
                mock_submit.assert_awaited_once_with(expected_awaited)


class TestAsyncPredictTaskCreation:
    """Тесты фактического создания задачи модерации в сервисе."""

    @staticmethod
    def _patch_dependencies():
        return (
            patch("services.async_moderation.AdRepository"),
            patch("services.async_moderation.ModerationResultRepository"),
            patch("services.async_moderation.get_kafka_producer"),
        )

    @pytest.mark.asyncio
    async def test_submit_moderation_request_creates_task_and_sends_kafka(self):
        """Успех: объявление найдено, запись pending создана, сообщение ушло в Kafka."""
        fake_ad = SimpleNamespace(id=100, name="Test Ad")
        fake_result = SimpleNamespace(id=321)
        fake_kafka = AsyncMock()

        patch_ad, patch_mod, patch_kafka = self._patch_dependencies()
        with patch_ad as mock_ad_repo_cls, patch_mod as mock_mod_repo_cls, patch_kafka as mock_get_kafka:
            mock_ad_repo = AsyncMock()
            mock_ad_repo.get_by_id.return_value = fake_ad
            mock_ad_repo_cls.return_value = mock_ad_repo

            mock_mod_repo = AsyncMock()
            mock_mod_repo.create.return_value = fake_result
            mock_mod_repo_cls.return_value = mock_mod_repo

            mock_get_kafka.return_value = fake_kafka

            service = AsyncModerationService()
            task_id = await service.submit_moderation_request(100)

            assert task_id == 321
            mock_ad_repo.get_by_id.assert_awaited_once_with(100, include_seller=False)
            mock_mod_repo.create.assert_awaited_once_with(item_id=100, status="pending")
            fake_kafka.send_moderation_request.assert_awaited_once_with(100)
            mock_mod_repo.update_failed.assert_not_called()

    @pytest.mark.asyncio
    async def test_submit_moderation_request_ad_not_found_raises_404_domain_error(self):
        """Неуспех: объявление не найдено -> AdNotFoundError, задача не создается."""
        fake_kafka = AsyncMock()

        patch_ad, patch_mod, patch_kafka = self._patch_dependencies()
        with patch_ad as mock_ad_repo_cls, patch_mod as mock_mod_repo_cls, patch_kafka as mock_get_kafka:
            mock_ad_repo = AsyncMock()
            mock_ad_repo.get_by_id.return_value = None
            mock_ad_repo_cls.return_value = mock_ad_repo

            mock_mod_repo = AsyncMock()
            mock_mod_repo_cls.return_value = mock_mod_repo

            mock_get_kafka.return_value = fake_kafka

            service = AsyncModerationService()

            with pytest.raises(AdNotFoundError):
                await service.submit_moderation_request(99999)

            mock_ad_repo.get_by_id.assert_awaited_once_with(99999, include_seller=False)
            mock_mod_repo.create.assert_not_called()
            fake_kafka.send_moderation_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_submit_moderation_request_kafka_error_marks_failed_and_reraises(self):
        """Ошибка обработки: при падении Kafka статус переводится в failed и ошибка пробрасывается."""
        fake_ad = SimpleNamespace(id=100, name="Test Ad")
        fake_result = SimpleNamespace(id=777)
        fake_kafka = AsyncMock()
        fake_kafka.send_moderation_request.side_effect = RuntimeError("kafka down")

        patch_ad, patch_mod, patch_kafka = self._patch_dependencies()
        with patch_ad as mock_ad_repo_cls, patch_mod as mock_mod_repo_cls, patch_kafka as mock_get_kafka:
            mock_ad_repo = AsyncMock()
            mock_ad_repo.get_by_id.return_value = fake_ad
            mock_ad_repo_cls.return_value = mock_ad_repo

            mock_mod_repo = AsyncMock()
            mock_mod_repo.create.return_value = fake_result
            mock_mod_repo_cls.return_value = mock_mod_repo

            mock_get_kafka.return_value = fake_kafka

            service = AsyncModerationService()

            with pytest.raises(RuntimeError):
                await service.submit_moderation_request(100)

            mock_mod_repo.create.assert_awaited_once_with(item_id=100, status="pending")
            fake_kafka.send_moderation_request.assert_awaited_once_with(100)
            mock_mod_repo.update_failed.assert_awaited_once()


class TestModerationResultEndpoint:
    """Тесты получения статуса модерации через /moderation_result/{task_id}."""

    @staticmethod
    def _patch_result():
        return patch(
            "routers.ads.AsyncModerationService.get_moderation_result",
            new_callable=AsyncMock,
        )

    def test_moderation_result_success(self, app_client: TestClient):
        """Успех: сервис возвращает статус, роутер отдает 200."""
        service_result = {
            "task_id": 123,
            "status": "pending",
            "is_violation": None,
            "probability": None,
            "error_message": None,
        }
        with self._patch_result() as mock_get_result:
            mock_get_result.return_value = service_result

            response = app_client.get("/moderation_result/123")

            assert response.status_code == HTTPStatus.OK
            assert response.json() == service_result
            mock_get_result.assert_awaited_once_with(123)

    def test_moderation_result_not_found(self, app_client: TestClient):
        """Ошибка: задача не найдена -> 404."""
        with self._patch_result() as mock_get_result:
            mock_get_result.side_effect = ModerationResultNotFoundError("not found")

            response = app_client.get("/moderation_result/99999")

            assert response.status_code == HTTPStatus.NOT_FOUND
            assert "не найдена" in response.json()["detail"].lower()
            mock_get_result.assert_awaited_once_with(99999)


class TestModerationWorker:
    """Тесты обработки сообщений воркером и DLQ."""

    @staticmethod
    def _message(item_id, retry_count=0):
        return SimpleNamespace(
            value={
                "item_id": item_id,
                "timestamp": "2026-01-01T00:00:00Z",
                "retry_count": retry_count,
            },
            topic="moderation",
            partition=0,
            offset=1,
        )

    @pytest.mark.asyncio
    async def test_worker_process_message_success_updates_result(self):
        """Воркер получает сообщение, делает predict и обновляет moderation_results."""
        from app.workers.moderation_worker import ModerationWorker

        worker = ModerationWorker()
        worker.ad_repository = AsyncMock()
        worker.db = AsyncMock()
        worker.model_manager = MagicMock()
        worker.model_manager.predict.return_value = (True, 0.91)

        ad = SimpleNamespace(
            seller_id=1,
            seller_is_verified=False,
            images_qty=0,
            description="spam",
            category=1,
        )
        worker.ad_repository.get_by_id.return_value = ad
        worker.db.fetchrow.return_value = {"id": 11}

        message = self._message(item_id=100)

        await worker.process_message(message)

        worker.ad_repository.get_by_id.assert_awaited_once_with(100, include_seller=True)
        worker.model_manager.predict.assert_called_once_with(
            is_verified_seller=False,
            images_qty=0,
            description="spam",
            category=1,
        )
        worker.db.fetchrow.assert_awaited_once()
        # query, is_violation, probability, item_id
        assert worker.db.fetchrow.call_args.args[1:] == (True, 0.91, 100)

    @pytest.mark.asyncio
    async def test_worker_sends_to_dlq_on_missing_item_id(self):
        """Ошибка в сообщении (нет item_id) -> сообщение отправляется в DLQ."""
        from app.workers.moderation_worker import ModerationWorker

        worker = ModerationWorker()
        worker.send_to_dlq = AsyncMock()

        message = SimpleNamespace(
            value={"timestamp": "2026-01-01T00:00:00Z", "retry_count": 0},
            topic="moderation",
            partition=0,
            offset=1,
        )

        await worker.process_message(message)

        worker.send_to_dlq.assert_awaited_once()
        args = worker.send_to_dlq.call_args.args
        assert args[1] == "Missing item_id in message"
