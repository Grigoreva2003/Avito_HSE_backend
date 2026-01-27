from typing import Any
import pytest
from fastapi.testclient import TestClient
from main import app
from http import HTTPStatus
from unittest.mock import MagicMock
import numpy as np
from model import train_model


@pytest.fixture
def app_client() -> TestClient:
    """Фикстура для тестового клиента"""
    # Убеждаемся, что модель загружена перед запуском тестов
    if not hasattr(app.state, 'model') or app.state.model is None:
        app.state.model = train_model()
    return TestClient(app)


def make_payload(overrides: dict | None = None) -> dict:
    """Создает тестовый payload с возможностью переопределения полей"""
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


class TestSuccessfulPredictionViolation:
    """Тест успешного предсказания (is_violation = True)"""

    def test_predict_violation_true(self, app_client: TestClient):
        """
        Тест предсказания с нарушением.
        Используем мок для гарантированного получения is_violation=True
        """
        # Создаем мок модели, которая возвращает нарушение
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([1])  # 1 = нарушение
        mock_model.predict_proba.return_value = np.array([[0.2, 0.8]])  # 80% вероятность нарушения

        # Сохраняем оригинальную модель
        original_model = app.state.model
        try:
            # Подменяем модель на мок
            app.state.model = mock_model

            response = app_client.post(
                "/predict",
                json=make_payload({
                    "is_verified_seller": False,
                    "images_qty": 0,
                    "description": "Краткое описание"
                }),
            )

            assert response.status_code == HTTPStatus.OK
            data = response.json()

            # Проверяем структуру ответа
            assert "is_violation" in data
            assert "probability" in data

            # Проверяем, что модель предсказала нарушение
            assert data["is_violation"] is True
            assert isinstance(data["probability"], float)
            assert 0.0 <= data["probability"] <= 1.0

            # Проверяем, что модель была вызвана
            assert mock_model.predict.called
            assert mock_model.predict_proba.called
        finally:
            # Восстанавливаем оригинальную модель
            app.state.model = original_model


class TestSuccessfulPredictionNoViolation:
    """Тест успешного предсказания (is_violation = False)"""

    def test_predict_violation_false(self, app_client: TestClient):
        """
        Тест предсказания без нарушения.
        Используем мок для гарантированного получения is_violation=False
        """
        # Создаем мок модели, которая возвращает отсутствие нарушения
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0])  # 0 = нет нарушения
        mock_model.predict_proba.return_value = np.array([[0.9, 0.1]])  # 10% вероятность нарушения

        original_model = app.state.model
        try:
            app.state.model = mock_model

            response = app_client.post(
                "/predict",
                json=make_payload({
                    "is_verified_seller": True,
                    "images_qty": 5,
                    "description": "Подробное описание товара с множеством деталей"
                }),
            )

            assert response.status_code == HTTPStatus.OK
            data = response.json()

            assert "is_violation" in data
            assert "probability" in data

            assert data["is_violation"] is False
            assert isinstance(data["probability"], float)
            assert 0.0 <= data["probability"] <= 1.0

            assert mock_model.predict.called
            assert mock_model.predict_proba.called
        finally:
            app.state.model = original_model


