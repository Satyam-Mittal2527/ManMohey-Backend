import os
from fastapi import APIRouter
import app.services.new_arrivals_service as new_arrivals_service

router = APIRouter(prefix="/api/NewArrivals")

BASE_URL = os.getenv("BASE_URL")

@router.get("/")
async def get_new_arrivals():
    products = new_arrivals_service.new_arrivals_service()
    return {
        "products": products
    }