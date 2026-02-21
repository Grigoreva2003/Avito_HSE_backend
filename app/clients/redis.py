import logging
from typing import Optional
from redis.asyncio import Redis
from config import get_settings

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Синглтон для работы с Redis.
    Используется как хранилище кэша и временных данных.
    """

    _instance: Optional["RedisClient"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._client: Optional[Redis] = None
        self._settings = get_settings().redis
        logger.info("RedisClient singleton инициализирован")

    async def start(self):
        """Создать подключение к Redis и проверить доступность."""
        if self._client is not None:
            logger.warning("RedisClient уже запущен")
            return

        self._client = Redis.from_url(
            self._settings.url,
            encoding="utf-8",
            decode_responses=True,
        )
        try:
            await self._client.ping()
            logger.info(f"RedisClient подключен к {self._settings.host}:{self._settings.port}/{self._settings.db}")
        except Exception:
            # Закрываем клиент, если проверка ping не прошла
            await self._client.aclose()
            self._client = None
            raise

    async def stop(self):
        """Закрыть подключение к Redis."""
        if self._client is None:
            return

        try:
            await self._client.aclose()
            logger.info("RedisClient остановлен")
        finally:
            self._client = None

    def get_client(self) -> Redis:
        """Получить активный экземпляр Redis клиента."""
        if self._client is None:
            raise RuntimeError("RedisClient не запущен. Вызовите start() сначала.")
        return self._client

    def is_started(self) -> bool:
        """Проверка, запущен ли Redis клиент."""
        return self._client is not None


_redis_client_instance: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    """Получить синглтон экземпляр RedisClient."""
    global _redis_client_instance
    if _redis_client_instance is None:
        _redis_client_instance = RedisClient()
    return _redis_client_instance
