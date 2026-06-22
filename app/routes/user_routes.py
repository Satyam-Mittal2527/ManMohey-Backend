from fastapi import APIRouter, Response
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
async def verifyOtp(request: Request, response: Response):
    value = await request.json()

    print(value)
    print(type(value))

    result = verify_otp(
        value["email"],
        value["token"]
    )

    access = result.get("access_token")
    refresh = result.get("refresh_token")

    if access:
        response.set_cookie(
            key="access_token",
            value=access,
            httponly=True,
            samesite="none",
            secure=True,
        )

    if refresh:
        response.set_cookie(
            key="refresh_token",
            value=refresh,
            httponly=True,
            samesite="none",
            secure=True,
        )

    return result


@router.get("/me")
async def get_current_user(request: Request):
    access = request.cookies.get("access_token")
    if not access:
        return {"user": None}

    try:
        # Try common supabase auth methods; adapt if your client differs
        user = None
        try:
            user = supabase.auth.get_user(access)
        except Exception:
            try:
                user = supabase.auth.api.get_user(access)
            except Exception:
                user = None

        if not user:
            return {"user": None}

        # The `user` object structure depends on supabase client; normalize
        u = getattr(user, "user", user)
        return {"user": u}

    except Exception as e:
        print("me route error:", e)
        return {"user": None}


@router.post("/logout")
async def logout(response: Response):
    # Clear auth cookies on logout
    response.delete_cookie(
        key="access_token",
        path="/",
        samesite="none",
    )
    response.delete_cookie(
        key="refresh_token",
        path="/",
        samesite="none",
    )
    return {"message": "Logged out"}