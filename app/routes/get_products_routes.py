import os
from fastapi import APIRouter, Query, Request

import app.services.getCollectionPage_service as getCollectionPage_service

router = APIRouter(prefix="/api/Products")

BASE_URL = os.getenv("BASE_URL")


@router.get("/search")
async def search_products(
    q: str = "",
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    search_term = q.strip()
    if not search_term:
        return {
            "products": [],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": 0,
                "totalPages": 0,
                "hasNextPage": False,
            },
        }

    result = getCollectionPage_service.search_products_service(search_term, page, limit)
    return result or {"products": [], "pagination": {"page": page, "limit": limit, "total": 0, "totalPages": 0, "hasNextPage": False}}


@router.get("/{collection_name}")
async def get_products(
    collection_name: str,
    request: Request,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    query_params = request.query_params
    filters = getCollectionPage_service.build_collection_page_filters(query_params)

    products = getCollectionPage_service.getCollectionPage_service(
        collection_name,
        selected_filters=filters["selected_filters"],
        selected_category_ids=filters["selected_category_ids"],
        min_price=filters["min_price"],
        max_price=filters["max_price"],
        availability=filters["availability"],
        page=page,
        limit=limit,
    )
    return {"products": products}


@router.get("/product/{product_slug}")
async def get_product_by_slug(product_slug: str):
    product = getCollectionPage_service.getProductById_service(product_slug)
    return {"product": product}


@router.get("/{collection_slug}")
async def get_collection(
    collection_slug: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    products = getCollectionPage_service.getCollectionProducts_service(collection_slug, page, limit)
    return products