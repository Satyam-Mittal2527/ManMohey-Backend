import os
from fastapi import APIRouter
import app.services.trendings_service as trendings_service

router = APIRouter(prefix="/api/Trendings")

BASE_URL = os.getenv("BASE_URL")

@router.get("/")
async def get_trendings():
    products = trendings_service.trendings_service()
    return {
        "products": products
    }