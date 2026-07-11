import os
from fastapi import APIRouter
from app.db.supabase_client import supabase, supabase_admin

router = APIRouter(prefix="/api/Home")

BASE_URL = os.getenv("BASE_URL")

@router.get("/PageHero")
def get_home_page_hero():
    response = (
        supabase_admin
        .table("home_banners")
        .select("image_path, button_link")
        .eq("is_active", True)
        .order("display_order")
        .execute()
    )
    print("Response"+str(response.data))
    images = [{}]

    for row in response.data:
        image_url = (
            supabase.storage
            .from_("website-assets")
            .get_public_url(row["image_path"])
        )
        temp_dict = {
            "image_url": image_url,
            "button_link": row["button_link"]
        }
        images.append(temp_dict)
    return {
        "images": images
    }