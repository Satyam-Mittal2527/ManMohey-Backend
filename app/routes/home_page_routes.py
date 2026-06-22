import os
from fastapi import APIRouter

router = APIRouter(prefix="/api/Home")

BASE_URL = os.getenv("BASE_URL")

@router.get("/PageHero")
def get_home_page_hero():
    return {
        "title": "HomePage Hero Picture",
        "description": "Hero Banner for the Home Page",
        "image_url": f"{BASE_URL}/public/hero_image.webp"
    }