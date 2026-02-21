from contextlib import asynccontextmanager
from fastapi import FastAPI
from routers.ads import router as ads_router
import uvicorn
import logging
from ml import get_model_manager
from database import get_database
from app.clients import get_kafka_producer, get_redis_client
from config import get_settings

# Загружаем настройки
settings = get_settings()

# Настройка логирования из конфига
logging.basicConfig(
    level=getattr(logging, settings.app.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения.
    Инициализирует Database, ModelManager и Kafka Producer при старте.
    """
    # Startup: инициализация Database
    logger.info("Запуск приложения: подключение к базе данных...")
    try:
        db = get_database()
        await db.connect()
        logger.info("Подключение к БД успешно установлено")
    except Exception as e:
        logger.error(f"Ошибка при подключении к БД: {e}")
        logger.warning("Приложение запущено БЕЗ подключения к БД")

    # Startup: инициализация ModelManager
    logger.info("Запуск приложения: загрузка ML-модели...")
    try:
        model_manager = get_model_manager()
        model_manager.load_model(settings.ml.model_path)
        logger.info("ML-модель успешно загружена и готова к использованию")
    except Exception as e:
        logger.error(f"Ошибка при загрузке модели: {e}")
        raise

    # Startup: запуск Kafka Producer
    logger.info("Запуск приложения: подключение к Kafka...")
    try:
        kafka_producer = get_kafka_producer()
        await kafka_producer.start()
        logger.info("Kafka Producer успешно запущен")
    except Exception as e:
        logger.error(f"Ошибка при запуске Kafka Producer: {e}")
        logger.warning("Приложение запущено БЕЗ Kafka Producer")

    # Startup: подключение к Redis
    logger.info("Запуск приложения: подключение к Redis...")
    try:
        redis_client = get_redis_client()
        await redis_client.start()
        logger.info("Redis клиент успешно подключен")
    except Exception as e:
        logger.error(f"Ошибка при подключении к Redis: {e}")
        logger.warning("Приложение запущено БЕЗ Redis")

    yield

    # Shutdown: освобождение ресурсов
    logger.info("Завершение работы приложения...")

    # Остановка Kafka Producer
    try:
        kafka_producer = get_kafka_producer()
        await kafka_producer.stop()
        logger.info("Kafka Producer остановлен")
    except Exception as e:
        logger.error(f"Ошибка при остановке Kafka Producer: {e}")

    # Остановка Redis клиента
    try:
        redis_client = get_redis_client()
        await redis_client.stop()
        logger.info("Redis клиент остановлен")
    except Exception as e:
        logger.error(f"Ошибка при остановке Redis клиента: {e}")

    # Выгружаем модель
    model_manager.unload()

    # Закрываем подключение к БД
    try:
        await db.disconnect()
        logger.info("Подключение к БД закрыто")
    except Exception as e:
        logger.error(f"Ошибка при закрытии подключения к БД: {e}")


app = FastAPI(
    title=settings.app.app_name,
    version=settings.app.app_version,
    lifespan=lifespan
)

@app.get("/")
async def root():
    return {
        'message': 'Hello World',
        'service': settings.app.app_name,
        'version': settings.app.app_version
    }


app.include_router(ads_router, tags=["Ads"])


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.app.host,
        port=settings.app.port
    )
