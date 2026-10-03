import os
from fastapi import APIRouter, Request

import app.services.getCollectionPage_service as getCollectionPage_service

router = APIRouter(prefix="/api/Products")

BASE_URL = os.getenv("BASE_URL")


@router.get("/search")
async def search_products(q: str = ""):
    search_term = q.strip()
    if not search_term:
        return {"products": []}

    products = getCollectionPage_service.search_products_service(search_term)
    return {"products": products or []}


@router.get("/{collection_name}")
async def get_products(collection_name: str, request: Request):
    query_params = request.query_params
    filters = getCollectionPage_service.build_collection_page_filters(query_params)

    products = getCollectionPage_service.getCollectionPage_service(
        collection_name,
        selected_filters=filters["selected_filters"],
        selected_category_ids=filters["selected_category_ids"],
        min_price=filters["min_price"],
        max_price=filters["max_price"],
        availability=filters["availability"],
    )
    return {"products": products}


@router.get("/product/{product_slug}")
async def get_product_by_slug(product_slug: str):
    product = getCollectionPage_service.getProductById_service(product_slug)
    return {"product": product}


@router.get("/{collection_slug}")
async def get_collection(collection_slug: str):
    products = getCollectionPage_service.getCollectionProducts_service(collection_slug)
    return products