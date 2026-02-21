import logging
from typing import Optional
from database import get_database

logger = logging.getLogger(__name__)


class ModerationResult:
    """Модель для результата модерации"""
    
    def __init__(
        self,
        id: int,
        item_id: int,
        status: str,
        is_violation: Optional[bool] = None,
        probability: Optional[float] = None,
        error_message: Optional[str] = None,
        created_at: Optional[str] = None,
        processed_at: Optional[str] = None
    ):
        self.id = id
        self.item_id = item_id
        self.status = status
        self.is_violation = is_violation
        self.probability = probability
        self.error_message = error_message
        self.created_at = created_at
        self.processed_at = processed_at


class ModerationResultRepository:
    """Репозиторий для работы с результатами модерации"""
    
    def __init__(self):
        self._db = get_database()
    
    async def create(self, item_id: int, status: str = "pending") -> ModerationResult:
        """
        Создать новую запись результата модерации.
        
        Args:
            item_id: ID объявления
            status: Статус модерации (по умолчанию "pending")
            
        Returns:
            ModerationResult: Созданный результат модерации
        """
        query = """
            INSERT INTO moderation_results (item_id, status)
            VALUES ($1, $2)
            RETURNING id, item_id, status, is_violation, probability, 
                      error_message, created_at, processed_at
        """
        
        row = await self._db.fetchrow(query, item_id, status)
        
        logger.info(f"Создана запись модерации: id={row['id']}, item_id={item_id}, status={status}")
        
        return ModerationResult(
            id=row['id'],
            item_id=row['item_id'],
            status=row['status'],
            is_violation=row['is_violation'],
            probability=row['probability'],
            error_message=row['error_message'],
            created_at=row['created_at'].isoformat() if row['created_at'] else None,
            processed_at=row['processed_at'].isoformat() if row['processed_at'] else None
        )
    
    async def get_by_id(self, task_id: int) -> Optional[ModerationResult]:
        """
        Получить результат модерации по ID.
        
        Args:
            task_id: ID задачи модерации
            
        Returns:
            ModerationResult или None если не найдено
        """
        query = """
            SELECT id, item_id, status, is_violation, probability,
                   error_message, created_at, processed_at
            FROM moderation_results
            WHERE id = $1
        """
        
        row = await self._db.fetchrow(query, task_id)
        
        if row is None:
            return None
        
        return ModerationResult(
            id=row['id'],
            item_id=row['item_id'],
            status=row['status'],
            is_violation=row['is_violation'],
            probability=row['probability'],
            error_message=row['error_message'],
            created_at=row['created_at'].isoformat() if row['created_at'] else None,
            processed_at=row['processed_at'].isoformat() if row['processed_at'] else None
        )
    
    async def update_completed(
        self,
        task_id: int,
        is_violation: bool,
        probability: float
    ) -> None:
        """
        Обновить результат модерации как завершённый.
        
        Args:
            task_id: ID задачи модерации
            is_violation: Результат модерации
            probability: Вероятность нарушения
        """
        query = """
            UPDATE moderation_results
            SET status = 'completed',
                is_violation = $2,
                probability = $3,
                processed_at = NOW()
            WHERE id = $1
        """
        
        await self._db.execute(query, task_id, is_violation, probability)
        logger.info(f"Результат модерации обновлён: task_id={task_id}, is_violation={is_violation}")
    
    async def update_failed(self, task_id: int, error_message: str) -> None:
        """
        Обновить результат модерации как неудачный.
        
        Args:
            task_id: ID задачи модерации
            error_message: Сообщение об ошибке
        """
        query = """
            UPDATE moderation_results
            SET status = 'failed',
                error_message = $2,
                processed_at = NOW()
            WHERE id = $1
        """
        
        await self._db.execute(query, task_id, error_message)
        logger.error(f"Модерация завершилась с ошибкой: task_id={task_id}, error={error_message}")

    async def get_task_ids_by_item_id(self, item_id: int) -> list[int]:
        """
        Получить ID задач модерации по item_id.

        Args:
            item_id: ID объявления

        Returns:
            list[int]: Список task_id
        """
        query = """
            SELECT id
            FROM moderation_results
            WHERE item_id = $1
            ORDER BY id
        """
        rows = await self._db.fetch(query, item_id)
        return [row["id"] for row in rows]

    async def delete_by_item_id(self, item_id: int) -> int:
        """
        Удалить все результаты модерации по item_id.

        Args:
            item_id: ID объявления

        Returns:
            int: Количество удаленных записей
        """
        query = """
            DELETE FROM moderation_results
            WHERE item_id = $1
            RETURNING id
        """
        rows = await self._db.fetch(query, item_id)
        deleted_count = len(rows)
        logger.info(f"Удалены результаты модерации: item_id={item_id}, deleted={deleted_count}")
        return deleted_count
