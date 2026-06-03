from fastapi import APIRouter
from app.services.user_services import register_user, sign_otp, verify_otp
from app.schemas.user_schema import UserCreate
from fastapi import Request

router = APIRouter(prefix = "/api/User")
@router.post("/register")
def register(user : UserCreate):
    print("Registering user:", user.email)
    return register_user(user)

@router.post("/send-otp")
async def sendOtp(request: Request):
    value = await request.json()

    print("Received Data", value)

    return sign_otp(value)

    
@router.post("/verify-otp")
async def verifyOtp(request: Request):
    value = await request.json()

    print(value)
    print(type(value))

    return verify_otp(
        value["email"],
        value["token"]
    )