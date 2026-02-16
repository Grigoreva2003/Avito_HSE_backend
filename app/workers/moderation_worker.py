"""
Kafka Consumer для асинхронной обработки модерации объявлений.

Запуск:
    python -m app.workers.moderation_worker
"""

import asyncio
import json
import logging
import signal
from datetime import datetime, timezone
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from config import get_settings
from database import get_database
from ml import get_model_manager
from repositories.ads import AdRepository
from repositories.moderation_results import ModerationResultRepository


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ModerationWorker:
    """
    Воркер для обработки задач модерации из Kafka.
    
    Подписывается на топик 'moderation', получает item_id,
    загружает данные из БД, запускает ML-модель и сохраняет результат.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.consumer = None
        self.dlq_producer = None
        self.running = False
        self.db = get_database()
        self.ad_repository = AdRepository()
        self.moderation_repository = ModerationResultRepository()
        self.model_manager = get_model_manager()
    
    async def start(self):
        """Запуск воркера и инициализация компонентов"""
        logger.info("Запуск модерационного воркера...")
        
        # Подключение к БД
        logger.info("Подключение к БД...")
        await self.db.connect()
        logger.info("Подключение к БД успешно")
        
        # Загрузка ML-модели
        logger.info("Загрузка ML-модели...")
        self.model_manager.load_model(self.settings.ml.model_path)
        logger.info("ML-модель успешно загружена")
        
        # Создание Kafka Consumer
        self.consumer = AIOKafkaConsumer(
            self.settings.kafka.topic_moderation,
            bootstrap_servers=self.settings.kafka.bootstrap_servers,
            group_id=self.settings.kafka.consumer_group_id,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True
        )
        
        # Создание DLQ Producer (для ошибочных сообщений)
        self.dlq_producer = AIOKafkaProducer(
            bootstrap_servers=self.settings.kafka.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        await self.consumer.start()
        await self.dlq_producer.start()
        
        logger.info(
            f"Воркер запущен. Слушаем топик: {self.settings.kafka.topic_moderation}, "
            f"group_id: {self.settings.kafka.consumer_group_id}"
        )
        
        self.running = True
    
    async def stop(self):
        """Остановка воркера"""
        logger.info("Остановка воркера...")
        self.running = False
        
        if self.consumer:
            await self.consumer.stop()
        
        if self.dlq_producer:
            await self.dlq_producer.stop()
        
        await self.db.disconnect()
        self.model_manager.unload()
        
        logger.info("Воркер успешно остановлен")
    
    async def process_message(self, message):
        """
        Обработка одного сообщения из Kafka.
        
        Args:
            message: Сообщение из Kafka с item_id
        """
        try:
            data = message.value
            item_id = data.get('item_id')
            timestamp = data.get('timestamp')
            
            logger.info(f"Получено сообщение: item_id={item_id}, timestamp={timestamp}")
            
            if not item_id:
                logger.error(f"Сообщение не содержит item_id: {data}")
                await self.send_to_dlq(message, "Missing item_id in message")
                return
            
            # 1. Получаем данные объявления из БД
            ad = await self.ad_repository.get_by_id(item_id, include_seller=True)
            
            if ad is None:
                logger.error(f"Объявление не найдено: item_id={item_id}")
                # Можно создать запись об ошибке или просто залогировать
                await self.send_to_dlq(message, f"Ad not found: item_id={item_id}")
                return
            
            logger.info(
                f"Объявление найдено: item_id={item_id}, "
                f"seller_id={ad.seller_id}, is_verified={ad.seller_is_verified}"
            )
            
            # 2. Находим соответствующую задачу модерации
            # (предполагаем что она была создана при отправке в Kafka)
            # Для простоты можно искать по item_id с статусом pending
            
            # 3. Вызываем ML-модель для предсказания
            is_violation, probability = self.model_manager.predict(
                is_verified_seller=ad.seller_is_verified,
                images_qty=ad.images_qty,
                description=ad.description,
                category=ad.category
            )
            
            logger.info(
                f"Предсказание выполнено: item_id={item_id}, "
                f"is_violation={is_violation}, probability={probability:.4f}"
            )
            
            # 4. Обновляем результат в БД
            # Находим запись moderation_results по item_id (последнюю pending)
            query = """
                UPDATE moderation_results
                SET status = 'completed',
                    is_violation = $1,
                    probability = $2,
                    processed_at = NOW()
                WHERE item_id = $3 
                  AND status = 'pending'
                RETURNING id
            """
            
            result = await self.db.fetchrow(query, is_violation, probability, item_id)
            
            if result:
                task_id = result['id']
                logger.info(
                    f"Результат модерации сохранён: task_id={task_id}, "
                    f"item_id={item_id}, is_violation={is_violation}"
                )
            else:
                logger.warning(
                    f"Не найдено pending задач для item_id={item_id}. "
                    "Возможно задача уже обработана."
                )
            
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения: {e}", exc_info=True)
            
            # Отправляем в DLQ
            await self.send_to_dlq(message, str(e))
            
            # Обновляем статус задачи как failed
            try:
                item_id = message.value.get('item_id')
                if item_id:
                    query = """
                        UPDATE moderation_results
                        SET status = 'failed',
                            error_message = $1,
                            processed_at = NOW()
                        WHERE item_id = $2 
                          AND status = 'pending'
                    """
                    await self.db.execute(query, str(e), item_id)
                    logger.info(f"Статус задачи обновлён на 'failed' для item_id={item_id}")
            except Exception as update_error:
                logger.error(f"Ошибка при обновлении статуса failed: {update_error}")
    
    async def send_to_dlq(self, message, error_message: str):
        """
        Отправка сообщения в Dead Letter Queue.
        
        Args:
            message: Исходное сообщение
            error_message: Сообщение об ошибке
        """
        try:
            dlq_message = {
                "original_message": message.value,
                "error": error_message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "topic": message.topic,
                "partition": message.partition,
                "offset": message.offset
            }
            
            await self.dlq_producer.send_and_wait(
                self.settings.kafka.topic_dlq,
                value=dlq_message
            )
            
            logger.warning(
                f"Сообщение отправлено в DLQ: item_id={message.value.get('item_id')}, "
                f"error={error_message}"
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке в DLQ: {e}", exc_info=True)
    
    async def run(self):
        """Основной цикл обработки сообщений"""
        try:
            async for message in self.consumer:
                if not self.running:
                    break
                
                await self.process_message(message)
        
        except asyncio.CancelledError:
            logger.info("Воркер получил сигнал остановки")
        except Exception as e:
            logger.error(f"Критическая ошибка в воркере: {e}", exc_info=True)
        finally:
            await self.stop()


async def main():
    """Точка входа для воркера"""
    worker = ModerationWorker()
    
    # Обработка сигналов для graceful shutdown
    loop = asyncio.get_running_loop()
    
    def signal_handler():
        logger.info("Получен сигнал остановки (SIGINT/SIGTERM)")
        asyncio.create_task(worker.stop())
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    try:
        await worker.start()
        await worker.run()
    except KeyboardInterrupt:
        logger.info("Воркер прерван пользователем")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}", exc_info=True)
    finally:
        await worker.stop()


if __name__ == "__main__":
    logger.info("="*60)
    logger.info("Запуск Moderation Worker")
    logger.info("="*60)
    
    asyncio.run(main())
