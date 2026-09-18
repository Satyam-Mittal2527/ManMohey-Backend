from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import get_current_user
from app.schemas.wishlist import WishlistItemCreate
from app.services.wishlist_service import (
    add_to_wishlist_service,
    get_user_wishlist_service,
    is_product_wishlisted_service,
    remove_from_wishlist_service,
)

router = APIRouter(prefix="/api/wishlist", tags=["Wishlist"])


@router.get("")
async def get_wishlist(current_user=Depends(get_current_user)):
    try:
        items = await get_user_wishlist_service(current_user["user_id"])
        return {"success": True, "data": items}
    except Exception as exc:
        print(f"Wishlist GET error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to fetch wishlist")


@router.post("")
async def add_wishlist_item(payload: WishlistItemCreate, current_user=Depends(get_current_user)):
    try:
        result = await add_to_wishlist_service(current_user["user_id"], payload.product_id)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        print(f"Wishlist POST error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to add to wishlist")


@router.get("/check/{product_id}")
async def check_wishlist_item(product_id: int, current_user=Depends(get_current_user)):
    try:
        result = await is_product_wishlisted_service(current_user["user_id"], product_id)
        return result
    except Exception as exc:
        print(f"Wishlist check error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to check wishlist status")


@router.delete("/{product_id}")
async def delete_wishlist_item(product_id: int, current_user=Depends(get_current_user)):
    try:
        result = await remove_from_wishlist_service(current_user["user_id"], product_id)
        return result
    except Exception as exc:
        print(f"Wishlist DELETE error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to remove from wishlist")
