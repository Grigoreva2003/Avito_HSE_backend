from pydantic import BaseModel, Field, field_validator


class AdRequest(BaseModel):
    """Модель запроса для предсказания нарушений в объявлении."""
    seller_id: int
    is_verified_seller: bool
    item_id: int
    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    category: int
    images_qty: int = Field(..., ge=0)

    @field_validator('name', 'description')
    @classmethod
    def check_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Поле не может быть пустым')
        return v


class PredictRequest(BaseModel):
    """Модель запроса для simple_predict (только item_id)."""
    item_id: int = Field(..., gt=0, description="ID объявления")


class AsyncPredictResponse(BaseModel):
    """Модель ответа для async_predict."""
    task_id: int = Field(..., description="ID задачи модерации")
    status: str = Field(..., description="Статус модерации (pending, completed, failed)")
    message: str = Field(..., description="Сообщение о статусе")


class ModerationResultResponse(BaseModel):
    """Модель ответа для получения результата модерации."""
    task_id: int = Field(..., description="ID задачи модерации")
    status: str = Field(..., description="Статус модерации (pending, completed, failed)")
    is_violation: bool | None = Field(None, description="Результат модерации (NULL если не обработано)")
    probability: float | None = Field(None, ge=0.0, le=1.0, description="Вероятность нарушения")
    error_message: str | None = Field(None, description="Сообщение об ошибке (если failed)")


class PredictResponse(BaseModel):
    """Модель ответа с предсказанием модели."""
    is_violation: bool = Field(..., description="Есть ли нарушение в объявлении")
    probability: float = Field(..., ge=0.0, le=1.0, description="Вероятность нарушения (от 0 до 1)")