from fastapi import HTTPException
from app.db.supabase_client import supabase, supabase_admin
from app.schemas.user_schema import UserCreate
def register_user(user: UserCreate):
    print("Registering user in service:", user.email)
    try:
        # Create auth user in Supabase
        auth_response = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password,
        })
        print("Supabase auth response:", auth_response)
        if auth_response.user is None:
            raise HTTPException(
                status_code=400,
                detail="Registration failed."
            )

        user_id = auth_response.user.id
        return {
            "message": "User registered successfully",
            "user": {
                "id": user_id,
                "email": user.email,
              
            },
            "access_token": (
                auth_response.session.access_token
                if auth_response.session
                else None
            ),
            "refresh_token": (
                auth_response.session.refresh_token
                if auth_response.session
                else None
            )
        }

    except HTTPException:
        raise

    except Exception as e:
        error_message = str(e).lower()

        if "already registered" in error_message:
            raise HTTPException(
                status_code=409,
                detail="Email already registered."
            )
        print("ERROR:", repr(e))
        raise HTTPException(
                status_code=500,
                detail=f"Registration failed: {str(e)}"
        )