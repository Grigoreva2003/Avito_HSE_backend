import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock

from repositories.accounts import Account
from services.auth import get_current_account
from services.exceptions import AuthenticationRequiredError


@pytest.mark.asyncio
async def test_get_current_account_success():
    auth_service = AsyncMock()
    expected_account = Account(id=1, login="u", password="h", is_blocked=False)
    auth_service.get_account_from_token.return_value = expected_account

    account = await get_current_account(access_token="token", auth_service=auth_service)

    assert account is expected_account
    auth_service.get_account_from_token.assert_awaited_once_with("token")


@pytest.mark.asyncio
async def test_get_current_account_missing_token():
    auth_service = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await get_current_account(access_token=None, auth_service=auth_service)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_account_invalid_token():
    auth_service = AsyncMock()
    auth_service.get_account_from_token.side_effect = AuthenticationRequiredError("bad token")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_account(access_token="bad", auth_service=auth_service)

    assert exc_info.value.status_code == 401
