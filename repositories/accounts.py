import hashlib
import logging
from typing import Optional
from database import get_database

logger = logging.getLogger(__name__)


class Account:
    def __init__(self, id: int, login: str, password: str, is_blocked: bool = False):
        self.id = id
        self.login = login
        self.password = password
        self.is_blocked = is_blocked

    @classmethod
    def from_record(cls, record) -> Optional["Account"]:
        if record is None:
            return None
        return cls(
            id=record["id"],
            login=record["login"],
            password=record["password"],
            is_blocked=record["is_blocked"],
        )


class AccountRepository:
    def __init__(self):
        self.db = get_database()

    @staticmethod
    def hash_password(password: str) -> str:
        return hashlib.md5(password.encode("utf-8")).hexdigest()

    async def create(self, login: str, password: str) -> Account:
        query = """
            INSERT INTO account (login, password)
            VALUES ($1, $2)
            RETURNING id, login, password, is_blocked
        """
        hashed_password = self.hash_password(password)
        record = await self.db.fetchrow(query, login, hashed_password)
        account = Account.from_record(record)
        logger.info(f"Created account: login={login}, id={account.id}")
        return account

    async def get_by_id(self, account_id: int) -> Optional[Account]:
        query = """
            SELECT id, login, password, is_blocked
            FROM account
            WHERE id = $1
        """
        record = await self.db.fetchrow(query, account_id)
        return Account.from_record(record)

    async def delete(self, account_id: int) -> bool:
        query = "DELETE FROM account WHERE id = $1"
        result = await self.db.execute(query, account_id)
        return result == "DELETE 1"

    async def block(self, account_id: int) -> bool:
        query = """
            UPDATE account
            SET is_blocked = TRUE
            WHERE id = $1
            RETURNING id
        """
        row = await self.db.fetchrow(query, account_id)
        return row is not None

    async def get_by_login_and_password(self, login: str, password: str) -> Optional[Account]:
        query = """
            SELECT id, login, password, is_blocked
            FROM account
            WHERE login = $1 AND password = $2
        """
        hashed_password = self.hash_password(password)
        record = await self.db.fetchrow(query, login, hashed_password)
        return Account.from_record(record)
