import os
from fastapi import APIRouter, Depends, Query
from app.dependencies.auth import get_current_user
from app.schemas.CartSchema import (
    AddProductCart
)
from app.services.cart_service import (
    add_product_to_cart,
    fetch_cart,
    update_cart_item_quantity,
    delete_cart_item
)

router = APIRouter(prefix="/api/cart")

BASE_URL = os.getenv("BASE_URL")

@router.post("/add")
async def addToCart(
    payload: AddProductCart,
    current_user=Depends(get_current_user)
):
    print("Received request to add product to cart:", payload)
    return await add_product_to_cart(
        current_user["access_token"],
        current_user["user_id"],
        payload
    )

@router.get("/")
async def get_cart(
    current_user=Depends(get_current_user)
):
    return await fetch_cart(
        current_user["access_token"],
        current_user["user_id"]
    )

@router.put("/{item_id}")
async def update_cart_item(
    item_id: int,
    quantity: int = Query(...),
    current_user=Depends(get_current_user)
):
    return await update_cart_item_quantity(
        current_user["access_token"],
        current_user["user_id"],
        item_id,
        quantity
    )

@router.delete("/{item_id}")
async def remove_from_cart(
    item_id: int,
    current_user=Depends(get_current_user)
):
    print(f"Delete request for item_id: {item_id}, user_id: {current_user['user_id']}")
    result = await delete_cart_item(
        current_user["access_token"],
        current_user["user_id"],
        item_id
    )
    print(f"Delete result: {result}")
    return result