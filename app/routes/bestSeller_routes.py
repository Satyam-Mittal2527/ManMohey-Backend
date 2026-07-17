import os
from fastapi import APIRouter
import app.services.bestSeller_service as best_seller_service

router = APIRouter(prefix="/api/BestSellers")

BASE_URL = os.getenv("BASE_URL")

@router.get("/")
async def get_best_sellers():
    products = best_seller_service.bestSeller_service()
    return {
        "products": products
    }