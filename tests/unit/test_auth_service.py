import pytest
from unittest.mock import AsyncMock

from repositories.accounts import Account
from services.auth import AuthService
from services.exceptions import InvalidCredentialsError, AccountBlockedError, AuthenticationRequiredError


@pytest.mark.asyncio
async def test_authenticate_success():
    repo = AsyncMock()
    repo.get_by_login_and_password.return_value = Account(
        id=10,
        login="user",
        password="hashed",
        is_blocked=False,
    )
    service = AuthService(account_repository=repo)

    account = await service.authenticate("user", "pass")

    assert account.id == 10
    repo.get_by_login_and_password.assert_awaited_once_with("user", "pass")


@pytest.mark.asyncio
async def test_authenticate_invalid_credentials():
    repo = AsyncMock()
    repo.get_by_login_and_password.return_value = None
    service = AuthService(account_repository=repo)

    with pytest.raises(InvalidCredentialsError):
        await service.authenticate("user", "wrong")


@pytest.mark.asyncio
async def test_authenticate_blocked_account():
    repo = AsyncMock()
    repo.get_by_login_and_password.return_value = Account(
        id=10,
        login="user",
        password="hashed",
        is_blocked=True,
    )
    service = AuthService(account_repository=repo)

    with pytest.raises(AccountBlockedError):
        await service.authenticate("user", "pass")


def test_create_and_decode_access_token_roundtrip():
    service = AuthService(account_repository=AsyncMock())

    token = service.create_access_token(42)
    decoded_id = service.decode_access_token(token)

    assert isinstance(token, str)
    assert decoded_id == 42


def test_decode_access_token_invalid_token():
    service = AuthService(account_repository=AsyncMock())

    with pytest.raises(AuthenticationRequiredError):
        service.decode_access_token("not-a-jwt")
