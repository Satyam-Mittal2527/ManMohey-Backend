from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4


from app.services.payment_service import create_razorpay_order

from fastapi import HTTPException

from app.db.supabase_client import (
    get_user_client,
    supabase_admin,
    supabase
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



def decrease_product_variant_stock(
    variant_id: int,
    quantity: int,
):
    response = (
        supabase_admin
        .rpc(
            "decrease_product_variant_stock",
            {
                "p_variant_id": variant_id,
                "p_quantity": quantity,
            },
        )
        .execute()
    )

    return response.data

def restore_product_variant_stock(
    variant_id: int,
    quantity: int,
):
    response = (
        supabase_admin
        .rpc(
            "restore_product_variant_stock",
            {
                "p_variant_id": variant_id,
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
    payment_method: str,
):
    client = get_user_client(token)

    # ---------------------------------------------------------
    # 1. Validate address
    # ---------------------------------------------------------

    address_response = (
        client.table("addresses")
        .select("""
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
        """)
        .eq("id", address_id)
        .eq("user_id", user_id)
        .limit(1)
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
        .select("""
            id,
            user_id,
            subtotal,
            shopper_fee,
            est_total
        """)
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
        .select("""
            id,
            shopping_list,
            product,
            variant_id,
            quantity,
            size
        """)
        .eq("shopping_list", cart_id)
        .execute()
    )

    cart_items = cart_items_response.data or []

    if not cart_items:
        raise ValueError("Your cart is empty")

    # ---------------------------------------------------------
    # 4. Validate products
    # ---------------------------------------------------------

    product_ids = list({
        item["product"]
        for item in cart_items
        if item.get("product") is not None
    })

    if not product_ids:
        raise ValueError("No valid products found in cart")

    products_response = (
        supabase_admin
        .table("products")
        .select("""
            id,
            name,
            sku,
            price,
            sale_price,
            stock,
            active
        """)
        .in_("id", product_ids)
        .execute()
    )

    products = products_response.data or []

    product_map = {
        product["id"]: product
        for product in products
    }

    # ---------------------------------------------------------
    # 5. Validate variants
    # ---------------------------------------------------------

    variant_ids = list({
        item["variant_id"]
        for item in cart_items
        if item.get("variant_id") is not None
    })

    variant_map = {}

    if variant_ids:

        variants_response = (
            supabase_admin
            .table("product_variants")
            .select("""
                id,
                product_id,
                sku,
                size,
                color,
                stock,
                price
            """)
            .in_("id", variant_ids)
            .execute()
        )

        variants = variants_response.data or []

        variant_map = {
            variant["id"]: variant
            for variant in variants
        }

    # ---------------------------------------------------------
    # 6. Validate cart and calculate order items
    # ---------------------------------------------------------

    order_items = []
    subtotal = Decimal("0.00")

    for cart_item in cart_items:

        product_id = cart_item["product"]
        variant_id = cart_item.get("variant_id")
        quantity = cart_item["quantity"]

        # -----------------------------------------------------
        # Product
        # -----------------------------------------------------

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
                f"Invalid quantity for '{product.get('name')}'"
            )

        # -----------------------------------------------------
        # Determine price + stock
        # -----------------------------------------------------

        if variant_id is not None:

            variant = variant_map.get(variant_id)

            if not variant:
                raise ValueError(
                    f"Selected variant for '{product.get('name')}' "
                    f"no longer exists"
                )

            if variant["product_id"] != product_id:
                raise ValueError(
                    "Cart variant does not belong to the product"
                )

            variant_stock = variant.get("stock")

            if (
                variant_stock is not None
                and variant_stock < quantity
            ):
                raise ValueError(
                    f"Insufficient stock for "
                    f"'{product.get('name')}' "
                    f"({variant.get('size') or 'selected variant'})"
                )

            unit_price = (
                Decimal(str(variant["price"]))
                if variant.get("price") is not None
                else _get_product_price(product)
            )

            size = (
                variant.get("size")
                or cart_item.get("size")
            )

            sku = (
                variant.get("sku")
                or product.get("sku")
            )

        else:

            # -------------------------------------------------
            # Normal product without variant
            # -------------------------------------------------

            stock = product.get("stock")

            if stock is not None and stock < quantity:
                raise ValueError(
                    f"Insufficient stock for "
                    f"'{product.get('name')}'"
                )

            unit_price = _get_product_price(product)

            size = cart_item.get("size")
            sku = product.get("sku")

        # -----------------------------------------------------
        # Calculate item subtotal
        # -----------------------------------------------------

        item_subtotal = unit_price * quantity

        subtotal += item_subtotal

        order_items.append({
            "product_id": product_id,
            "variant_id": variant_id,
            "product_name": product["name"],
            "sku": sku,
            "quantity": quantity,
            "size": size,
            "unit_price": float(unit_price),
            "subtotal": float(item_subtotal),
        })

    # ---------------------------------------------------------
    # 7. Calculate totals
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
    # 8. Create order
    # ---------------------------------------------------------

    order_number = _generate_order_number()

    order_data = {
        "user_id": user_id,
        "order_number": order_number,
        "payment_method": payment_method,

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
    # Create Razorpay order for online payment
    # ---------------------------------------------------------

    razorpay_order = None

    if payment_method == "UPI payment":

        razorpay_order = create_razorpay_order(
            amount=float(total_amount),
            receipt=order_number,
        )

        supabase_admin \
            .table("orders") \
            .update({
                "razorpay_order_id": razorpay_order["id"]
            }) \
            .eq("id", order_id) \
            .execute()

        order["razorpay_order_id"] = razorpay_order["id"]

    # ---------------------------------------------------------
    # 9. Create order items
    # ---------------------------------------------------------

    try:

        items_response = (
            supabase_admin
            .table("order_items")
            .insert([
                {
                    "order_id": order_id,
                    **item,
                }
                for item in order_items
            ])
            .execute()
        )

        if not items_response.data:
            raise ValueError(
                "Failed to create order items"
            )

        # -----------------------------------------------------
        # 10. Decrease inventory
        # -----------------------------------------------------

        for item in order_items:

            if item["variant_id"] is not None:

                decrease_product_variant_stock(
                    item["variant_id"],
                    item["quantity"],
                )

            else:

                decrease_product_stock(
                    item["product_id"],
                    item["quantity"],
                )

        # -----------------------------------------------------
        # 11. Empty cart
        # -----------------------------------------------------

        delete_cart_items = (
            supabase_admin
            .table("shopping_list_items")
            .delete()
            .eq("shopping_list", cart_id)
            .execute()
        )

        if delete_cart_items.data is None:
            raise ValueError(
                "Failed to clear cart"
            )

        # Reset cart totals
        supabase_admin \
            .table("user_shopping_list") \
            .update({
                "subtotal": 0,
                "shopper_fee": 0,
                "est_total": 0
            }) \
            .eq("id", cart_id) \
            .execute()

    except Exception as error:

        # Roll back order
        supabase_admin \
            .table("orders") \
            .delete() \
            .eq("id", order_id) \
            .execute()

        raise ValueError(
            f"Failed to complete order: {error}"
        )

    # ---------------------------------------------------------
    # 12. Return complete order
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
            variant_id,
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

    order_items = items_response.data or []

    for item in order_items:

        # ---------------------------------------------------------
        # Get product image
        # ---------------------------------------------------------

        image_response = (
            supabase_admin
            .table("product_images")
            .select(
                """
                image_url,
                display_order
                """
            )
            .eq("product_id", item["product_id"])
            .order("display_order")
            .limit(1)
            .execute()
        )

        image_url = None

        if image_response.data:

            image_path = image_response.data[0].get("image_url")

            if image_path:
                image_url = (
                    supabase
                    .storage
                    .from_("website-assets")
                    .get_public_url(image_path)
                )

        item["image"] = image_url

        # ---------------------------------------------------------
        # Get variant information
        # ---------------------------------------------------------

        variant_id = item.get("variant_id")

        if variant_id is not None:

            variant_response = (
                supabase_admin
                .table("product_variants")
                .select(
                    """
                    id,
                    size,
                    color,
                    sku,
                    price
                    """
                )
                .eq("id", variant_id)
                .limit(1)
                .execute()
            )

            if variant_response.data:

                variant = variant_response.data[0]

                item["size"] = (
                    variant.get("size")
                    or item.get("size")
                )

                item["color"] = variant.get("color")

                item["sku"] = (
                    variant.get("sku")
                    or item.get("sku")
                )

        else:

            item["color"] = None

    order["items"] = order_items

    return order

async def cancel_order_service(
    token: str,
    user_id: str,
    order_id: int,
):

    # ---------------------------------------------------------
    # 1. Find order belonging to authenticated user
    # ---------------------------------------------------------

    order_response = (
        supabase_admin
        .table("orders")
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
    # 3. Get order items
    # ---------------------------------------------------------

    items_response = (
        supabase_admin
        .table("order_items")
        .select(
            """
            product_id,
            variant_id,
            quantity,
            product_name
            """
        )
        .eq("order_id", order_id)
        .execute()
    )

    if not items_response.data:
        raise ValueError("Order items not found")

    order_items = items_response.data

    # ---------------------------------------------------------
    # 4. Restore stock
    # ---------------------------------------------------------

    try:

        for item in order_items:

            product_id = item["product_id"]
            variant_id = item.get("variant_id")
            quantity = item["quantity"]

            # -------------------------------------------------
            # Variant product
            # -------------------------------------------------

            if variant_id is not None:

                success = restore_product_variant_stock(
                    variant_id,
                    quantity,
                )

                if not success:
                    raise ValueError(
                        f"Failed to restore stock for variant "
                        f"{variant_id} "
                        f"('{item.get('product_name', 'Unknown product')}')"
                    )

            # -------------------------------------------------
            # Normal product without variant
            # -------------------------------------------------

            else:

                success = restore_product_stock(
                    product_id,
                    quantity,
                )

                if not success:
                    raise ValueError(
                        f"Failed to restore stock for product "
                        f"{product_id} "
                        f"('{item.get('product_name', 'Unknown product')}')"
                    )

        # -----------------------------------------------------
        # 5. Cancel order
        # -----------------------------------------------------

        update_response = (
            supabase_admin
            .table("orders")
            .update({
                "status": "CANCELLED"
            })
            .eq("id", order_id)
            .eq("user_id", user_id)
            .eq("status", "PENDING")
            .execute()
        )

        if not update_response.data:
            raise ValueError(
                "Failed to cancel order"
            )

        # -----------------------------------------------------
        # 6. Return cancelled order
        # -----------------------------------------------------

        return update_response.data[0]

    except Exception as error:

        # -----------------------------------------------------
        # IMPORTANT:
        # We don't change the order status here because the
        # order has not been cancelled yet.
        #
        # If stock restoration fails, the order remains PENDING.
        # -----------------------------------------------------

        raise ValueError(
            f"Failed to cancel order: {error}"
        )