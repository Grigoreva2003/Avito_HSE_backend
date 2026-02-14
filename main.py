from contextlib import asynccontextmanager
from fastapi import FastAPI
from routers.ads import router as ads_router
import uvicorn
import logging
from ml import get_model_manager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения.
    Инициализирует ModelManager (синглтон) при старте.
    """
    # Startup: инициализация ModelManager
    logger.info("Запуск приложения: инициализация ModelManager...")
    try:
        model_manager = get_model_manager()
        model_manager.load_model("model.pkl")
        logger.info("ModelManager успешно инициализирован, модель готова к использованию")
    except Exception as e:
        logger.error(f"Ошибка при инициализации ModelManager: {e}")
        raise

    yield

    # Shutdown: освобождение ресурсов
    logger.info("Завершение работы приложения...")
    model_manager.unload()


app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {'message': 'Hello World'}


app.include_router(ads_router, tags=["Ads"])


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
