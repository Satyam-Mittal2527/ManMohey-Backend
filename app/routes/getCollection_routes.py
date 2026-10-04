from fastapi import APIRouter, Query

import app.services.getCollectionPage_service as getCollectionPage_service

router = APIRouter(
    prefix="/api/Collections",
    tags=["Collections"]
)


@router.get("/{collection_slug}")
async def get_collection(
    collection_slug: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    print("Getting Collection for:", collection_slug)
    products = getCollectionPage_service.getCollectionProducts_service(
        collection_slug,
        page=page,
        limit=limit,
    )

    return products