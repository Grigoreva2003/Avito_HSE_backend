from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class DatabaseSettings(BaseSettings):
    """Настройки подключения к PostgreSQL"""

    host: str = Field(default="localhost", description="Хост БД")
    port: int = Field(default=5432, description="Порт БД")
    user: str = Field(default="vagrigorevaaa", description="Пользователь БД")
    password: str = Field(default="", description="Пароль БД")
    database: str = Field(default="avito_moderation", description="Имя БД")
    pool_min_size: int = Field(default=10, description="Минимальный размер пула подключений")
    pool_max_size: int = Field(default=20, description="Максимальный размер пула подключений")

    model_config = SettingsConfigDict(
        env_prefix="DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @property
    def url(self) -> str:
        """Получить URL подключения к БД"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    @property
    def async_url(self) -> str:
        """Получить асинхронный URL подключения к БД"""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class AppSettings(BaseSettings):
    """Общие настройки приложения"""

    app_name: str = Field(default="Avito Moderation Service", description="Название приложения")
    app_version: str = Field(default="1.0.0", description="Версия приложения")
    host: str = Field(default="0.0.0.0", description="Хост для запуска сервера")
    port: int = Field(default=8003, description="Порт для запуска сервера")
    debug: bool = Field(default=False, description="Режим отладки")
    log_level: str = Field(default="INFO", description="Уровень логирования")

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class MLSettings(BaseSettings):
    """Настройки ML модели"""

    model_path: str = Field(default="model.pkl", description="Путь к файлу модели")
    model_version: str = Field(default="1.0.0", description="Версия модели")

    model_config = SettingsConfigDict(
        env_prefix="ML_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class KafkaSettings(BaseSettings):
    """Настройки Kafka"""

    bootstrap_servers: str = Field(default="localhost:9092", description="Kafka bootstrap серверы")
    topic_moderation: str = Field(default="moderation", description="Топик для модерации")
    topic_dlq: str = Field(default="moderation_dlq", description="Dead Letter Queue топик")
    producer_timeout: int = Field(default=10, description="Таймаут отправки сообщения (сек)")
    consumer_group_id: str = Field(default="moderation_workers", description="Consumer group ID")

    model_config = SettingsConfigDict(
        env_prefix="KAFKA_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class RedisSettings(BaseSettings):
    """Настройки Redis"""

    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    db: int = Field(default=0, description="Redis database index")
    password: str = Field(default="", description="Redis password")
    ssl: bool = Field(default=False, description="Использовать SSL для Redis")

    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @property
    def url(self) -> str:
        """Получить URL подключения к Redis"""
        auth_part = f":{self.password}@" if self.password else ""
        scheme = "rediss" if self.ssl else "redis"
        return f"{scheme}://{auth_part}{self.host}:{self.port}/{self.db}"


class JWTSettings(BaseSettings):
    """Настройки JWT авторизации"""

    secret_key: str = Field(default="change-me-in-production", description="JWT secret key")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=60, description="Access token TTL in minutes")
    cookie_name: str = Field(default="access_token", description="Cookie name for JWT token")

    model_config = SettingsConfigDict(
        env_prefix="JWT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class SentrySettings(BaseSettings):
    """Настройки Sentry"""

    dsn: str = Field(default="", description="Sentry DSN")
    traces_sample_rate: float = Field(default=1.0, description="Доля трейсинга (0..1)")
    environment: str = Field(default="development", description="Окружение для Sentry")
    enabled: bool = Field(default=False, description="Включить отправку ошибок в Sentry")

    model_config = SettingsConfigDict(
        env_prefix="SENTRY_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class Settings:
    """Глобальные настройки приложения"""

    def __init__(self):
        self.app = AppSettings()
        self.database = DatabaseSettings()
        self.ml = MLSettings()
        self.kafka = KafkaSettings()
        self.redis = RedisSettings()
        self.jwt = JWTSettings()
        self.sentry = SentrySettings()


# Глобальный экземпляр настроек (синглтон)
_settings: Settings | None = None


def get_settings() -> Settings:
    """Получить экземпляр настроек (синглтон)"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
