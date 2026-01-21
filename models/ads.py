from pydantic import BaseModel, Field, field_validator


class AdRequest(BaseModel):
    seller_id: int
    is_verified_seller: bool
    item_id: int
    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    category: int
    images_qty: int = Field(..., ge=0)

    @field_validator('name', 'description')
    @classmethod
    def check_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Поле не может быть пустым')
        return v