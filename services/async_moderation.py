import logging
from repositories.ads import AdRepository
from repositories.moderation_results import ModerationResultRepository
from app.clients import get_kafka_producer
from services.exceptions import AdNotFoundError

logger = logging.getLogger(__name__)


class AsyncModerationService:
    """Сервис для асинхронной модерации объявлений через Kafka"""
    
    def __init__(self):
        self._ad_repository = AdRepository()
        self._moderation_repository = ModerationResultRepository()
        self._kafka_producer = get_kafka_producer()
    
    async def submit_moderation_request(self, item_id: int) -> int:
        """
        Отправить запрос на асинхронную модерацию.
        
        Args:
            item_id: ID объявления
            
        Returns:
            int: task_id для отслеживания статуса
            
        Raises:
            AdNotFoundError: Если объявление не найдено
            Exception: Ошибки при отправке в Kafka
        """
        logger.info(f"Запрос на асинхронную модерацию: item_id={item_id}")
        
        # 1. Проверяем что объявление существует
        ad = await self._ad_repository.get_by_id(item_id, include_seller=False)
        if ad is None:
            logger.warning(f"Объявление не найдено: item_id={item_id}")
            raise AdNotFoundError(f"Объявление с ID {item_id} не найдено")
        
        logger.info(f"Объявление найдено: item_id={item_id}, name={ad.name}")
        
        # 2. Создаём запись в moderation_results со статусом pending
        moderation_result = await self._moderation_repository.create(
            item_id=item_id,
            status="pending"
        )
        
        task_id = moderation_result.id
        logger.info(f"Создана задача модерации: task_id={task_id}, item_id={item_id}")
        
        # 3. Отправляем сообщение в Kafka
        try:
            await self._kafka_producer.send_moderation_request(item_id)
            logger.info(f"Сообщение отправлено в Kafka: task_id={task_id}, item_id={item_id}")
        except Exception as e:
            logger.error(f"Ошибка при отправке в Kafka: {e}")
            # Обновляем статус на failed
            await self._moderation_repository.update_failed(
                task_id=task_id,
                error_message=f"Ошибка отправки в Kafka: {str(e)}"
            )
            raise
        
        return task_id
