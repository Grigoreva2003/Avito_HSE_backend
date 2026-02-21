from typing import Any
import pytest
from fastapi.testclient import TestClient
from main import app
from http import HTTPStatus
from unittest.mock import MagicMock, patch, AsyncMock
from ml import get_model_manager
import numpy as np
from services.exceptions import AdNotFoundError


class TestSuccessfulPredictionViolation:
    """Тест успешного предсказания (is_violation = True)"""

    def test_predict_violation_true(self, app_client: TestClient, make_payload):
        """
        Тест предсказания с нарушением.
        Мокаем ModelManager для гарантированного получения is_violation=True
        """
        # Мокаем метод predict у ModelManager
        with patch.object(
            get_model_manager(),
            'predict',
            return_value=(True, 0.8)  # is_violation=True, probability=0.8
        ):
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
            assert data["probability"] == 0.8
            assert isinstance(data["probability"], float)
            assert 0.0 <= data["probability"] <= 1.0


class TestSuccessfulPredictionNoViolation:
    """Тест успешного предсказания (is_violation = False)"""

    def test_predict_violation_false(self, app_client: TestClient, make_payload):
        """
        Тест предсказания без нарушения.
        Мокаем ModelManager для гарантированного получения is_violation=False
        """
        # Мокаем метод predict у ModelManager
        with patch.object(
            get_model_manager(),
            'predict',
            return_value=(False, 0.1)  # is_violation=False, probability=0.1
        ):
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
            assert data["probability"] == 0.1
            assert isinstance(data["probability"], float)
            assert 0.0 <= data["probability"] <= 1.0


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
        make_payload,
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
        make_payload,
        missing_field: str,
    ):
        """
        Тест валидации: проверяет, что API возвращает 422 при отсутствии обязательного поля
        """
        data = make_payload()
        data.pop(missing_field)

        response = app_client.post("/predict", json=data)
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_negative_images_qty(self, app_client: TestClient, make_payload):
        """Тест валидации: отрицательное количество изображений"""
        response = app_client.post(
            "/predict",
            json=make_payload({"images_qty": -1}),
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_empty_name(self, app_client: TestClient, make_payload):
        """Тест валидации: пустое название"""
        response = app_client.post(
            "/predict",
            json=make_payload({"name": ""}),
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_empty_description(self, app_client: TestClient, make_payload):
        """Тест валидации: пустое описание"""
        response = app_client.post(
            "/predict",
            json=make_payload({"description": ""}),
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


class TestModelUnavailable:
    """Тест обработки ошибки при недоступной модели"""

    def test_model_not_loaded_returns_503(self, app_client: TestClient, make_payload):
        """
        Тест обработки ошибки: проверяет, что API возвращает 503 Service Unavailable,
        когда модель недоступна
        """
        # Мокаем is_available чтобы вернуть False (модель недоступна)
        with patch.object(
            get_model_manager(),
            'is_available',
            return_value=False
        ):
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

    def test_model_prediction_error_returns_500(self, app_client: TestClient, make_payload):
        """
        Тест обработки ошибки: проверяет, что API возвращает 500 Internal Server Error,
        когда модель выбрасывает исключение при предсказании
        """
        # Мокаем predict чтобы выбросить исключение
        with patch.object(
            get_model_manager(),
            'predict',
            side_effect=Exception("Ошибка модели")
        ):
            response = app_client.post(
                "/predict",
                json=make_payload(),
            )

            # Должен вернуться статус 500
            assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR

            # Проверяем, что есть сообщение об ошибке
            data = response.json()
            assert "detail" in data


class TestModelIntegration:
    """Дополнительные интеграционные тесты для проверки работы модели"""

    def test_model_returns_valid_response_structure(self, app_client: TestClient, make_payload):
        """Проверка, что ответ модели имеет правильную структуру"""
        with patch.object(
            get_model_manager(),
            'predict',
            return_value=(False, 0.3)  # is_violation=False, probability=0.3
        ):
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

    def test_probability_matches_prediction(self, app_client: TestClient, make_payload):
        """Проверка, что вероятность соответствует предсказанию"""
        # Высокая вероятность нарушения
        with patch.object(
            get_model_manager(),
            'predict',
            return_value=(True, 0.9)  # is_violation=True, probability=0.9
        ):
            response = app_client.post(
                "/predict",
                json=make_payload(),
            )

            data = response.json()
            assert data["is_violation"] is True
            assert data["probability"] == 0.9


class TestSimplePredictViolation:
    """Тесты для /simple_predict с положительным результатом"""

    def test_simple_predict_violation_true(self, app_client: TestClient):
        """
        Тест /simple_predict с нарушением (is_violation=True).
        Мокаем получение объявления из БД и предсказание модели.
        """
        # Мокаем репозиторий для возврата объявления
        from repositories.ads import Ad
        mock_ad = Ad(
            id=100,
            seller_id=1,
            name="Test Ad",
            description="Short description",
            category=1,
            images_qty=0,
            seller_is_verified=False
        )
        
        with patch('repositories.AdRepository.get_by_id', return_value=mock_ad):
            # Мокаем предсказание модели
            with patch.object(
                get_model_manager(),
                'predict',
                return_value=(True, 0.85)
            ):
                response = app_client.post(
                    "/simple_predict",
                    json={"item_id": 100}
                )
                
                assert response.status_code == HTTPStatus.OK
                data = response.json()
                
                assert "is_violation" in data
                assert "probability" in data
                assert data["is_violation"] is True
                assert data["probability"] == 0.85


class TestSimplePredictNoViolation:
    """Тесты для /simple_predict с отрицательным результатом"""

    def test_simple_predict_violation_false(self, app_client: TestClient):
        """
        Тест /simple_predict без нарушения (is_violation=False).
        Мокаем получение объявления из БД и предсказание модели.
        """
        from repositories.ads import Ad
        mock_ad = Ad(
            id=101,
            seller_id=2,
            name="Quality Product",
            description="Detailed description with many details",
            category=5,
            images_qty=10,
            seller_is_verified=True
        )
        
        with patch('repositories.AdRepository.get_by_id', return_value=mock_ad):
            with patch.object(
                get_model_manager(),
                'predict',
                return_value=(False, 0.15)
            ):
                response = app_client.post(
                    "/simple_predict",
                    json={"item_id": 101}
                )
                
                assert response.status_code == HTTPStatus.OK
                data = response.json()
                
                assert data["is_violation"] is False
                assert data["probability"] == 0.15
                assert isinstance(data["probability"], float)
                assert 0.0 <= data["probability"] <= 1.0


class TestSimplePredictNotFound:
    """Тесты для /simple_predict когда объявление не найдено"""

    def test_simple_predict_ad_not_found(self, app_client: TestClient):
        """
        Тест /simple_predict когда объявление не существует в БД.
        Должен вернуть 404.
        """
        # Мокаем репозиторий для возврата None (объявление не найдено)
        with patch('repositories.AdRepository.get_by_id', return_value=None):
            response = app_client.post(
                "/simple_predict",
                json={"item_id": 99999}
            )
            
            assert response.status_code == HTTPStatus.NOT_FOUND
            data = response.json()
            assert "detail" in data
            assert "99999" in data["detail"]


class TestSimplePredictValidation:
    """Тесты валидации для /simple_predict"""

    def test_simple_predict_invalid_item_id_type(self, app_client: TestClient):
        """Тест: неверный тип item_id"""
        response = app_client.post(
            "/simple_predict",
            json={"item_id": "not_a_number"}
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_simple_predict_negative_item_id(self, app_client: TestClient):
        """Тест: отрицательный item_id"""
        response = app_client.post(
            "/simple_predict",
            json={"item_id": -1}
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_simple_predict_zero_item_id(self, app_client: TestClient):
        """Тест: нулевой item_id"""
        response = app_client.post(
            "/simple_predict",
            json={"item_id": 0}
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_simple_predict_missing_item_id(self, app_client: TestClient):
        """Тест: отсутствует item_id"""
        response = app_client.post(
            "/simple_predict",
            json={}
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY




class TestCloseAdEndpoint:
    """Тесты для /close."""

    def test_close_ad_success(self, app_client: TestClient):
        with patch("routers.ads.ModerationService.close_ad", new_callable=AsyncMock) as mock_close:
            response = app_client.post("/close", json={"item_id": 100})

            assert response.status_code == HTTPStatus.OK
            assert response.json() == {
                "item_id": 100,
                "status": "closed",
                "message": "Ad successfully closed",
            }
            mock_close.assert_awaited_once_with(100)

    def test_close_ad_not_found(self, app_client: TestClient):
        with patch("routers.ads.ModerationService.close_ad", new_callable=AsyncMock) as mock_close:
            mock_close.side_effect = AdNotFoundError("Объявление с ID 99999 не найдено")
            response = app_client.post("/close", json={"item_id": 99999})

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_close_ad_validation_error(self, app_client: TestClient):
        response = app_client.post("/close", json={"item_id": 0})
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
