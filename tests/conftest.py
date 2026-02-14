import pytest
import asyncio
from fastapi.testclient import TestClient
from main import app
from ml import get_model_manager
from database import get_database
from repositories import SellerRepository, AdRepository


@pytest.fixture
def app_client() -> TestClient:
    """Фикстура для тестового клиента"""
    # Убеждаемся, что ModelManager инициализирован
    model_manager = get_model_manager()
    if not model_manager.is_available():
        model_manager.load_model("model.pkl")
    return TestClient(app)


@pytest.fixture
def make_payload():
    """Фикстура для создания тестового payload с возможностью переопределения полей"""
    def _make_payload(overrides: dict | None = None) -> dict:
        payload = {
            "seller_id": 1,
            "is_verified_seller": True,
            "item_id": 100,
            "name": "Товар",
            "description": "Описание",
            "category": 1,
            "images_qty": 1,
        }
        if overrides:
            payload.update(overrides)
        return payload
    return _make_payload


@pytest.fixture(scope="session")
def event_loop():
    """Создает event loop для асинхронных тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_database(event_loop):
    """
    Подключение к БД перед тестами и отключение после.
    """
    db = get_database()
    
    # Подключаемся к БД
    event_loop.run_until_complete(db.connect())
    
    yield db
    
    # Отключаемся от БД
    event_loop.run_until_complete(db.disconnect())


@pytest.fixture
def seller_repository():
    """Фикстура для репозитория продавцов"""
    return SellerRepository()


@pytest.fixture
def ad_repository():
    """Фикстура для репозитория объявлений"""
    return AdRepository()
