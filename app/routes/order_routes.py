from fastapi import APIRouter, Depends, HTTPException

from app.dependencies.auth import get_current_user

from app.schemas.order import OrderCreate

from app.services.order_service import (
    create_order_service,
    get_user_orders_service,
    get_user_order_by_id_service,
    cancel_order_service
)


router = APIRouter(
    prefix="/api/orders",
    tags=["Orders"],
)


@router.post("/create")
async def create_order(
    payload: OrderCreate,
    current_user=Depends(get_current_user),
):

    try:

        result = await create_order_service(
            current_user["access_token"],
            current_user["user_id"],
            payload.address_id,
            payload.payment_method
        )

        return {
            "success": True,
            "message": "Order created successfully",
            "data": result,
        }

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:

        print(
            f"Create order error: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to create order",
        )

@router.get("/")
async def get_orders(
    current_user=Depends(get_current_user),
):
    try:

        orders = await get_user_orders_service(
            current_user["access_token"],
            current_user["user_id"],
        )

        return {
            "success": True,
            "data": orders,
        }

    except Exception as e:

        print(f"Get orders error: {e}")

        raise HTTPException(
            status_code=500,
            detail="Failed to fetch orders",
        )

@router.get("/{order_id}")
async def get_order(
    order_id: int,
    current_user=Depends(get_current_user),
):
    try:

        order = await get_user_order_by_id_service(
            current_user["access_token"],
            current_user["user_id"],
            order_id,
        )

        return {
            "success": True,
            "data": order,
        }

    except ValueError as e:

        raise HTTPException(
            status_code=404,
            detail=str(e),
        )

    except Exception as e:

        print(f"Get order error: {e}")

        raise HTTPException(
            status_code=500,
            detail="Failed to fetch order",
        )

@router.patch("/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    current_user=Depends(get_current_user),
):

    try:

        result = await cancel_order_service(
            current_user["access_token"],
            current_user["user_id"],
            order_id,
        )

        return {
            "success": True,
            "message": "Order cancelled successfully",
            "data": result,
        }

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:

        print(
            f"Cancel order error: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to cancel order",
        )