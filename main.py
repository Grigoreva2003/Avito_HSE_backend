from contextlib import asynccontextmanager
from fastapi import FastAPI
from routers.users import router as user_router, root_router
from routers.ads import router as ads_router
import uvicorn
import logging
from model import get_or_create_model

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
    Загружает модель при старте и освобождает ресурсы при завершении.
    """
    # Startup: загрузка модели
    logger.info("Запуск приложения: загрузка ML-модели...")
    try:
        model = get_or_create_model("model.pkl")
        app.state.model = model
        logger.info("ML-модель успешно загружена и готова к использованию")
    except Exception as e:
        logger.error(f"Ошибка при загрузке модели: {e}")
        app.state.model = None
        raise
    
    yield
    
    # Shutdown: освобождение ресурсов
    logger.info("Завершение работы приложения...")
    app.state.model = None


app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {'message': 'Hello World'}


app.include_router(root_router)
app.include_router(user_router, prefix='/users')
app.include_router(ads_router, tags=["Ads"])


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)