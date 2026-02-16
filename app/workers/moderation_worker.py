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

    Поддерживает механизм retry для временных ошибок:
    - Максимум 3 попытки
    - Задержка между попытками
    - Автоматическое различение временных и постоянных ошибок
    """

    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 5  # Задержка перед повторной попыткой

    def __init__(self):
        self.settings = get_settings()
        self.consumer = None
        self.dlq_producer = None
        self.retry_producer = None  # Producer для повторных попыток
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

        # Создание Retry Producer (для повторных попыток)
        self.retry_producer = AIOKafkaProducer(
            bootstrap_servers=self.settings.kafka.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )

        await self.consumer.start()
        await self.dlq_producer.start()
        await self.retry_producer.start()

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

        if self.retry_producer:
            await self.retry_producer.stop()

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
            retry_count = data.get('retry_count', 0)

            logger.info(
                f"Получено сообщение: item_id={item_id}, "
                f"timestamp={timestamp}, retry_count={retry_count}"
            )

            if not item_id:
                logger.error(f"Сообщение не содержит item_id: {data}")
                await self.send_to_dlq(message, "Missing item_id in message", is_permanent=True)
                return

            # 1. Получаем данные объявления из БД
            ad = await self.ad_repository.get_by_id(item_id, include_seller=True)

            if ad is None:
                error_msg = f"Объявление не найдено: item_id={item_id}"
                logger.error(error_msg)

                # Это постоянная ошибка - объявление не появится при повторе
                await self._update_moderation_status_failed(item_id, error_msg)
                await self.send_to_dlq(message, error_msg, is_permanent=True)
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

        except RuntimeError as e:
            # Временная ошибка (например, ML-модель недоступна)
            error_msg = f"Временная ошибка: {str(e)}"
            logger.warning(error_msg)

            retry_count = message.value.get('retry_count', 0)
            item_id = message.value.get('item_id')

            if retry_count < self.MAX_RETRIES:
                # Повторная попытка
                await self.schedule_retry(message, error_msg)
            else:
                # Исчерпаны попытки
                logger.error(f"Исчерпаны попытки для item_id={item_id} после {retry_count} попыток")
                if item_id:
                    await self._update_moderation_status_failed(
                        item_id,
                        f"Максимум попыток достигнут. Последняя ошибка: {str(e)}"
                    )
                await self.send_to_dlq(message, error_msg, is_permanent=False)

        except Exception as e:
            # Неизвестная ошибка - считаем постоянной
            error_msg = f"Критическая ошибка при обработке: {str(e)}"
            logger.error(error_msg, exc_info=True)

            item_id = message.value.get('item_id')
            retry_count = message.value.get('retry_count', 0)

            # Проверяем retry_count
            if retry_count < self.MAX_RETRIES:
                # Дадим еще шанс
                await self.schedule_retry(message, error_msg)
            else:
                # Исчерпаны попытки
                if item_id:
                    await self._update_moderation_status_failed(item_id, str(e))
                await self.send_to_dlq(message, error_msg, is_permanent=False)

    async def _update_moderation_status_failed(self, item_id: int, error_message: str):
        """
        Обновить статус модерации на failed.

        Args:
            item_id: ID объявления
            error_message: Сообщение об ошибке
        """
        try:
            query = """
                UPDATE moderation_results
                SET status = 'failed',
                    error_message = $1,
                    processed_at = NOW()
                WHERE item_id = $2
                  AND status = 'pending'
                RETURNING id
            """
            result = await self.db.fetchrow(query, error_message, item_id)

            if result:
                task_id = result['id']
                logger.info(
                    f"Статус задачи обновлён на 'failed': task_id={task_id}, "
                    f"item_id={item_id}, error={error_message}"
                )
            else:
                logger.warning(
                    f"Не найдено pending задач для обновления на failed: item_id={item_id}"
                )
        except Exception as update_error:
            logger.error(
                f"Ошибка при обновлении статуса failed для item_id={item_id}: {update_error}",
                exc_info=True
            )

    async def schedule_retry(self, message, error_message: str):
        """
        Запланировать повторную попытку обработки.

        Args:
            message: Исходное сообщение
            error_message: Сообщение об ошибке
        """
        try:
            original_data = message.value
            retry_count = original_data.get('retry_count', 0) + 1
            item_id = original_data.get('item_id')

            # Создаем новое сообщение с увеличенным retry_count
            retry_message = {
                "item_id": item_id,
                "timestamp": original_data.get('timestamp'),
                "retry_count": retry_count,
                "last_error": error_message
            }

            logger.info(
                f"Запланирована повторная попытка #{retry_count}/{self.MAX_RETRIES} "
                f"для item_id={item_id} через {self.RETRY_DELAY_SECONDS} сек"
            )

            # Задержка перед повторной отправкой
            await asyncio.sleep(self.RETRY_DELAY_SECONDS)

            # Отправляем обратно в основной топик
            await self.retry_producer.send_and_wait(
                self.settings.kafka.topic_moderation,
                value=retry_message
            )

            logger.info(
                f"Сообщение отправлено на повторную обработку: "
                f"item_id={item_id}, retry_count={retry_count}"
            )

        except Exception as e:
            logger.error(f"Ошибка при планировании retry: {e}", exc_info=True)
            # Если не удалось отправить на retry, отправляем в DLQ
            await self.send_to_dlq(message, f"Ошибка retry механизма: {str(e)}", is_permanent=True)

    async def send_to_dlq(self, message, error_message: str, is_permanent: bool = False):
        """
        Отправка сообщения в Dead Letter Queue.

        Args:
            message: Исходное сообщение
            error_message: Сообщение об ошибке
            is_permanent: Является ли ошибка постоянной (не временной)
        """
        try:
            original_data = message.value
            retry_count = original_data.get('retry_count', 0)

            error_type = "permanent" if is_permanent else "max_retries_exceeded"

            dlq_message = {
                "original_message": original_data,
                "error": error_message,
                "error_type": error_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "retry_count": retry_count,
                "topic": message.topic,
                "partition": message.partition,
                "offset": message.offset
            }

            await self.dlq_producer.send_and_wait(
                self.settings.kafka.topic_dlq,
                value=dlq_message
            )

            logger.warning(
                f"Сообщение отправлено в DLQ: item_id={original_data.get('item_id')}, "
                f"error={error_message}, retry_count={retry_count}, type={error_type}"
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
