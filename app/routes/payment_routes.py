from fastapi import APIRouter, Depends, HTTPException

from app.dependencies.auth import get_current_user
from app.schemas.payment import PaymentVerify
from app.services.payment_service import verify_payment_service
from app.services.order_service import cancel_order_service


router = APIRouter(
    prefix="/api/payments",
    tags=["Payments"],
)


@router.post("/verify")
async def verify_payment(
    payload: PaymentVerify,
    current_user=Depends(get_current_user),
):

    try:

        result = verify_payment_service(
            user_id=current_user["user_id"],
            order_id=payload.order_id,
            razorpay_payment_id=payload.razorpay_payment_id,
            razorpay_order_id=payload.razorpay_order_id,
            razorpay_signature=payload.razorpay_signature,
        )

        return {
            "success": True,
            "message": "Payment verified successfully",
            "data": result,
        }

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:

        print(
            f"Payment verification error: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail="Payment verification failed",
        )

@router.patch("/cancel/{order_id}")
async def cancel_unpaid_payment(
    order_id: int,
    current_user=Depends(get_current_user),
):
    try:

        result = await cancel_order_service(
            token=current_user["access_token"],
            user_id=current_user["user_id"],
            order_id=order_id,
        )

        return {
            "success": True,
            "message": "Unpaid order cancelled successfully",
            "data": result,
        }

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:

        print(
            f"Payment cancellation error: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to cancel unpaid order",
        )