from http import HTTPStatus
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from repositories.accounts import Account
from services.exceptions import InvalidCredentialsError, AccountBlockedError


class TestLoginEndpoint:
    def test_login_success_sets_cookie(self, app_client_no_auth_override: TestClient):
        with patch("routers.ads.AuthService") as mock_auth_service_cls:
            mock_auth_service = mock_auth_service_cls.return_value
            mock_auth_service.authenticate = AsyncMock(
                return_value=Account(
                    id=42,
                    login="user",
                    password="hashed-password",
                    is_blocked=False,
                )
            )
            mock_auth_service.create_access_token.return_value = "jwt-token"

            response = app_client_no_auth_override.post(
                "/login",
                json={"login": "user", "password": "pass"},
            )

        assert response.status_code == HTTPStatus.OK
        assert response.json() == {
            "account_id": 42,
            "message": "Login successful",
        }
        assert response.cookies.get("access_token") == "jwt-token"
        mock_auth_service.authenticate.assert_awaited_once_with("user", "pass")
        mock_auth_service.create_access_token.assert_called_once_with(42)

    def test_login_invalid_credentials(self, app_client_no_auth_override: TestClient):
        with patch("routers.ads.AuthService") as mock_auth_service_cls:
            mock_auth_service = mock_auth_service_cls.return_value
            mock_auth_service.authenticate = AsyncMock(
                side_effect=InvalidCredentialsError("Invalid login or password")
            )

            response = app_client_no_auth_override.post(
                "/login",
                json={"login": "user", "password": "wrong"},
            )

        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert response.json()["detail"] == "Invalid login or password"

    def test_login_blocked_account(self, app_client_no_auth_override: TestClient):
        with patch("routers.ads.AuthService") as mock_auth_service_cls:
            mock_auth_service = mock_auth_service_cls.return_value
            mock_auth_service.authenticate = AsyncMock(
                side_effect=AccountBlockedError("Account is blocked")
            )

            response = app_client_no_auth_override.post(
                "/login",
                json={"login": "blocked", "password": "pass"},
            )

        assert response.status_code == HTTPStatus.FORBIDDEN
        assert response.json()["detail"] == "Account is blocked"

    def test_login_validation_error(self, app_client_no_auth_override: TestClient):
        response = app_client_no_auth_override.post(
            "/login",
            json={"login": "", "password": "pass"},
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


class TestProtectedEndpointsAuth:
    def test_simple_predict_requires_auth(self, app_client_no_auth_override: TestClient):
        response = app_client_no_auth_override.post(
            "/simple_predict",
            json={"item_id": 100},
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED
