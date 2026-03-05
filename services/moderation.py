import logging
from models.ads import AdRequest, PredictResponse
from services.exceptions import ModelNotAvailableError, PredictionError, AdNotFoundError
from ml import get_model_manager
from repositories import AdRepository, ModerationResultRepository
from repositories.prediction_cache import PredictionCacheStorage
from app.metrics import (
    observe_prediction_duration,
    record_prediction_result,
    record_prediction_error,
)

logger = logging.getLogger(__name__)


class ModerationService:
    """
    Сервис для модерации объявлений с использованием ML-модели.
    
    Не знает о деталях работы с моделью - все инкапсулировано в ModelManager.
    """
    
    def __init__(self):
        """Инициализация сервиса модерации"""
        self._model_manager = get_model_manager()
        self._ad_repository = AdRepository()
        self._moderation_repository = ModerationResultRepository()
        self._prediction_cache = PredictionCacheStorage()

    def _ensure_model_available(self) -> None:
        """Проверка доступности модели перед инференсом."""
        if not self._model_manager.is_available():
            logger.error("ML-модель не загружена")
            raise ModelNotAvailableError("ML-модель недоступна")

    def _predict_with_metrics(
        self,
        *,
        is_verified_seller: bool,
        images_qty: int,
        description: str,
        category: int,
    ) -> tuple[bool, float]:
        """Выполнить инференс модели с инкрементом бизнес-метрик."""
        with observe_prediction_duration():
            is_violation, probability = self._model_manager.predict(
                is_verified_seller=is_verified_seller,
                images_qty=images_qty,
                description=description,
                category=category,
            )
        record_prediction_result(is_violation, probability)
        return is_violation, probability
    
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
        
        self._ensure_model_available()
        
        try:
            is_violation, probability = self._predict_with_metrics(
                is_verified_seller=ad_data.is_verified_seller,
                images_qty=ad_data.images_qty,
                description=ad_data.description,
                category=ad_data.category,
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
            record_prediction_error("model_unavailable")
            logger.error(f"Модель недоступна: {e}")
            raise ModelNotAvailableError(str(e)) from e
        except Exception as e:
            record_prediction_error("prediction_error")
            logger.error(f"Ошибка при предсказании: {e}", exc_info=True)
            raise PredictionError(f"Ошибка при обработке предсказания: {str(e)}") from e
    
    async def predict_violation_by_item_id(self, item_id: int) -> PredictResponse:
        """
        Предсказание нарушения в объявлении по item_id.
        Получает данные объявления из БД.
        
        Args:
            item_id: ID объявления
            
        Returns:
            PredictResponse: Результат предсказания
            
        Raises:
            AdNotFoundError: Если объявление не найдено
            ModelNotAvailableError: Если модель недоступна
            PredictionError: При ошибке предсказания
        """
        logger.info(f"Запрос на предсказание по item_id={item_id}")

        cached_prediction = await self._prediction_cache.get(item_id)
        if cached_prediction is not None:
            logger.info(f"Возвращаем результат из кэша для item_id={item_id}")
            return cached_prediction
        
        # Получаем объявление из БД со связанными данными продавца
        ad = await self._ad_repository.get_by_id(item_id, include_seller=True)
        
        if ad is None:
            logger.warning(f"Объявление не найдено: item_id={item_id}")
            raise AdNotFoundError(f"Объявление с ID {item_id} не найдено")
        
        logger.info(
            f"Получены данные объявления: item_id={item_id}, "
            f"seller_id={ad.seller_id}, is_verified={ad.seller_is_verified}, "
            f"images_qty={ad.images_qty}, category={ad.category}"
        )
        
        self._ensure_model_available()
        
        try:
            is_violation, probability = self._predict_with_metrics(
                is_verified_seller=ad.seller_is_verified,
                images_qty=ad.images_qty,
                description=ad.description,
                category=ad.category,
            )
            
            logger.info(
                f"Результат предсказания для item_id={item_id}: "
                f"is_violation={is_violation}, probability={probability:.4f}"
            )
            
            response = PredictResponse(
                is_violation=is_violation,
                probability=probability
            )
            await self._prediction_cache.set(item_id, response)
            return response
        
        except RuntimeError as e:
            record_prediction_error("model_unavailable")
            logger.error(f"Модель недоступна: {e}")
            raise ModelNotAvailableError(str(e)) from e
        except Exception as e:
            record_prediction_error("prediction_error")
            logger.error(f"Ошибка при предсказании для item_id={item_id}: {e}", exc_info=True)
            raise PredictionError(f"Ошибка при обработке предсказания: {str(e)}") from e

    async def close_ad(self, item_id: int) -> None:
        """
        Закрыть объявление: пометить объявление как закрытое и удалить связанные результаты модерации.
        Также очистить кэш Redis для sync/async предсказаний.
        """
        ad = await self._ad_repository.get_by_id(item_id, include_seller=False)
        if ad is None:
            raise AdNotFoundError(f"Объявление с ID {item_id} не найдено")

        task_ids = await self._moderation_repository.get_task_ids_by_item_id(item_id)
        await self._moderation_repository.delete_by_item_id(item_id)
        closed = await self._ad_repository.close(item_id)
        if not closed:
            raise AdNotFoundError(f"Объявление с ID {item_id} не найдено")

        await self._prediction_cache.delete(item_id)
        for task_id in task_ids:
            await self._prediction_cache.delete_moderation_result(task_id)