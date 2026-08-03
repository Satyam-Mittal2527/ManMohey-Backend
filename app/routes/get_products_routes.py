import os
from fastapi import APIRouter
import app.services.getCollectionPage_service as getCollectionPage_service

router = APIRouter(prefix="/api/Products")

BASE_URL = os.getenv("BASE_URL")

@router.get("/{collection_name}")
async def get_products(collection_name: str):
    print(collection_name)  # e.g. "New Arrivals"

    products = getCollectionPage_service.getCollectionPage_service(collection_name)
    return {"products": products}

@router.get("/product/{product_slug}")
async def get_product_by_slug(product_slug: str):

    print("Product Slug:", product_slug)

    product = getCollectionPage_service.getProductById_service(product_slug)

    return {"product": product}