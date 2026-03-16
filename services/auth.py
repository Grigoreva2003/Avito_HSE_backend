from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Cookie, Depends, HTTPException, status

from config import get_settings
from repositories.accounts import AccountRepository, Account
from services.exceptions import (
    InvalidCredentialsError,
    AccountBlockedError,
    AuthenticationRequiredError,
)


class AuthService:
    def __init__(self, account_repository: Optional[AccountRepository] = None):
        self._account_repository = account_repository or AccountRepository()
        self._settings = get_settings()

    async def authenticate(self, login: str, password: str) -> Account:
        account = await self._account_repository.get_by_login_and_password(login, password)
        if account is None:
            raise InvalidCredentialsError("Invalid login or password")
        if account.is_blocked:
            raise AccountBlockedError("Account is blocked")
        return account

    def create_access_token(self, account_id: int) -> str:
        expires_delta = timedelta(minutes=self._settings.jwt.access_token_expire_minutes)
        payload = {
            "sub": str(account_id),
            "exp": datetime.now(timezone.utc) + expires_delta,
        }
        return jwt.encode(
            payload,
            self._settings.jwt.secret_key,
            algorithm=self._settings.jwt.algorithm,
        )

    def decode_access_token(self, token: str) -> int:
        try:
            payload = jwt.decode(
                token,
                self._settings.jwt.secret_key,
                algorithms=[self._settings.jwt.algorithm],
            )
            account_id = payload.get("sub")
            if account_id is None:
                raise AuthenticationRequiredError("Token does not contain account id")
            return int(account_id)
        except (jwt.InvalidTokenError, ValueError) as exc:
            raise AuthenticationRequiredError("Invalid access token") from exc

    async def get_account_from_token(self, token: str) -> Account:
        account_id = self.decode_access_token(token)
        account = await self._account_repository.get_by_id(account_id)
        if account is None or account.is_blocked:
            raise AuthenticationRequiredError("Account not found or blocked")
        return account


def get_auth_service() -> AuthService:
    return AuthService()


async def get_current_account(
    access_token: str | None = Cookie(default=None, alias="access_token"),
    auth_service: AuthService = Depends(get_auth_service),
) -> Account:
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        return await auth_service.get_account_from_token(access_token)
    except AuthenticationRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
