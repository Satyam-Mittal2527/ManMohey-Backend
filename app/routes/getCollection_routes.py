from fastapi import APIRouter

import app.services.getCollectionPage_service as getCollectionPage_service

router = APIRouter(
    prefix="/api/Collections",
    tags=["Collections"]
)


@router.get("/{collection_slug}")
async def get_collection(collection_slug: str):

    products = getCollectionPage_service.getCollectionProducts_service(
        collection_slug
    )

    return products