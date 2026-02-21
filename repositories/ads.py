import logging
from typing import Optional
from database import get_database

logger = logging.getLogger(__name__)


class Ad:
    """Модель объявления"""
    
    def __init__(
        self,
        id: int,
        seller_id: int,
        name: str,
        description: str,
        category: int,
        images_qty: int,
        is_closed: bool = False,
        created_at=None,
        updated_at=None,
        seller_is_verified: Optional[bool] = None
    ):
        self.id = id
        self.seller_id = seller_id
        self.name = name
        self.description = description
        self.category = category
        self.images_qty = images_qty
        self.is_closed = is_closed
        self.created_at = created_at
        self.updated_at = updated_at
        self.seller_is_verified = seller_is_verified
    
    @classmethod
    def from_record(cls, record) -> 'Ad':
        """Создает объект Ad из записи БД"""
        if record is None:
            return None
        return cls(
            id=record['id'],
            seller_id=record['seller_id'],
            name=record['name'],
            description=record['description'],
            category=record['category'],
            images_qty=record['images_qty'],
            is_closed=record.get('is_closed', False),
            created_at=record.get('created_at'),
            updated_at=record.get('updated_at'),
            seller_is_verified=record.get('seller_is_verified')
        )
    
    def __repr__(self):
        return f"Ad(id={self.id}, seller_id={self.seller_id}, name='{self.name[:30]}...')"


class AdRepository:
    """Репозиторий для работы с объявлениями"""
    
    def __init__(self):
        self.db = get_database()
    
    async def get_by_id(self, ad_id: int, include_seller: bool = False) -> Optional[Ad]:
        """
        Получить объявление по ID.
        
        Args:
            ad_id: ID объявления
            include_seller: Включить информацию о продавце
            
        Returns:
            Optional[Ad]: Объявление или None
        """
        if include_seller:
            query = """
                SELECT 
                    a.id, a.seller_id, a.name, a.description, 
                    a.category, a.images_qty, a.is_closed, a.created_at, a.updated_at,
                    s.is_verified as seller_is_verified
                FROM ads a
                JOIN sellers s ON a.seller_id = s.id
                WHERE a.id = $1
            """
        else:
            query = """
                SELECT id, seller_id, name, description, category, images_qty, is_closed, created_at, updated_at
                FROM ads
                WHERE id = $1
            """
        
        try:
            record = await self.db.fetchrow(query, ad_id)
            ad = Ad.from_record(record)
            
            if ad:
                logger.debug(f"Found ad: {ad}")
            else:
                logger.debug(f"Ad not found: id={ad_id}")
            
            return ad
        except Exception as e:
            logger.error(f"Error fetching ad {ad_id}: {e}")
            raise
    
    async def get_by_seller(self, seller_id: int, limit: int = 100, offset: int = 0) -> list[Ad]:
        """
        Получить объявления продавца.
        
        Args:
            seller_id: ID продавца
            limit: Максимальное количество записей
            offset: Смещение
            
        Returns:
            list[Ad]: Список объявлений
        """
        query = """
            SELECT id, seller_id, name, description, category, images_qty, is_closed, created_at, updated_at
            FROM ads
            WHERE seller_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        """
        
        try:
            records = await self.db.fetch(query, seller_id, limit, offset)
            ads = [Ad.from_record(record) for record in records]
            logger.debug(f"Found {len(ads)} ads for seller {seller_id}")
            return ads
        except Exception as e:
            logger.error(f"Error fetching ads for seller {seller_id}: {e}")
            raise
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> list[Ad]:
        """
        Получить все объявления.
        
        Args:
            limit: Максимальное количество записей
            offset: Смещение
            
        Returns:
            list[Ad]: Список объявлений
        """
        query = """
            SELECT id, seller_id, name, description, category, images_qty, is_closed, created_at, updated_at
            FROM ads
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
        """
        
        try:
            records = await self.db.fetch(query, limit, offset)
            ads = [Ad.from_record(record) for record in records]
            logger.debug(f"Found {len(ads)} ads")
            return ads
        except Exception as e:
            logger.error(f"Error fetching ads: {e}")
            raise
    
    async def create(
        self,
        seller_id: int,
        name: str,
        description: str,
        category: int,
        images_qty: int = 0
    ) -> Ad:
        """
        Создать новое объявление.
        
        Args:
            seller_id: ID продавца
            name: Название товара
            description: Описание товара
            category: Категория
            images_qty: Количество изображений
            
        Returns:
            Ad: Созданное объявление
        """
        query = """
            INSERT INTO ads (seller_id, name, description, category, images_qty)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, seller_id, name, description, category, images_qty, is_closed, created_at, updated_at
        """
        
        try:
            record = await self.db.fetchrow(query, seller_id, name, description, category, images_qty)
            ad = Ad.from_record(record)
            logger.info(f"Created ad: {ad}")
            return ad
        except Exception as e:
            logger.error(f"Error creating ad: {e}")
            raise
    
    async def update(
        self,
        ad_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[int] = None,
        images_qty: Optional[int] = None
    ) -> Optional[Ad]:
        """
        Обновить объявление.
        
        Args:
            ad_id: ID объявления
            name: Новое название (опционально)
            description: Новое описание (опционально)
            category: Новая категория (опционально)
            images_qty: Новое количество изображений (опционально)
            
        Returns:
            Optional[Ad]: Обновленное объявление или None
        """
        updates = []
        params = []
        param_num = 1
        
        if name is not None:
            updates.append(f"name = ${param_num}")
            params.append(name)
            param_num += 1
        
        if description is not None:
            updates.append(f"description = ${param_num}")
            params.append(description)
            param_num += 1
        
        if category is not None:
            updates.append(f"category = ${param_num}")
            params.append(category)
            param_num += 1
        
        if images_qty is not None:
            updates.append(f"images_qty = ${param_num}")
            params.append(images_qty)
            param_num += 1
        
        if not updates:
            return await self.get_by_id(ad_id)
        
        updates.append(f"updated_at = CURRENT_TIMESTAMP")
        params.append(ad_id)
        
        query = f"""
            UPDATE ads
            SET {', '.join(updates)}
            WHERE id = ${param_num}
            RETURNING id, seller_id, name, description, category, images_qty, is_closed, created_at, updated_at
        """
        
        try:
            record = await self.db.fetchrow(query, *params)
            ad = Ad.from_record(record)
            if ad:
                logger.info(f"Updated ad: {ad}")
            return ad
        except Exception as e:
            logger.error(f"Error updating ad {ad_id}: {e}")
            raise
    
    async def delete(self, ad_id: int) -> bool:
        """
        Удалить объявление.
        
        Args:
            ad_id: ID объявления
            
        Returns:
            bool: True если удалено, False если не найдено
        """
        query = "DELETE FROM ads WHERE id = $1"
        
        try:
            result = await self.db.execute(query, ad_id)
            deleted = result == "DELETE 1"
            if deleted:
                logger.info(f"Deleted ad: id={ad_id}")
            else:
                logger.debug(f"Ad not found for deletion: id={ad_id}")
            return deleted
        except Exception as e:
            logger.error(f"Error deleting ad {ad_id}: {e}")
            raise
