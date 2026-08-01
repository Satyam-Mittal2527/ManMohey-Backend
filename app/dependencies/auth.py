from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.db.supabase_client import supabase

security = HTTPBearer(auto_error=False)


def _resolve_user_from_response(response):
    if response is None:
        return None
    user = getattr(response, "user", response)
    if user is None and isinstance(response, dict):
        user = response.get("user") or response
    return user


def _get_user_by_token(token: str):
    try:
        user_resp = supabase.auth.get_user(token)
        user = _resolve_user_from_response(user_resp)
        if not user:
            raise Exception("Empty user response")
        return user
    except Exception:
        try:
            user_resp = supabase.auth.api.get_user(token)
            user = _resolve_user_from_response(user_resp)
            if not user:
                raise Exception("Empty user response")
            return user
        except Exception as exc:
            raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
):
    token = credentials.credentials if credentials else request.cookies.get("access_token")

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        masked = token[:8] + "..." if token else "(no token)"
    except Exception:
        masked = "(no token)"

    print(f"Auth check: token={masked}")
    user = _get_user_by_token(token)
    user_id = getattr(user, "id", None) or (user.get("id") if isinstance(user, dict) else None)

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    print(f"Auth resolved user_id={user_id}")
    return {
        "user_id": user_id,
        "access_token": token,
        "user": user,
    }


def get_optional_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
):
    token = credentials.credentials if credentials else request.cookies.get("access_token")
    if not token:
        return None

    try:
        return get_current_user(request=request, credentials=credentials)
    except HTTPException:
        return None
