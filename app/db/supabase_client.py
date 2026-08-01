from supabase import create_client
from app.core.config import settings

supabase = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_ANON_KEY
)

supabase_admin = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_ROLE_KEY
)

def get_user_client(access_token: str):
    client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_ANON_KEY
    )

    client.postgrest.auth(access_token)
    return client