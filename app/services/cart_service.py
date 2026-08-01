from urllib import response

from app.db.supabase_client import supabase, get_user_client


def handle_db_error(response):
    if hasattr(response, "error") and response.error:
        raise Exception(response.error.message)


async def update_cart_totals(client, cart_id):
    try:
        # Get all cart items with their product prices
        response = (
            client.table("shopping_list_items")
            .select("""
                quantity,
                Collections (
                    id,
                    product_price
                )
            """)
            .eq("shopping_list", cart_id)
            .execute()
        )

        handle_db_error(response)

        subtotal = 0

        for item in response.data:
            product = item.get("products")

            if not product:
                continue

            price = float(product["product_price"])
            quantity = item["quantity"]

            subtotal += price * quantity

        # Calculate shopper fee
        shopper_fee = round(subtotal * 0.02, 2)   # 2% fee (change if needed)

        est_total = subtotal + shopper_fee

        update = (
            client.table("user_shopping_list")
            .update({
                "subtotal": subtotal,
                "shopper_fee": shopper_fee,
                "est_total": est_total
            })
            .eq("id", cart_id)
            .execute()
        )

        handle_db_error(update)

        return {
            "subtotal": subtotal,
            "shopper_fee": shopper_fee,
            "est_total": est_total
        }

    except Exception as e:
        raise Exception(f"Failed to update cart totals: {str(e)}")
    
async def get_or_create_cart(client, user_id):
    print(user_id)
    try:
        cart = client.table("user_shopping_list") \
            .select("*") \
            .eq("user_id", user_id) \
            .limit(1) \
            .execute()

        handle_db_error(cart)

        if cart.data:
            return cart.data[0]["id"]

        new_cart = client.table("user_shopping_list") \
            .insert({
                "user_id": user_id,
                "subtotal": 0,
                "shopper_fee": 0,
                "est_total": 0
            }) \
            .execute()

        handle_db_error(new_cart)

        return new_cart.data[0]["id"]

    except Exception as e:
        raise Exception(f"Cart creation failed: {str(e)}")
    
async def add_product_to_cart(token, user_id, payload):
    # print("Adding product to cart:", payload)

    try:
        if payload.quantity <= 0:
            raise Exception("Quantity must be greater than 0")

        client = get_user_client(token)

        cart_id = await get_or_create_cart(client, user_id)
        # response = (
        #         client.table("Collections")
        #         .select("*")
        #         .execute()
        #     )

        # print(response.data)
        # ✅ Check product exists
        product = (
            client.table("Collections")
            .select("*")
            .eq("id", payload.product_id)
            .execute()
        )

        # print(product.data)

        if not product.data:
            raise Exception("Invalid product")

        # ✅ Prevent duplicate
        existing = client.table("shopping_list_items") \
            .select("*") \
            .eq("shopping_list", cart_id) \
            .eq("id", payload.product_id) \
            .eq("size", payload.size) \
            .execute()

        if existing.data:
            client.table("shopping_list_items") \
                .update({
                    "quantity": existing.data[0]["quantity"] + payload.quantity
                }) \
                .eq("id", existing.data[0]["id"]) \
                .execute()
        else:
            client.table("shopping_list_items") \
                .insert({
                    "shopping_list": cart_id,
                    "product": payload.product_id,
                    "quantity": payload.quantity,
                    "size": payload.size
                }) \
                .execute()

        await update_cart_totals(client, cart_id)

        return {"message": "Product added to cart"}

    except Exception as e:
        raise Exception(f"Add to cart failed: {str(e)}")

async def fetch_cart(token, user_id):
    client = get_user_client(token)

    # Find user's cart
    cart = (
        client.table("user_shopping_list")
        .select("id")
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )

    if cart.data is None:
        return {
            "items": [],
            "subtotal": 0,
            "total_items": 0
        }

    cart_id = cart.data["id"]

    response = (
        client.table("shopping_list_items")
        .select("""
            id,
            quantity,
            size,
            Collections(
                id,
                product_name,
                product_price,
                product_image1,
                category
            )
        """)
        .eq("shopping_list", cart_id)
        .execute()
    )

    subtotal = 0
    items = []

    for row in response.data:

        product = row["Collections"]

        subtotal += product["product_price"] * row["quantity"]

        # Get public URL for the first image
        image_url = None
        if product.get("product_image1"):
            image_url = (
                supabase.storage
                .from_("website-assets")
                .get_public_url(product["product_image1"])
            )

        items.append({
            "id": row["id"],
            "product_id": product["id"],
            "name": product["product_name"],
            "price": product["product_price"],
            "image": image_url,
            "category": product["category"],
            "quantity": row["quantity"],
            "size": row["size"]
        })

    return {
        "items": items,
        "subtotal": subtotal,
        "total_items": sum(i["quantity"] for i in items)
    }

async def update_cart_item_quantity(token, user_id, item_id, quantity):
    """Update quantity of a cart item"""
    try:
        if quantity < 1:
            raise Exception("Quantity must be at least 1")

        client = get_user_client(token)

        # Update the item quantity
        response = (
            client.table("shopping_list_items")
            .update({"quantity": quantity})
            .eq("id", item_id)
            .execute()
        )

        handle_db_error(response)

        return {"success": True, "message": "Item quantity updated"}

    except Exception as e:
        raise Exception(f"Failed to update cart item: {str(e)}")

async def delete_cart_item(token, user_id, item_id):
    """Delete an item from cart"""
    try:
        print(f"Attempting to delete item {item_id} for user {user_id}")
        client = get_user_client(token)

        # Delete the item from cart
        response = (
            client.table("shopping_list_items")
            .delete()
            .eq("id", item_id)
            .execute()
        )

        print(f"Delete response: {response}")
        handle_db_error(response)

        return {"success": True, "message": "Item removed from cart"}

    except Exception as e:
        print(f"Error in delete_cart_item: {str(e)}")
        raise Exception(f"Failed to delete cart item: {str(e)}")