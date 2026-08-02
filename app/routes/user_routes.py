from fastapi import APIRouter, Depends, Response, HTTPException, Request
from app.services.user_services import register_user, sign_otp, verify_otp
from app.schemas.user_schema import UserCreate
from app.db.supabase_client import supabase, supabase_admin
from fastapi.responses import JSONResponse
from app.dependencies.auth import get_current_user as require_current_user, get_optional_current_user

router = APIRouter(prefix = "/api/User")
@router.post("/register")
def register(user : UserCreate):
    print("Registering user:", user.email)
    return register_user(user)

@router.post("/send-otp")
async def sendOtp(request: Request):
    value = await request.json()

    # print("Received Data", value)

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

    secure_cookie = request.url.scheme == "https"
    same_site = "none" if secure_cookie else "lax"

    if access:
        response.set_cookie(
            key="access_token",
            value=access,
            httponly=True,
            samesite=same_site,
            secure=secure_cookie,
            path="/",
        )

    if refresh:
        response.set_cookie(
            key="refresh_token",
            value=refresh,
            httponly=True,
            samesite=same_site,
            secure=secure_cookie,
            path="/",
        )

    return result


@router.get("/me")
async def get_current_user_route(current_auth: dict | None = Depends(get_optional_current_user)):
    if not current_auth:
        return {"user": None}

    try:
        user = current_auth["user"]
        user_id = current_auth["user_id"]
        print("/me resolved user id:", user_id)

        profile = None
        try:
            profiles_resp = supabase_admin.table("profiles").select("id, email, first_name, last_name, phone_number").eq("id", user_id).single().execute()
            profile = getattr(profiles_resp, "data", None) or (profiles_resp.data if hasattr(profiles_resp, "data") else None)
            print("/me profiles query result:", profile)
        except Exception as e:
            print("profiles query error in /me:", e)

        return {"user": user, "profile": profile}

    except Exception as e:
        print("me route error:", e)
        return {"user": None}


@router.post("/change-password")
async def change_password(request: Request, current_auth: dict = Depends(require_current_user)):
    payload = await request.json()
    current_password = payload.get("current_password")
    new_password = payload.get("new_password")
    confirm_password = payload.get("confirm_password")

    if not current_password or not new_password or not confirm_password:
        raise HTTPException(status_code=400, detail="All password fields are required")

    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="New password and confirm password do not match")

    try:
        user = current_auth["user"]
        if not user:
            raise HTTPException(status_code=401, detail="Invalid authentication")

        email = getattr(user, "email", None) or (user.get("email") if isinstance(user, dict) else None)
        user_id = current_auth["user_id"]

        if not email or not user_id:
            raise HTTPException(status_code=400, detail="User email or id not available")

        try:
            auth_resp = supabase.auth.sign_in_with_password({
                "email": email,
                "password": current_password,
            })
            if getattr(auth_resp, "user", None) is None and not getattr(auth_resp, "session", None):
                raise Exception("Invalid credentials")
        except Exception as e:
            print("change_password verify current password error:", e)
            raise HTTPException(status_code=401, detail="Wrong current password")

        try:
            updated_resp = supabase_admin.auth.admin.update_user_by_id(user_id, {"password": new_password})
        except Exception as e:
            print("change_password update user error:", e)
            raise HTTPException(status_code=500, detail="Failed to update password")

        return {"status": "ok", "message": "Password updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        print("change_password error:", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/profile")
async def update_profile(request: Request, response: Response, current_auth: dict = Depends(require_current_user)):
    user_id = current_auth["user_id"]
    if not user_id:
        raise HTTPException(status_code=400, detail="User id not found")

    try:
        payload = await request.json()
        # accept first_name, last_name, email, phone_number
        update_data = {}
        if "first_name" in payload:
            update_data["first_name"] = payload["first_name"]
        if "last_name" in payload:
            update_data["last_name"] = payload["last_name"]
        if "email" in payload:
            update_data["email"] = payload["email"]
        if "phone_number" in payload:
            update_data["phone_number"] = payload["phone_number"]

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        try:
            res = supabase_admin.table("profiles").update(update_data).eq("id", user_id).execute()
            updated = getattr(res, "data", None) or (res.data if hasattr(res, "data") else None)
        except Exception as e:
            print("profile update error:", e)
            raise HTTPException(status_code=500, detail="Failed to update profile")

        return {"status": "ok", "profile": (updated[0] if isinstance(updated, list) and len(updated) > 0 else updated)}

    except HTTPException:
        raise
    except Exception as e:
        print("update_profile error:", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/reset-password")
async def reset_password(request: Request, current_auth: dict = Depends(require_current_user)):
    payload = await request.json()
    new_password = payload.get("new_password")
    confirm_password = payload.get("confirm_password")

    if not new_password or not confirm_password:
        raise HTTPException(status_code=400, detail="Both password fields are required")

    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="New password and confirm password do not match")

    try:
        user_id = current_auth["user_id"]
        if not user_id:
            raise HTTPException(status_code=400, detail="User id not available")

        try:
            supabase_admin.auth.admin.update_user_by_id(user_id, {"password": new_password})
        except Exception as e:
            print("reset_password update user error:", e)
            raise HTTPException(status_code=500, detail="Failed to reset password")

        return {"status": "ok", "message": "Password reset successfully"}

    except HTTPException:
        raise
    except Exception as e:
        print("reset_password error:", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/logout")
async def logout():
    # print("Logging out user")
    response = JSONResponse({"message": "Logged out"})

    response.delete_cookie(
        key="access_token",
        path="/",
    )
    response.delete_cookie(
        key="refresh_token",
        path="/",
    )

    return response