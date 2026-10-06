import os
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile

import app.services.getCollectionPage_service as getCollectionPage_service
from app.dependencies.auth import get_current_user

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


@router.get("/product/{product_slug}/reviews")
async def get_product_reviews(product_slug: str, page: int = Query(default=1, ge=1), limit: int = Query(default=10, ge=1, le=50)):
    result = getCollectionPage_service.get_product_reviews_service(product_slug, page=page, limit=limit)
    return result or {"reviews": [], "summary": {"average_rating": 0.0, "total_reviews": 0, "rating_distribution": {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0}}}


@router.get("/{product_id}/reviews")
async def get_product_reviews_by_id(product_id: str, page: int = Query(default=1, ge=1), limit: int = Query(default=10, ge=1, le=50)):
    result = getCollectionPage_service.get_product_reviews_service(product_id, page=page, limit=limit)
    return result or {"reviews": [], "summary": {"average_rating": 0.0, "total_reviews": 0, "rating_distribution": {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0}}}


@router.post("/{product_id}/reviews")
async def create_product_review(
    product_id: int,
    rating: Annotated[int, Form(...)],
    comment: Annotated[str, Form(...)],
    images: list[UploadFile] = File(default_factory=list),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required.")

    try:
        review = getCollectionPage_service.create_product_review_service(
            product_id=product_id,
            user_id=str(user_id),
            rating=rating,
            comment=comment,
            image_files=images,
        )
    except ValueError as exc:
        message = str(exc)
        if message == "You have already reviewed this product.":
            raise HTTPException(status_code=409, detail=message) from exc
        if message == "Product not found.":
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=400, detail=message) from exc

    return {"message": "Review created successfully.", "review": review}


@router.get("/{collection_slug}")
async def get_collection(
    collection_slug: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    products = getCollectionPage_service.getCollectionProducts_service(collection_slug, page, limit)
    return products