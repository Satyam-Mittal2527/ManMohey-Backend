from fastapi import APIRouter

router = APIRouter(prefix = "/api/Home")

@router.get("/PageHero")
def get_home_page_hero():
    return {
        "title": "HomePage Hero Picture",
        "description": "Hero Banner for the Home Page",
        "image_url": "https://images.unsplash.com/photo-1512436991641-6745cdb1723f?auto=format&fit=crop&w=1200&q=80"
    }