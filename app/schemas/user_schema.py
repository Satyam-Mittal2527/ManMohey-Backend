from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date
from decimal import Decimal

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    age: Optional[int] = None
    phone_number: Optional[str] = None
    
