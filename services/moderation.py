import logging
from models.ads import AdRequest, PredictResponse
from services.exceptions import ModelNotAvailableError, PredictionError
from ml import get_model_manager

logger = logging.getLogger(__name__)


class ModerationService:
    """
    Сервис для модерации объявлений с использованием ML-модели.
    
    Не знает о деталях работы с моделью - все инкапсулировано в ModelManager.
    """
    
    def __init__(self):
        """Инициализация сервиса модерации"""
        self._model_manager = get_model_manager()
    
    def predict_violation(self, ad_data: AdRequest) -> PredictResponse:
        """
        Предсказание нарушения в объявлении.
        
        Args:
            ad_data: Данные объявления
            
        Returns:
            PredictResponse: Результат предсказания с вероятностью
            
        Raises:
            ModelNotAvailableError: Модель недоступна
            PredictionError: Ошибка при предсказании
        """
        # Логирование входящего запроса
        logger.info(
            f"Запрос на предсказание: seller_id={ad_data.seller_id}, "
            f"item_id={ad_data.item_id}, is_verified={ad_data.is_verified_seller}, "
            f"images_qty={ad_data.images_qty}, category={ad_data.category}, "
            f"description_len={len(ad_data.description)}"
        )
        
        # Проверка доступности модели
        if not self._model_manager.is_available():
            logger.error("ML-модель не загружена")
            raise ModelNotAvailableError("ML-модель недоступна")
        
        try:
            # Предсказание через ModelManager (он сам нормализует признаки)
            is_violation, probability = self._model_manager.predict(
                is_verified_seller=ad_data.is_verified_seller,
                images_qty=ad_data.images_qty,
                description=ad_data.description,
                category=ad_data.category
            )
            
            # Логирование результата
            logger.info(
                f"Результат предсказания для seller_id={ad_data.seller_id}, "
                f"item_id={ad_data.item_id}: is_violation={is_violation}, "
                f"probability={probability:.4f}"
            )
            
            return PredictResponse(
                is_violation=is_violation,
                probability=probability
            )
            
        except RuntimeError as e:
            # ModelManager выбрасывает RuntimeError если модель недоступна
            logger.error(f"Модель недоступна: {e}")
            raise ModelNotAvailableError(str(e)) from e
        except Exception as e:
            logger.error(f"Ошибка при предсказании: {e}", exc_info=True)
            raise PredictionError(f"Ошибка при обработке предсказания: {str(e)}") from e
