from fastapi import APIRouter
from app.services.user_services import register_user
from app.schemas.user_schema import UserCreate


router = APIRouter(prefix = "/api/User")
@router.post("/register")
def register(user : UserCreate):
    print("Registering user:", user.email)
    return register_user(user)
