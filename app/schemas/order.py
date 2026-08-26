from typing import Optional, List

from pydantic import BaseModel, Field


class OrderCreate(BaseModel):
    address_id: str


class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    sku: Optional[str] = None
    quantity: int
    size: Optional[str] = None
    unit_price: float
    subtotal: float


class OrderResponse(BaseModel):
    id: int
    order_number: str
    user_id: str

    full_name: str
    phone_number: str
    address_line_1: str
    address_line_2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str

    subtotal: float
    shipping_fee: float
    discount: float
    total_amount: float

    status: str
    payment_status: str

    items: List[OrderItemResponse] = Field(
        default_factory=list
    )