import json
import logging
from datetime import datetime, timezone
from typing import Optional
from aiokafka import AIOKafkaProducer
from config import get_settings

logger = logging.getLogger(__name__)


class KafkaProducer:
    """
    Синглтон для работы с Kafka Producer.
    Отправляет сообщения в топики Kafka.
    """
    
    _instance: Optional['KafkaProducer'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._producer: Optional[AIOKafkaProducer] = None
        self._settings = get_settings().kafka
        logger.info("KafkaProducer singleton инициализирован")
    
    async def start(self):
        """Запуск Kafka Producer"""
        if self._producer is not None:
            logger.warning("KafkaProducer уже запущен")
            return
        
        try:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self._settings.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                request_timeout_ms=self._settings.producer_timeout * 1000,
            )
            await self._producer.start()
            logger.info(f"KafkaProducer подключен к {self._settings.bootstrap_servers}")
        except Exception as e:
            logger.error(f"Ошибка при запуске KafkaProducer: {e}")
            raise
    
    async def stop(self):
        """Остановка Kafka Producer"""
        if self._producer is None:
            return
        
        try:
            await self._producer.stop()
            logger.info("KafkaProducer остановлен")
            self._producer = None
        except Exception as e:
            logger.error(f"Ошибка при остановке KafkaProducer: {e}")
            raise
    
    async def send_moderation_request(self, item_id: int, task_id: int) -> None:
        """
        Отправить запрос на модерацию в Kafka.
        
        Args:
            item_id: ID объявления для модерации
            task_id: ID задачи модерации
            
        Raises:
            RuntimeError: Если producer не запущен
            Exception: Ошибки отправки в Kafka
        """
        if self._producer is None:
            raise RuntimeError("KafkaProducer не запущен. Вызовите start() сначала.")
        
        message = {
            "item_id": item_id,
            "task_id": task_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            logger.info(f"Отправка сообщения в Kafka: task_id={task_id}, item_id={item_id}")
            
            # Отправляем сообщение в топик
            await self._producer.send_and_wait(
                self._settings.topic_moderation,
                value=message
            )
            
            logger.info(
                f"Сообщение успешно отправлено в топик {self._settings.topic_moderation}: "
                f"task_id={task_id}, item_id={item_id}"
            )
            
        except Exception as e:
            logger.error(
                f"Ошибка при отправке сообщения в Kafka для task_id={task_id}, item_id={item_id}: {e}"
            )
            raise
    
    def is_started(self) -> bool:
        """Проверка, запущен ли producer"""
        return self._producer is not None


_kafka_producer_instance: Optional[KafkaProducer] = None


def get_kafka_producer() -> KafkaProducer:
    """
    Получить синглтон экземпляр KafkaProducer.
    
    Returns:
        KafkaProducer: Экземпляр Kafka Producer
    """
    global _kafka_producer_instance
    if _kafka_producer_instance is None:
        _kafka_producer_instance = KafkaProducer()
    return _kafka_producer_instance
