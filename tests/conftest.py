import pytest
from fastapi.testclient import TestClient
from main import app
from ml import get_model_manager
from repositories import SellerRepository, AdRepository
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def app_client() -> TestClient:
    """Фикстура для тестового клиента без реальных подключений к хранилищам."""
    # Убеждаемся, что ModelManager инициализирован
    model_manager = get_model_manager()
    if not model_manager.is_available():
        model_manager.load_model("model.pkl")

    mock_db = MagicMock()
    mock_db.connect = AsyncMock()
    mock_db.disconnect = AsyncMock()

    mock_kafka = MagicMock()
    mock_kafka.start = AsyncMock()
    mock_kafka.stop = AsyncMock()
    mock_kafka.is_started.return_value = True
    mock_kafka.send_moderation_request = AsyncMock()

    mock_redis = MagicMock()
    mock_redis.start = AsyncMock()
    mock_redis.stop = AsyncMock()
    mock_redis.is_started.return_value = True
    mock_redis.get_client.return_value = MagicMock()

    with patch("main.get_database", return_value=mock_db), \
         patch("main.get_kafka_producer", return_value=mock_kafka), \
         patch("main.get_redis_client", return_value=mock_redis), \
         patch("app.clients.get_kafka_producer", return_value=mock_kafka), \
         patch("services.async_moderation.get_kafka_producer", return_value=mock_kafka):
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
