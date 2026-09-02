import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    SUPABASE_URL: str = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_TEST_API_KEY")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_TEST_SECRET_KEY")

settings = Settings()
