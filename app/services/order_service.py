from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException

from app.db.supabase_client import (
    get_user_client,
    supabase_admin,
)

def decrease_product_stock(
    product_id: int,
    quantity: int,
):
    response = (
        supabase_admin
        .rpc(
            "decrease_product_stock",
            {
                "p_product_id": product_id,
                "p_quantity": quantity,
            },
        )
        .execute()
    )

    return response.data
def restore_product_stock(
    product_id: int,
    quantity: int,
):
    response = (
        supabase_admin
        .rpc(
            "restore_product_stock",
            {
                "p_product_id": product_id,
                "p_quantity": quantity,
            },
        )
        .execute()
    )

    return response.data


def _generate_order_number():
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    unique_part = uuid4().hex[:6].upper()

    return f"MMH-{timestamp}-{unique_part}"


def _get_product_price(product):
    """
    Use sale_price when available, otherwise regular price.
    """

    sale_price = product.get("sale_price")
    regular_price = product.get("price")

    if sale_price is not None:
        return Decimal(str(sale_price))

    if regular_price is not None:
        return Decimal(str(regular_price))

    raise ValueError(
        f"Product {product.get('id')} does not have a valid price"
    )


async def create_order_service(
    token: str,
    user_id: str,
    address_id: str,
):
    client = get_user_client(token)

    # ---------------------------------------------------------
    # 1. Validate address belongs to authenticated user
    # ---------------------------------------------------------

    address_response = (
        client.table("addresses")
        .select(
            """
            id,
            user_id,
            full_name,
            phone_number,
            address_line_1,
            address_line_2,
            city,
            state,
            postal_code,
            country
            """
        )
        .eq("id", address_id)
        .eq("user_id", user_id)
        .execute()
    )

    if not address_response.data:
        raise ValueError(
            "Address not found or does not belong to the user"
        )

    address = address_response.data[0]

    # ---------------------------------------------------------
    # 2. Get user's cart
    # ---------------------------------------------------------

    cart_response = (
        client.table("user_shopping_list")
        .select(
            """
            id,
            user_id,
            subtotal,
            shopper_fee,
            est_total
            """
        )
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    if not cart_response.data:
        raise ValueError("Cart not found")

    cart = cart_response.data[0]
    cart_id = cart["id"]

    # ---------------------------------------------------------
    # 3. Get cart items
    # ---------------------------------------------------------

    cart_items_response = (
        client.table("shopping_list_items")
        .select(
            """
            id,
            shopping_list,
            product,
            quantity,
            size
            """
        )
        .eq("shopping_list", cart_id)
        .execute()
    )

    cart_items = cart_items_response.data or []

    if not cart_items:
        raise ValueError("Your cart is empty")

    # ---------------------------------------------------------
    # 4. Get products
    # ---------------------------------------------------------

    product_ids = list(
        {
            item["product"]
            for item in cart_items
            if item.get("product") is not None
        }
    )

    if not product_ids:
        raise ValueError("No valid products found in cart")

    products_response = (
        supabase_admin
        .table("products")
        .select(
            """
            id,
            name,
            sku,
            price,
            sale_price,
            stock,
            active
            """
        )
        .in_("id", product_ids)
        .execute()
    )

    products = products_response.data or []

    product_map = {
        product["id"]: product
        for product in products
    }

    # ---------------------------------------------------------
    # 5. Validate cart and calculate order items
    # ---------------------------------------------------------

    order_items = []
    subtotal = Decimal("0.00")

    for cart_item in cart_items:

        product_id = cart_item["product"]
        quantity = cart_item["quantity"]

        product = product_map.get(product_id)

        if not product:
            raise ValueError(
                f"Product {product_id} no longer exists"
            )

        if not product.get("active"):
            raise ValueError(
                f"Product '{product.get('name')}' is no longer available"
            )

        if quantity <= 0:
            raise ValueError(
                f"Invalid quantity for product '{product.get('name')}'"
            )

        stock = product.get("stock")

        if stock is not None and stock < quantity:
            raise ValueError(
                f"Insufficient stock for '{product.get('name')}'"
            )

        unit_price = _get_product_price(product)

        item_subtotal = unit_price * quantity

        subtotal += item_subtotal

        order_items.append(
            {
                "product_id": product_id,
                "product_name": product["name"],
                "sku": product.get("sku"),
                "quantity": quantity,
                "size": cart_item.get("size"),
                "unit_price": float(unit_price),
                "subtotal": float(item_subtotal),
            }
        )

    # ---------------------------------------------------------
    # 6. Calculate totals
    # ---------------------------------------------------------

    shipping_fee = Decimal(
        str(cart.get("shopper_fee") or 0)
    )

    discount = Decimal("0.00")

    total_amount = (
        subtotal
        + shipping_fee
        - discount
    )

    if total_amount < 0:
        total_amount = Decimal("0.00")

    # ---------------------------------------------------------
    # 7. Create order
    # ---------------------------------------------------------

    order_number = _generate_order_number()

    order_data = {
        "user_id": user_id,
        "order_number": order_number,

        # Address snapshot
        "full_name": address["full_name"],
        "phone_number": address["phone_number"],
        "address_line_1": address["address_line_1"],
        "address_line_2": address.get("address_line_2"),
        "city": address["city"],
        "state": address["state"],
        "postal_code": address["postal_code"],
        "country": address["country"],

        # Pricing
        "subtotal": float(subtotal),
        "shipping_fee": float(shipping_fee),
        "discount": float(discount),
        "total_amount": float(total_amount),

        # Status
        "status": "PENDING",
        "payment_status": "PENDING",
    }

    order_response = (
        supabase_admin
        .table("orders")
        .insert(order_data)
        .execute()
    )

    if not order_response.data:
        raise ValueError(
            "Failed to create order"
        )

    order = order_response.data[0]
    order_id = order["id"]

    # ---------------------------------------------------------
    # 8. Create order items and decrease stock
    # ---------------------------------------------------------

    decreased_stock = []

    try:

        items_to_insert = [
            {
                "order_id": order_id,
                **item,
            }
            for item in order_items
        ]

        # Create order items
        items_response = (
            supabase_admin
            .table("order_items")
            .insert(items_to_insert)
            .execute()
        )

        if not items_response.data:
            raise ValueError(
                "Failed to create order items"
            )

        # -----------------------------------------------------
        # 8.5. Decrease product stock
        # -----------------------------------------------------

        for item in order_items:

            success = decrease_product_stock(
                item["product_id"],
                item["quantity"],
            )

            if not success:
                raise ValueError(
                    f"Insufficient stock for "
                    f"'{item['product_name']}'"
                )

            decreased_stock.append(
                {
                    "product_id": item["product_id"],
                    "quantity": item["quantity"],
                }
            )

    except Exception as error:

        # -----------------------------------------------------
        # Restore stock that was already decreased
        # -----------------------------------------------------

        for item in decreased_stock:

            restore_product_stock(
                item["product_id"],
                item["quantity"],
            )

        # -----------------------------------------------------
        # Delete order items
        # -----------------------------------------------------

        supabase_admin \
            .table("order_items") \
            .delete() \
            .eq("order_id", order_id) \
            .execute()

        # -----------------------------------------------------
        # Delete order
        # -----------------------------------------------------

        supabase_admin \
            .table("orders") \
            .delete() \
            .eq("id", order_id) \
            .execute()

        raise ValueError(
            f"Failed to create order: {error}"
        )

    # ---------------------------------------------------------
    # 9. Return complete order
    # ---------------------------------------------------------

    return {
        **order,
        "items": items_response.data,
    }

async def get_user_orders_service(
    token: str,
    user_id: str,
):
    client = get_user_client(token)

    orders_response = (
        client.table("orders")
        .select(
            """
            id,
            order_number,
            subtotal,
            shipping_fee,
            discount,
            total_amount,
            status,
            payment_status,
            created_at,
            updated_at
            """
        )
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )

    if not orders_response.data:
        return []

    return orders_response.data


async def get_user_order_by_id_service(
    token: str,
    user_id: str,
    order_id: int,
):
    client = get_user_client(token)

    order_response = (
        client.table("orders")
        .select("*")
        .eq("id", order_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )

    if not order_response.data:
        raise ValueError("Order not found")

    order = order_response.data

    items_response = (
        client.table("order_items")
        .select(
            """
            id,
            order_id,
            product_id,
            product_name,
            sku,
            quantity,
            size,
            unit_price,
            subtotal,
            created_at
            """
        )
        .eq("order_id", order_id)
        .execute()
    )

    order["items"] = items_response.data or []

    return order

async def cancel_order_service(
    token: str,
    user_id: str,
    order_id: int,
):
    
    # client = get_user_client(token)

    # ---------------------------------------------------------
    # 1. Find order belonging to authenticated user
    # ---------------------------------------------------------

    order_response = (
        supabase_admin.table("orders")
        .select(
            """
            id,
            order_number,
            status,
            payment_status
            """
        )
        .eq("id", order_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    print(order_response)
    if not order_response.data:
        raise ValueError("Order not found")

    order = order_response.data[0]

    # ---------------------------------------------------------
    # 2. Check whether order can be cancelled
    # ---------------------------------------------------------

    if order["status"] != "PENDING":
        raise ValueError(
            f"Order cannot be cancelled because its current "
            f"status is {order['status']}"
        )

    # ---------------------------------------------------------
    # 3. Cancel order
    # ---------------------------------------------------------

    update_response = (
        supabase_admin
        .table("orders")
        .update({
            "status": "CANCELLED"
        })
        .eq("id", order_id)
        .eq("user_id", user_id)
        .execute()
    )

    if not update_response.data:
        raise ValueError(
            "Failed to cancel order"
        )

    return update_response.data[0]