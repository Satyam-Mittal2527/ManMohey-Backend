import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    SUPABASE_URL: str = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_TEST_API_KEY")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_TEST_SECRET_KEY")
    KLAVIYO_PRIVATE_API_KEY: str | None = os.getenv("KLAVIYO_PRIVATE_API_KEY")
    KLAVIYO_NEWSLETTER_LIST_ID: str = os.getenv(
        "KLAVIYO_NEWSLETTER_LIST_ID",
        "XyrkBT",
    )
    KLAVIYO_API_REVISION: str = os.getenv(
        "KLAVIYO_API_REVISION",
        "2026-07-15",
    )

settings = Settings()
