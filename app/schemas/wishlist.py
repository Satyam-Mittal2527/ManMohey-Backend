from pydantic import BaseModel, Field


class WishlistItemCreate(BaseModel):
    product_id: int = Field(..., gt=0)
