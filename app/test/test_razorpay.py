from app.services.payment_service import create_razorpay_order


order = create_razorpay_order(
    amount=400,
    receipt="MMH-TEST-001"
)

print(order)