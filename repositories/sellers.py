import logging
from typing import Optional
from database import get_database

logger = logging.getLogger(__name__)


class Seller:
    """Модель продавца (пользователя)"""
    
    def __init__(
        self,
        id: int,
        name: str,
        is_verified: bool,
        created_at=None,
        updated_at=None
    ):
        self.id = id
        self.name = name
        self.is_verified = is_verified
        self.created_at = created_at
        self.updated_at = updated_at
    
    @classmethod
    def from_record(cls, record) -> 'Seller':
        """Создает объект Seller из записи БД"""
        if record is None:
            return None
        return cls(
            id=record['id'],
            name=record['name'],
            is_verified=record['is_verified'],
            created_at=record.get('created_at'),
            updated_at=record.get('updated_at')
        )
    
    def __repr__(self):
        return f"Seller(id={self.id}, name='{self.name}', is_verified={self.is_verified})"


class SellerRepository:
    """Репозиторий для работы с продавцами"""
    
    def __init__(self):
        self.db = get_database()
    
    async def get_by_id(self, seller_id: int) -> Optional[Seller]:
        """
        Получить продавца по ID.
        
        Args:
            seller_id: ID продавца
            
        Returns:
            Optional[Seller]: Продавец или None
        """
        query = """
            SELECT id, name, is_verified, created_at, updated_at
            FROM sellers
            WHERE id = $1
        """
        
        try:
            record = await self.db.fetchrow(query, seller_id)
            seller = Seller.from_record(record)
            
            if seller:
                logger.debug(f"Found seller: {seller}")
            else:
                logger.debug(f"Seller not found: id={seller_id}")
            
            return seller
        except Exception as e:
            logger.error(f"Error fetching seller {seller_id}: {e}")
            raise
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> list[Seller]:
        """
        Получить всех продавцов.
        
        Args:
            limit: Максимальное количество записей
            offset: Смещение
            
        Returns:
            list[Seller]: Список продавцов
        """
        query = """
            SELECT id, name, is_verified, created_at, updated_at
            FROM sellers
            ORDER BY id
            LIMIT $1 OFFSET $2
        """
        
        try:
            records = await self.db.fetch(query, limit, offset)
            sellers = [Seller.from_record(record) for record in records]
            logger.debug(f"Found {len(sellers)} sellers")
            return sellers
        except Exception as e:
            logger.error(f"Error fetching sellers: {e}")
            raise
    
    async def create(self, name: str, is_verified: bool = False) -> Seller:
        """
        Создать нового продавца.
        
        Args:
            name: Имя продавца
            is_verified: Подтвержден ли продавец
            
        Returns:
            Seller: Созданный продавец
        """
        query = """
            INSERT INTO sellers (name, is_verified)
            VALUES ($1, $2)
            RETURNING id, name, is_verified, created_at, updated_at
        """
        
        try:
            record = await self.db.fetchrow(query, name, is_verified)
            seller = Seller.from_record(record)
            logger.info(f"Created seller: {seller}")
            return seller
        except Exception as e:
            logger.error(f"Error creating seller: {e}")
            raise
    
    async def update(self, seller_id: int, name: Optional[str] = None, is_verified: Optional[bool] = None) -> Optional[Seller]:
        """
        Обновить данные продавца.
        
        Args:
            seller_id: ID продавца
            name: Новое имя (опционально)
            is_verified: Новый статус верификации (опционально)
            
        Returns:
            Optional[Seller]: Обновленный продавец или None
        """
        # Формируем SET часть запроса динамически
        updates = []
        params = []
        param_num = 1
        
        if name is not None:
            updates.append(f"name = ${param_num}")
            params.append(name)
            param_num += 1
        
        if is_verified is not None:
            updates.append(f"is_verified = ${param_num}")
            params.append(is_verified)
            param_num += 1
        
        if not updates:
            return await self.get_by_id(seller_id)
        
        updates.append(f"updated_at = CURRENT_TIMESTAMP")
        params.append(seller_id)
        
        query = f"""
            UPDATE sellers
            SET {', '.join(updates)}
            WHERE id = ${param_num}
            RETURNING id, name, is_verified, created_at, updated_at
        """
        
        try:
            record = await self.db.fetchrow(query, *params)
            seller = Seller.from_record(record)
            if seller:
                logger.info(f"Updated seller: {seller}")
            return seller
        except Exception as e:
            logger.error(f"Error updating seller {seller_id}: {e}")
            raise
    
    async def delete(self, seller_id: int) -> bool:
        """
        Удалить продавца.
        
        Args:
            seller_id: ID продавца
            
        Returns:
            bool: True если удален, False если не найден
        """
        query = "DELETE FROM sellers WHERE id = $1"
        
        try:
            result = await self.db.execute(query, seller_id)
            deleted = result == "DELETE 1"
            if deleted:
                logger.info(f"Deleted seller: id={seller_id}")
            else:
                logger.debug(f"Seller not found for deletion: id={seller_id}")
            return deleted
        except Exception as e:
            logger.error(f"Error deleting seller {seller_id}: {e}")
            raise
