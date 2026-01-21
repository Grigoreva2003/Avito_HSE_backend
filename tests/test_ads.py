from typing import Any
import pytest
from fastapi.testclient import TestClient
from main import app
from http import HTTPStatus


@pytest.fixture
def app_client() -> TestClient:
    return TestClient(app)


def make_payload(overrides: dict | None = None) -> dict:
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


class TestPredictPositive:
    """Нарушений НЕТ"""

    @pytest.mark.parametrize(
        "overrides",
        [
            {"is_verified_seller": True, "images_qty": 0},
            {"is_verified_seller": True, "images_qty": 10},
            {"is_verified_seller": False, "images_qty": 1},
            {"is_verified_seller": False, "images_qty": 5},
        ],
    )
    def test_no_violations(self, app_client: TestClient, overrides: dict):
        response = app_client.post(
            "/predict",
            json=make_payload(overrides),
        )

        assert response.status_code == HTTPStatus.OK
        assert response.json() is False


class TestPredictNegative:
    """Есть нарушения"""

    def test_has_violations(self, app_client: TestClient):
        response = app_client.post(
            "/predict",
            json=make_payload(
                {"is_verified_seller": False, "images_qty": 0}
            ),
        )

        assert response.status_code == HTTPStatus.OK
        assert response.json() is True


class TestValidation:
    """Валидация входных данных"""

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
        data = make_payload()
        data.pop(missing_field)

        response = app_client.post("/predict", json=data)
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize(
        "field,value",
        [
            ("seller_id", "не число"),
            ("is_verified_seller", "да"),
            ("item_id", "сто"),
            ("category", "электроника"),
            ("images_qty", "три"),
        ],
    )
    def test_invalid_types(
        self,
        app_client: TestClient,
        field: str,
        value: Any,
    ):
        response = app_client.post(
            "/predict",
            json=make_payload({field: value}),
        )

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


class TestBusinessLogic:
    """Бизнес-логика"""

    @pytest.mark.parametrize("images_qty", [0, 10, 100])
    def test_verified_seller_always_no_violations(
        self,
        app_client: TestClient,
        images_qty: int,
    ):
        response = app_client.post(
            "/predict",
            json=make_payload(
                {"is_verified_seller": True, "images_qty": images_qty}
            ),
        )

        assert response.status_code == HTTPStatus.OK
        assert response.json() is False

    def test_unverified_seller_with_images_no_violations(
        self,
        app_client: TestClient,
    ):
        response = app_client.post(
            "/predict",
            json=make_payload(
                {"is_verified_seller": False, "images_qty": 1}
            ),
        )

        assert response.status_code == HTTPStatus.OK
        assert response.json() is False

    def test_unverified_seller_no_images_has_violations(
        self,
        app_client: TestClient,
    ):
        response = app_client.post(
            "/predict",
            json=make_payload(
                {"is_verified_seller": False, "images_qty": 0}
            ),
        )

        assert response.status_code == HTTPStatus.OK
        assert response.json() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])