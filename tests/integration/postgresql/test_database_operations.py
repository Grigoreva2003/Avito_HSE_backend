import pytest
import pytest_asyncio

from database import get_database

@pytest.mark.integration
@pytest.mark.asyncio
class TestDatabaseOperations:
    """Тесты работы с базой данных."""

    @pytest_asyncio.fixture(autouse=True)
    async def ensure_database_pool(self):
        """
        Для integration тестов держим lifecycle БД в пределах одного теста,
        чтобы пул не пересекался между разными event loop.
        """
        db = get_database()
        await db.connect()
        try:
            yield
        finally:
            await db.disconnect()

    async def test_create_seller(self, seller_repository):
        """Тест создания продавца в БД."""
        seller = await seller_repository.create(
            name="Test Seller",
            is_verified=True
        )

        assert seller is not None
        assert seller.name == "Test Seller"
        assert seller.is_verified is True
        assert seller.id is not None

        # Очистка
        await seller_repository.delete(seller.id)

    async def test_create_ad(self, seller_repository, ad_repository):
        """Тест создания объявления в БД."""
        # Сначала создаем продавца
        seller = await seller_repository.create(
            name="Test Seller for Ad",
            is_verified=False
        )

        # Создаем объявление
        ad = await ad_repository.create(
            seller_id=seller.id,
            name="Test Product",
            description="Test description",
            category=10,
            images_qty=5
        )

        assert ad is not None
        assert ad.name == "Test Product"
        assert ad.seller_id == seller.id
        assert ad.images_qty == 5
        assert ad.id is not None

        # Очистка
        await ad_repository.delete(ad.id)
        await seller_repository.delete(seller.id)

    async def test_get_ad_with_seller(self, seller_repository, ad_repository):
        """Тест получения объявления со связанными данными продавца."""
        # Создаем продавца
        seller = await seller_repository.create(
            name="Verified Seller",
            is_verified=True
        )

        # Создаем объявление
        ad = await ad_repository.create(
            seller_id=seller.id,
            name="Premium Product",
            description="Quality description",
            category=5,
            images_qty=10
        )

        # Получаем объявление со связанными данными
        fetched_ad = await ad_repository.get_by_id(ad.id, include_seller=True)

        assert fetched_ad is not None
        assert fetched_ad.id == ad.id
        assert fetched_ad.seller_id == seller.id
        assert fetched_ad.seller_is_verified is True  # Проверяем что данные продавца подтянулись

        # Очистка
        await ad_repository.delete(ad.id)
        await seller_repository.delete(seller.id)

    async def test_get_nonexistent_ad(self, ad_repository):
        """Тест получения несуществующего объявления."""
        ad = await ad_repository.get_by_id(999999)
        assert ad is None

    async def test_close_ad_marks_is_closed(self, seller_repository, ad_repository):
        """Тест закрытия объявления: is_closed=TRUE и скрытие из обычной выборки."""
        seller = await seller_repository.create(
            name="Seller for close test",
            is_verified=True
        )
        ad = await ad_repository.create(
            seller_id=seller.id,
            name="Close me",
            description="Ad will be closed",
            category=2,
            images_qty=1
        )

        closed = await ad_repository.close(ad.id)
        assert closed is True

        # Закрытое объявление по умолчанию не возвращается
        assert await ad_repository.get_by_id(ad.id) is None

        # Но должно быть доступно при include_closed=True
        closed_ad = await ad_repository.get_by_id(ad.id, include_closed=True)
        assert closed_ad is not None
        assert closed_ad.id == ad.id
        assert closed_ad.is_closed is True

        # Очистка
        await ad_repository.delete(ad.id)
        await seller_repository.delete(seller.id)
