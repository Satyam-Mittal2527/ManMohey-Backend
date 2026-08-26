from typing import Optional

from pydantic import BaseModel, Field


class AddressCreate(BaseModel):
    full_name: str = Field(..., min_length=1)
    phone_number: str = Field(..., min_length=7)

    address_line_1: str = Field(..., min_length=1)
    address_line_2: Optional[str] = None

    city: str = Field(..., min_length=1)
    state: str = Field(..., min_length=1)
    postal_code: str = Field(..., min_length=3)
    country: str = "India"

    address_type: str = "Home"
    is_default: bool = False


class AddressUpdate(BaseModel):
    full_name: Optional[str] = Field(
        default=None,
        min_length=1
    )

    phone_number: Optional[str] = Field(
        default=None,
        min_length=7
    )

    address_line_1: Optional[str] = Field(
        default=None,
        min_length=1
    )

    address_line_2: Optional[str] = None

    city: Optional[str] = Field(
        default=None,
        min_length=1
    )

    state: Optional[str] = Field(
        default=None,
        min_length=1
    )

    postal_code: Optional[str] = Field(
        default=None,
        min_length=3
    )

    country: Optional[str] = None

    address_type: Optional[str] = None

    is_default: Optional[bool] = None