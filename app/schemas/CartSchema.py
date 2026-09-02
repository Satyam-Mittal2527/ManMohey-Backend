from pydantic import BaseModel


class AddProductCart(BaseModel):
    product_id: int
    variant_id: int | None = None
    quantity: int = 1
    size: str | None = None