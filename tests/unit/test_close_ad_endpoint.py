from http import HTTPStatus
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from services.exceptions import AdNotFoundError


class TestCloseAdEndpoint:
    def test_close_ad_success(self, app_client: TestClient):
        with patch("routers.ads.ModerationService.close_ad", new_callable=AsyncMock) as mock_close:
            response = app_client.post("/close", json={"item_id": 100})

        assert response.status_code == HTTPStatus.OK
        assert response.json() == {
            "item_id": 100,
            "status": "closed",
            "message": "Ad successfully closed",
        }
        mock_close.assert_awaited_once_with(100)

    def test_close_ad_not_found(self, app_client: TestClient):
        with patch("routers.ads.ModerationService.close_ad", new_callable=AsyncMock) as mock_close:
            mock_close.side_effect = AdNotFoundError("ad not found")
            response = app_client.post("/close", json={"item_id": 99999})

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_close_ad_validation_error(self, app_client: TestClient):
        response = app_client.post("/close", json={"item_id": 0})
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
