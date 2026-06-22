from fastapi import APIRouter

router = APIRouter(prefix = "/api/Home")

@router.get("/PageHero")
def get_home_page_hero():
    return {
        "title": "HomePage Hero Picture",
        "description": "Hero Banner for the Home Page",
        "image_url": "http://localhost:8000/public/hero_image.webp"
    }