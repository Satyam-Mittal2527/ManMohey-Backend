from pydantic import BaseModel


class AddProductCart(BaseModel):
    product_id: int
    quantity: int = 1
    size: str | None = None