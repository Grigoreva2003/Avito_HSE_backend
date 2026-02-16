from fastapi import APIRouter, HTTPException
import logging
from models.ads import (
    AdRequest,
    PredictRequest,
    PredictResponse,
    AsyncPredictResponse,
    ModerationResultResponse
)
from services.moderation import ModerationService
from services.async_moderation import AsyncModerationService
from services.exceptions import ModelNotAvailableError, PredictionError, AdNotFoundError, ModerationResultNotFoundError

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


@router.post("/async_predict", response_model=AsyncPredictResponse)
async def async_predict(request: PredictRequest) -> AsyncPredictResponse:
    """
    Отправить запрос на асинхронную модерацию объявления.

    Объявление отправляется в очередь Kafka для обработки воркером.
    Результат можно получить позже по task_id.

    Args:
        request: Запрос с item_id объявления

    Returns:
        AsyncPredictResponse: task_id и статус

    Raises:
        HTTPException 404: Объявление не найдено
        HTTPException 422: Невалидный item_id (автоматически Pydantic)
        HTTPException 500: Внутренняя ошибка сервера
    """
    async_service = AsyncModerationService()

    try:
        task_id = await async_service.submit_moderation_request(request.item_id)

        return AsyncPredictResponse(
            task_id=task_id,
            status="pending",
            message="Moderation request accepted"
        )

    except AdNotFoundError as e:
        logger.warning(f"Объявление не найдено: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"Объявление с ID {request.item_id} не найдено."
        )
    except Exception as e:
        logger.error(f"Неожиданная ошибка при async_predict: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера при отправке задачи на модерацию."
        )


@router.post("/simple_predict", response_model=PredictResponse)
async def simple_predict(request: PredictRequest) -> PredictResponse:
    """
    Предсказать наличие нарушения в объявлении по item_id.
    Данные объявления получаются из БД.

    Args:
        request: Запрос с item_id

    Returns:
        PredictResponse: Результат предсказания (is_violation, probability)

    Raises:
        HTTPException 404: Объявление не найдено
        HTTPException 503: ML-модель недоступна
        HTTPException 500: Внутренняя ошибка сервера
    """
    moderation_service = ModerationService()

    try:
        return await moderation_service.predict_violation_by_item_id(request.item_id)
    except AdNotFoundError as e:
        logger.warning(f"Объявление не найдено: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"Объявление с ID {request.item_id} не найдено"
        )
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


@router.get("/moderation_result/{task_id}", response_model=ModerationResultResponse)
async def moderation_result(task_id: int) -> ModerationResultResponse:
    """
    Получить результат асинхронной модерации по task_id.
    
    Позволяет проверить статус модерации (polling).
    
    Args:
        task_id: ID задачи модерации
        
    Returns:
        ModerationResultResponse: Результат модерации со статусом
        
    Raises:
        HTTPException 404: Задача модерации не найдена
        HTTPException 500: Внутренняя ошибка сервера
    """
    async_service = AsyncModerationService()

    try:
        return await async_service.get_moderation_result(task_id)
    except ModerationResultNotFoundError as e:
        logger.warning(f"Задача модерации не найдена: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"Задача модерации с ID {task_id} не найдена."
        )
    except Exception as e:
        logger.error(f"Неожиданная ошибка при moderation_result/{task_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера при получении результата модерации."
        )
