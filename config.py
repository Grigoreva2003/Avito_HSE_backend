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


class Settings:
    """Глобальные настройки приложения"""

    def __init__(self):
        self.app = AppSettings()
        self.database = DatabaseSettings()
        self.ml = MLSettings()
        self.kafka = KafkaSettings()


# Глобальный экземпляр настроек (синглтон)
_settings: Settings | None = None


def get_settings() -> Settings:
    """Получить экземпляр настроек (синглтон)"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
