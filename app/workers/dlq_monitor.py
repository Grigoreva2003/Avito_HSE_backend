"""
DLQ Monitor - инструмент для мониторинга и анализа сообщений в Dead Letter Queue.

Запуск:
    python -m app.workers.dlq_monitor
"""

import asyncio
import json
import logging
from datetime import datetime
from aiokafka import AIOKafkaConsumer
from config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DLQMonitor:
    """
    Монитор для просмотра сообщений в DLQ топике.
    Полезен для анализа ошибок и отладки.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.consumer = None
        self.running = False
    
    async def start(self):
        """Запуск мониторинга DLQ"""
        logger.info("Запуск DLQ Monitor...")
        
        self.consumer = AIOKafkaConsumer(
            self.settings.kafka.topic_dlq,
            bootstrap_servers=self.settings.kafka.bootstrap_servers,
            group_id='dlq_monitor',
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True
        )
        
        await self.consumer.start()
        logger.info(f"Мониторинг DLQ топика: {self.settings.kafka.topic_dlq}")
        self.running = True
    
    async def stop(self):
        """Остановка монитора"""
        logger.info("Остановка DLQ Monitor...")
        self.running = False
        
        if self.consumer:
            await self.consumer.stop()
        
        logger.info("DLQ Monitor остановлен")
    
    async def monitor(self):
        """Основной цикл мониторинга"""
        try:
            message_count = 0
            
            async for message in self.consumer:
                if not self.running:
                    break
                
                message_count += 1
                data = message.value
                
                logger.info("="*80)
                logger.info(f"DLQ Message #{message_count}")
                logger.info("="*80)
                logger.info(f"Timestamp: {data.get('timestamp')}")
                logger.info(f"Retry Count: {data.get('retry_count', 0)}")
                logger.info(f"Error: {data.get('error')}")
                logger.info(f"Original Message: {json.dumps(data.get('original_message'), indent=2)}")
                logger.info(f"Topic: {data.get('topic')}")
                logger.info(f"Partition: {data.get('partition')}")
                logger.info(f"Offset: {data.get('offset')}")
                logger.info("="*80)
        
        except asyncio.CancelledError:
            logger.info("Мониторинг прерван")
        except Exception as e:
            logger.error(f"Ошибка в мониторе: {e}", exc_info=True)
        finally:
            await self.stop()


async def main():
    """Точка входа для DLQ монитора"""
    monitor = DLQMonitor()
    
    try:
        await monitor.start()
        await monitor.monitor()
    except KeyboardInterrupt:
        logger.info("Монитор прерван пользователем")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}", exc_info=True)
    finally:
        await monitor.stop()


if __name__ == "__main__":
    logger.info("="*60)
    logger.info("Запуск DLQ Monitor")
    logger.info("Нажмите Ctrl+C для остановки")
    logger.info("="*60)
    
    asyncio.run(main())
