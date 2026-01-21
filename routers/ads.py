from fastapi import APIRouter
from models.ads import AdRequest

router = APIRouter()


@router.post("/predict")
async def predict(ad_data: AdRequest) -> bool:
    """
    Предсказать наличие нарушения в объявлении

    Логика:
    - Подтвержденные продавцы (is_verified_seller=True) всегда публикуют объявления без нарушений
    - Неподтвержденные продавцы публикуют без нарушений только при наличии изображений (images_qty > 0)

    Args:
        seller_id: id продавца,
        is_verified_seller: статуст продавца (подтвержденный/не подтвержденный),
        item_id: id товара,
        name: название товара,
        description: описание товара,
        category: категория,
        images_qty: количество изображений

    Returns:
        bool: True если есть нарушения, False если нарушений нет
    """

    if ad_data.is_verified_seller or ad_data.images_qty > 0:
        return False
    return True