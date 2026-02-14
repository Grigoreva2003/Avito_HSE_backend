import pytest
from fastapi.testclient import TestClient
from main import app
from ml import get_model_manager


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
