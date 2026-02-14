from fastapi import APIRouter, HTTPException
import logging
from models.ads import AdRequest, PredictResponse
from services.moderation import ModerationService
from services.exceptions import ModelNotAvailableError, PredictionError

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/predict", response_model=PredictResponse)
async def predict(ad_data: AdRequest) -> PredictResponse:
    """
    Предсказать наличие нарушения в объявлении с использованием ML-модели.

    Args:
        ad_data: Данные объявления (автоматически валидируется Pydantic)

    Returns:
        PredictResponse: Результат предсказания с вероятностью

    Raises:
        HTTPException 503: Модель не загружена
        HTTPException 422: Невалидные данные (автоматически Pydantic)
        HTTPException 500: Ошибка при предсказании
    """
    moderation_service = ModerationService()
    
    try:
        return moderation_service.predict_violation(ad_data)
    except ModelNotAvailableError as e:
        logger.error(f"Модель недоступна: {e}")
        raise HTTPException(
            status_code=503,
            detail="ML-модель недоступна. Сервис временно не может обрабатывать запросы."
        )
    except PredictionError as e:
        logger.error(f"Ошибка предсказания: {e}")
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера при обработке предсказания."
        )
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера."
        )