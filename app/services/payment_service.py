import razorpay

from app.core.config import settings
from app.db.supabase_client import supabase_admin

razorpay_client = razorpay.Client(
    auth=(
        settings.RAZORPAY_KEY_ID,
        settings.RAZORPAY_KEY_SECRET
    )
)


def create_razorpay_order(
    amount: float,
    receipt: str
):
    amount_in_paise = int(round(amount * 100))

    razorpay_order = razorpay_client.order.create({
        "amount": amount_in_paise,
        "currency": "INR",
        "receipt": receipt,
    })

    return razorpay_order


def verify_razorpay_payment(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str
):
    razorpay_client.utility.verify_payment_signature({
        "razorpay_order_id": razorpay_order_id,
        "razorpay_payment_id": razorpay_payment_id,
        "razorpay_signature": razorpay_signature,
    })

    return True

def verify_payment_service(
    user_id: str,
    order_id: int,
    razorpay_payment_id: str,
    razorpay_order_id: str,
    razorpay_signature: str,
):
    # ---------------------------------------------------------
    # 1. Get the ManMohey order
    # ---------------------------------------------------------

    order_response = (
        supabase_admin
        .table("orders")
        .select("""
            id,
            user_id,
            order_number,
            total_amount,
            status,
            payment_status,
            payment_method,
            razorpay_order_id
        """)
        .eq("id", order_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    if not order_response.data:
        raise ValueError("Order not found")

    order = order_response.data[0]

    # ---------------------------------------------------------
    # 2. Check Razorpay order belongs to this ManMohey order
    # ---------------------------------------------------------

    if order.get("razorpay_order_id") != razorpay_order_id:
        raise ValueError(
            "Razorpay order does not match the ManMohey order"
        )

    # ---------------------------------------------------------
    # 3. Verify Razorpay signature
    # ---------------------------------------------------------

    verify_razorpay_payment(
        razorpay_order_id=razorpay_order_id,
        razorpay_payment_id=razorpay_payment_id,
        razorpay_signature=razorpay_signature,
    )

    # ---------------------------------------------------------
    # 4. Mark order as paid and confirmed
    # ---------------------------------------------------------

    update_response = (
        supabase_admin
        .table("orders")
        .update({
            "payment_status": "PAID",
            "status": "CONFIRMED",
        })
        .eq("id", order_id)
        .eq("user_id", user_id)
        .execute()
    )

    if not update_response.data:
        raise ValueError(
            "Failed to update order payment status"
        )

    return update_response.data[0]