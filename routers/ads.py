from fastapi import APIRouter, Request, HTTPException
from models.ads import AdRequest, PredictResponse
from model import prepare_features
import logging
import numpy as np

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/predict", response_model=PredictResponse)
async def predict(ad_data: AdRequest, request: Request) -> PredictResponse:
    """
    Предсказать наличие нарушения в объявлении с использованием ML-модели.

    Args:
        ad_data: Данные объявления
        request: FastAPI Request для доступа к app.state

    Returns:
        PredictResponse: Результат предсказания с вероятностью

    Raises:
        HTTPException 503: Модель не загружена
        HTTPException 500: Ошибка при предсказании
    """
    
    # Логирование входящего запроса
    logger.info(
        f"Запрос на предсказание: seller_id={ad_data.seller_id}, "
        f"item_id={ad_data.item_id}, is_verified={ad_data.is_verified_seller}, "
        f"images_qty={ad_data.images_qty}, category={ad_data.category}, "
        f"description_len={len(ad_data.description)}"
    )
    
    # Проверка доступности модели
    if not hasattr(request.app.state, 'model') or request.app.state.model is None:
        logger.error("ML-модель не загружена")
        raise HTTPException(
            status_code=503,
            detail="ML-модель недоступна. Сервис временно не может обрабатывать запросы."
        )
    
    try:
        # Подготовка признаков для модели
        features = prepare_features(
            is_verified_seller=ad_data.is_verified_seller,
            images_qty=ad_data.images_qty,
            description=ad_data.description,
            category=ad_data.category
        )
        
        logger.debug(f"Подготовленные признаки: {features}")
        
        # Получение предсказания модели
        model = request.app.state.model
        prediction = model.predict(features)[0]  # 0 или 1
        probability = model.predict_proba(features)[0][1]  # Вероятность класса 1 (нарушение)
        
        is_violation = bool(prediction)
        
        # Логирование результата
        logger.info(
            f"Результат предсказания для seller_id={ad_data.seller_id}, "
            f"item_id={ad_data.item_id}: is_violation={is_violation}, "
            f"probability={probability:.4f}"
        )
        
        return PredictResponse(
            is_violation=is_violation,
            probability=float(probability)
        )
        
    except Exception as e:
        logger.error(f"Ошибка при предсказании: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Внутренняя ошибка сервера при обработке предсказания: {str(e)}"
        )