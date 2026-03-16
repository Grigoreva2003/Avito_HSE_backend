import hashlib
from uuid import uuid4

import pytest
import pytest_asyncio

from database import get_database
from repositories.accounts import AccountRepository


@pytest.mark.integration
@pytest.mark.asyncio
class TestAccountRepositoryIntegration:
    @pytest_asyncio.fixture(autouse=True)
    async def ensure_database_pool(self):
        db = get_database()
        await db.connect()
        try:
            yield
        finally:
            await db.disconnect()

    async def test_create_and_get_by_id(self):
        repository = AccountRepository()
        login = f"int_user_{uuid4().hex[:8]}"

        account = await repository.create(login=login, password="secret")
        try:
            assert account is not None
            assert account.login == login
            assert account.password == hashlib.md5("secret".encode("utf-8")).hexdigest()
            assert account.is_blocked is False

            fetched = await repository.get_by_id(account.id)
            assert fetched is not None
            assert fetched.id == account.id
            assert fetched.login == login
        finally:
            await repository.delete(account.id)

    async def test_get_by_login_and_password_uses_hash(self):
        repository = AccountRepository()
        login = f"int_user_{uuid4().hex[:8]}"

        account = await repository.create(login=login, password="password-123")
        try:
            found = await repository.get_by_login_and_password(
                login=login,
                password="password-123",
            )
            assert found is not None
            assert found.id == account.id

            not_found = await repository.get_by_login_and_password(
                login=login,
                password="wrong-password",
            )
            assert not_found is None
        finally:
            await repository.delete(account.id)

    async def test_block_and_delete(self):
        repository = AccountRepository()
        login = f"int_user_{uuid4().hex[:8]}"
        account = await repository.create(login=login, password="secret")

        blocked = await repository.block(account.id)
        assert blocked is True

        blocked_account = await repository.get_by_id(account.id)
        assert blocked_account is not None
        assert blocked_account.is_blocked is True

        deleted = await repository.delete(account.id)
        assert deleted is True
        assert await repository.get_by_id(account.id) is None
