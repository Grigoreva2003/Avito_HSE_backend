import pytest
from fastapi.testclient import TestClient
from main import app
from ml import get_model_manager
from repositories import SellerRepository, AdRepository


@pytest.fixture
def app_client() -> TestClient:
    """Фикстура для тестового клиента"""
    # Убеждаемся, что ModelManager инициализирован
    model_manager = get_model_manager()
    if not model_manager.is_available():
        model_manager.load_model("model.pkl")
    
    # Мокируем Kafka Producer для тестов
    from unittest.mock import AsyncMock, patch
    with patch('app.clients.kafka.get_kafka_producer') as mock_get_producer:
        mock_producer = AsyncMock()
        mock_producer.is_started = lambda: True
        mock_producer.send_moderation_request = AsyncMock()
        mock_get_producer.return_value = mock_producer

        with TestClient(app) as client:
            yield client


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


@pytest.fixture
def seller_repository():
    """Фикстура для репозитория продавцов"""
    return SellerRepository()


@pytest.fixture
def ad_repository():
    """Фикстура для репозитория объявлений"""
    return AdRepository()