class TestValidation:
    """Тест валидации входных данных (неверные типы)"""

    @pytest.mark.parametrize(
        "field,value",
        [
            ("seller_id", "не число"),
            ("seller_id", "abc"),
            ("seller_id", None),
            ("is_verified_seller", "да"),
            ("item_id", "сто"),
            ("item_id", 12.5),
            ("item_id", [100]),
            ("category", "электроника"),
            ("category", 1.5),
            ("category", None),
            ("images_qty", "три"),
            ("images_qty", 5.5),
            ("images_qty", [5]),
            ("name", 123),
            ("name", None),
            ("description", 456),
            ("description", None),
        ],
    )
    def test_invalid_types(
        self,
        app_client: TestClient,
        field: str,
        value: Any,
    ):
        """
        Тест валидации: проверяет, что API возвращает 422 при неверных типах данных

        Примечание: Pydantic может конвертировать некоторые значения (например, 1/"true" в bool),
        поэтому мы тестируем только те значения, которые точно не могут быть преобразованы.
        """
        response = app_client.post(
            "/predict",
            json=make_payload({field: value}),
        )

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data

    @pytest.mark.parametrize(
        "missing_field",
        [
            "seller_id",
            "is_verified_seller",
            "item_id",
            "name",
            "description",
            "category",
            "images_qty",
        ],
    )
    def test_missing_required_field(
        self,
        app_client: TestClient,
        missing_field: str,
    ):
        """
        Тест валидации: проверяет, что API возвращает 422 при отсутствии обязательного поля
        """
        data = make_payload()
        data.pop(missing_field)

        response = app_client.post("/predict", json=data)
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_negative_images_qty(self, app_client: TestClient):
        """Тест валидации: отрицательное количество изображений"""
        response = app_client.post(
            "/predict",
            json=make_payload({"images_qty": -1}),
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_empty_name(self, app_client: TestClient):
        """Тест валидации: пустое название"""
        response = app_client.post(
            "/predict",
            json=make_payload({"name": ""}),
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_empty_description(self, app_client: TestClient):
        """Тест валидации: пустое описание"""
        response = app_client.post(
            "/predict",
            json=make_payload({"description": ""}),
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


class TestModelUnavailable:
    """Тест обработки ошибки при недоступной модели"""

    def test_model_not_loaded_returns_503(self, app_client: TestClient):
        """
        Тест обработки ошибки: проверяет, что API возвращает 503 Service Unavailable,
        когда модель недоступна
        """
        original_model = getattr(app.state, 'model', None)

        try:
            # Устанавливаем модель в None, имитируя ее недоступность
            app.state.model = None

            response = app_client.post(
                "/predict",
                json=make_payload(),
            )

            # Должен вернуться статус 503
            assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE

            # Проверяем, что есть понятное сообщение об ошибке
            data = response.json()
            assert "detail" in data
            assert "модель" in data["detail"].lower() or "model" in data["detail"].lower()

        finally:
            if original_model is not None:
                app.state.model = original_model

    def test_model_prediction_error_returns_500(self, app_client: TestClient):
        """
        Тест обработки ошибки: проверяет, что API возвращает 500 Internal Server Error,
        когда модель выбрасывает исключение при предсказании
        """
        # Создаем мок модели, которая выбрасывает исключение
        mock_model = MagicMock()
        mock_model.predict.side_effect = Exception("Ошибка модели")

        original_model = app.state.model
        try:
            app.state.model = mock_model

            response = app_client.post(
                "/predict",
                json=make_payload(),
            )

            # Должен вернуться статус 500
            assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR

            # Проверяем, что есть сообщение об ошибке
            data = response.json()
            assert "detail" in data
        finally:
            app.state.model = original_model


class TestModelIntegration:
    """Дополнительные интеграционные тесты для проверки работы модели"""

    def test_model_returns_valid_response_structure(self, app_client: TestClient):
        """Проверка, что ответ модели имеет правильную структуру"""
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0])
        mock_model.predict_proba.return_value = np.array([[0.7, 0.3]])

        original_model = app.state.model
        try:
            app.state.model = mock_model

            response = app_client.post(
                "/predict",
                json=make_payload(),
            )

            assert response.status_code == HTTPStatus.OK
            data = response.json()

            assert "is_violation" in data
            assert "probability" in data

            # Проверяем типы
            assert isinstance(data["is_violation"], bool)
            assert isinstance(data["probability"], float)

            # Проверяем диапазон вероятности
            assert 0.0 <= data["probability"] <= 1.0
        finally:
            app.state.model = original_model

    def test_probability_matches_prediction(self, app_client: TestClient):
        """Проверка, что вероятность соответствует предсказанию"""
        # Высокая вероятность нарушения
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([1])
        mock_model.predict_proba.return_value = np.array([[0.1, 0.9]])

        original_model = app.state.model
        try:
            app.state.model = mock_model

            response = app_client.post(
                "/predict",
                json=make_payload(),
            )

            data = response.json()
            assert data["is_violation"] is True
            assert data["probability"] == 0.9
        finally:
            app.state.model = original_model


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
