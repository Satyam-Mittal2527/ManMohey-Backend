from fastapi import HTTPException
from app.db.supabase_client import supabase, supabase_admin
from app.schemas.user_schema import UserCreate

# from supabase_auth.types import VerifyOtpParams



def register_user(user: UserCreate):
    print("Registering user in service:", user.first_name, user.last_name, user.age, user.phone_number)
    try:
        response = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password,
            "options": {
                "data": {
                    "display_name": user.first_name,
                    "last_name": user.last_name,
                    "Age": user.age,
                    "phone": user.phone_number,
                }
            }
        })
    except Exception as e:
        error_message = str(e).lower()

        if "already" in error_message:
                raise HTTPException(status_code=409, detail="Email already exists")

        raise HTTPException(status_code=400, detail="Failed to register user")

    if response.user is None:
            raise HTTPException(status_code=400, detail="Failed to register user")
        
    user_id = response.user.id
    print("User registered with ID:", user_id)

    supabase_admin.table("profiles").insert({
            "id": user_id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "age": user.age,
            "phone_number": user.phone_number,
        }).execute()
    print("User profile created for ID:", user_id)

    return {
            "status_code": 201,
            "id": user_id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "age": user.age,
            "phone_number": user.phone_number,
            "access_token": response.session.access_token if response.session else None,
            "refresh_token": response.session.refresh_token if response.session else None,
        }

def sign_otp(email: str):
    try:
        # verify user exists in profiles table before sending OTP
        try:
            profiles_resp = supabase_admin.table("profiles").select("id,email").eq("email", email).execute()
        except Exception as e:
            print("profiles query error:", e)
            raise HTTPException(status_code=500, detail="Internal error checking user profile")

        rows = getattr(profiles_resp, "data", None) or profiles_resp.data if hasattr(profiles_resp, "data") else None
        # supabase client may return dict with 'data' key or an object with .data
        if not rows or len(rows) == 0:
            raise HTTPException(status_code=404, detail="User not found. Please register first.")

        response = supabase.auth.sign_in_with_otp({
            "email": email
        })

        print(response)

        return {
            "message": "OTP sent successfully"
        }

    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=400,
            detail= str(e)
        )



def verify_otp(email: str, token: str):
    try:

        print(type(supabase.auth))
        print(type(email))
        print(type(token))
        response = supabase.auth.verify_otp({
            "email": email,
            "token": token,
            "type": "email"
        })

        print(response)

        user_info = None
        if getattr(response, "user", None):
            user = response.user
            user_info = {
                "id": getattr(user, "id", None),
                "email": getattr(user, "email", None),
                "user_metadata": getattr(user, "user_metadata", None),
            }

        return {
            "message": "OTP verified successfully",
            "access_token": response.session.access_token if response.session else None,
            "refresh_token": response.session.refresh_token if response.session else None,
            "user": user_info,
        }

    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=400,
            detail="Failed to verify OTP"
        )