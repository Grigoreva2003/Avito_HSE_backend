import asyncpg
import logging
from typing import Optional
from config import get_settings
from app.metrics import observe_db_query_duration

logger = logging.getLogger(__name__)


class Database:
    """
    Singleton для управления подключением к PostgreSQL.
    Использует asyncpg для асинхронной работы с БД.
    Настройки загружаются из config.py (который читает .env).
    """

    _instance: Optional['Database'] = None
    _pool: Optional[asyncpg.Pool] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def connect(self) -> None:
        """
        Создает пул подключений к PostgreSQL.
        Параметры загружаются из настроек (config.py -> .env).
        """
        if self._pool is None:
            try:
                settings = get_settings()
                db_config = settings.database

                self._pool = await asyncpg.create_pool(
                    host=db_config.host,
                    port=db_config.port,
                    database=db_config.database,
                    user=db_config.user,
                    password=db_config.password,
                    min_size=db_config.pool_min_size,
                    max_size=db_config.pool_max_size
                )
                logger.info(
                    f"Database connection pool created: "
                    f"{db_config.database}@{db_config.host}:{db_config.port}"
                )
            except Exception as e:
                logger.error(f"Failed to create database pool: {e}")
                raise

    async def disconnect(self) -> None:
        """Закрывает пул подключений"""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Database connection pool closed")

    def get_pool(self) -> asyncpg.Pool:
        """
        Возвращает пул подключений.

        Returns:
            asyncpg.Pool: Пул подключений

        Raises:
            RuntimeError: Если пул не инициализирован
        """
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized. Call connect() first.")
        return self._pool

    @staticmethod
    def _extract_query_type(query: str, default: str = "select") -> str:
        first_token = query.strip().split(maxsplit=1)[0].lower() if query and query.strip() else default
        if first_token in {"select", "insert", "update", "delete"}:
            return first_token
        return default

    async def execute(self, query: str, *args) -> str:
        """
        Выполняет SQL запрос (INSERT, UPDATE, DELETE).

        Args:
            query: SQL запрос
            *args: Параметры запроса

        Returns:
            str: Результат выполнения
        """
        pool = self.get_pool()
        query_type = self._extract_query_type(query, default="update")
        with observe_db_query_duration(query_type):
            async with pool.acquire() as conn:
                result = await conn.execute(query, *args)
        return result

    async def fetch(self, query: str, *args) -> list:
        """
        Выполняет SELECT запрос и возвращает все строки.

        Args:
            query: SQL запрос
            *args: Параметры запроса

        Returns:
            list: Список записей
        """
        pool = self.get_pool()
        query_type = self._extract_query_type(query)
        with observe_db_query_duration(query_type):
            async with pool.acquire() as conn:
                result = await conn.fetch(query, *args)
        return result

    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """
        Выполняет SELECT запрос и возвращает одну строку.

        Args:
            query: SQL запрос
            *args: Параметры запроса

        Returns:
            Optional[asyncpg.Record]: Запись или None
        """
        pool = self.get_pool()
        query_type = self._extract_query_type(query)
        with observe_db_query_duration(query_type):
            async with pool.acquire() as conn:
                result = await conn.fetchrow(query, *args)
        return result

    async def fetchval(self, query: str, *args):
        """
        Выполняет SELECT запрос и возвращает одно значение.

        Args:
            query: SQL запрос
            *args: Параметры запроса

        Returns:
            Any: Значение первого столбца первой строки
        """
        pool = self.get_pool()
        query_type = self._extract_query_type(query)
        with observe_db_query_duration(query_type):
            async with pool.acquire() as conn:
                result = await conn.fetchval(query, *args)
        return result


# Глобальная функция для получения экземпляра
def get_database() -> Database:
    """Получить экземпляр Database (синглтон)"""
    return Database()
