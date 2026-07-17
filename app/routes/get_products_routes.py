import os
from fastapi import APIRouter
import app.services.getProducts_service as get_Products_service

router = APIRouter(prefix="/api/Products")

BASE_URL = os.getenv("BASE_URL")

@router.get("/{collection_name}")
async def get_products(collection_name: str):
    print(collection_name)  # e.g. "New Arrivals"

    products = get_Products_service.getProducts_service(collection_name)
    return {"products": products}

@router.get("/{collection_name}/Product/{product_id}")
async def get_product_by_id(collection_name: str, product_id: str):
    print("Collection Name:", collection_name)
    print("Product ID:", product_id)  # e.g. "12345"
    product = get_Products_service.getProductById_service(product_id, collection_name)
    print("Fetched product:", product)

    return {"product": product}