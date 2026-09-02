from urllib import response

from app.db.supabase_client import supabase, get_user_client, supabase_admin


def handle_db_error(response):
    if hasattr(response, "error") and response.error:
        raise Exception(response.error.message)


async def update_cart_totals(client, cart_id):
    try:

        # -----------------------------------------------------
        # Get cart items
        # -----------------------------------------------------

        response = (
            client
            .table("shopping_list_items")
            .select("""
                quantity,
                product,
                variant_id
            """)
            .eq("shopping_list", cart_id)
            .execute()
        )

        handle_db_error(response)

        subtotal = 0.0

        # -----------------------------------------------------
        # Calculate price for every cart item
        # -----------------------------------------------------

        for item in response.data or []:

            product_id = item["product"]
            variant_id = item.get("variant_id")
            quantity = item["quantity"]

            price = None

            # -------------------------------------------------
            # Variant price
            # -------------------------------------------------

            if variant_id is not None:

                variant_response = (
                    supabase
                    .table("product_variants")
                    .select("price")
                    .eq("id", variant_id)
                    .eq("product_id", product_id)
                    .limit(1)
                    .execute()
                )

                if variant_response.data:

                    variant = variant_response.data[0]

                    if variant.get("price") is not None:
                        price = float(
                            variant["price"]
                        )

            # -------------------------------------------------
            # Product price fallback
            # -------------------------------------------------

            if price is None:

                product_response = (
                    supabase
                    .table("products")
                    .select("""
                        price,
                        sale_price
                    """)
                    .eq("id", product_id)
                    .limit(1)
                    .execute()
                )

                if not product_response.data:
                    continue

                product = product_response.data[0]

                price = (
                    product.get("sale_price")
                    if product.get("sale_price") is not None
                    else product.get("price")
                )

            if price is None:
                continue

            subtotal += float(price) * quantity

        # -----------------------------------------------------
        # Shopper fee
        # -----------------------------------------------------

        shopper_fee = round(
            subtotal * 0.02,
            2
        )

        est_total = round(
            subtotal + shopper_fee,
            2
        )

        # -----------------------------------------------------
        # Update cart
        # -----------------------------------------------------

        update = (
            client
            .table("user_shopping_list")
            .update({
                "subtotal": round(subtotal, 2),
                "shopper_fee": shopper_fee,
                "est_total": est_total
            })
            .eq("id", cart_id)
            .execute()
        )

        handle_db_error(update)

        return {
            "subtotal": round(subtotal, 2),
            "shopper_fee": shopper_fee,
            "est_total": est_total
        }

    except Exception as e:

        raise Exception(
            f"Failed to update cart totals: {str(e)}"
        )
    
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
    try:
        if payload.quantity <= 0:
            raise Exception("Quantity must be greater than 0")

        client = get_user_client(token)

        # ---------------------------------------------------------
        # 1. Get / create user's cart
        # ---------------------------------------------------------

        cart_id = await get_or_create_cart(client, user_id)

        # ---------------------------------------------------------
        # 2. Validate product
        # ---------------------------------------------------------

        product_response = (
            supabase_admin
            .table("products")
            .select("""
                id,
                name,
                price,
                sale_price,
                stock,
                active
            """)
            .eq("id", payload.product_id)
            .eq("active", True)
            .limit(1)
            .execute()
        )

        handle_db_error(product_response)

        if not product_response.data:
            raise Exception("Product not found or inactive")

        product = product_response.data[0]

        if not product:
            raise Exception("Product not found or inactive")

        # ---------------------------------------------------------
        # 3. Validate variant if supplied
        # ---------------------------------------------------------

        variant = None

        if payload.variant_id is not None:

            variant_response = (
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
                .eq("id", payload.variant_id)
                .eq("product_id", payload.product_id)
                .limit(1)
                .execute()
            )

            handle_db_error(variant_response)

            if not variant_response.data:
                raise Exception("Selected variant not found")

            variant = variant_response.data[0]

            # Make sure size matches the variant
            if (
                payload.size is not None
                and variant.get("size") != payload.size
            ):
                raise Exception(
                    "Selected size does not match the variant"
                )

            # Use variant size
            size = variant.get("size")

            # Variant stock
            available_stock = variant.get("stock")

        else:
            # -----------------------------------------------------
            # Normal product without variants
            # -----------------------------------------------------

            size = payload.size
            available_stock = product.get("stock")

        # ---------------------------------------------------------
        # 4. Validate stock
        # ---------------------------------------------------------

        if available_stock is not None:

            if available_stock <= 0:
                raise Exception("Product is out of stock")

            if payload.quantity > available_stock:
                raise Exception(
                    f"Only {available_stock} item(s) available"
                )

        # ---------------------------------------------------------
        # 5. Check whether same product/variant already exists
        # ---------------------------------------------------------

        existing_query = (
            client
            .table("shopping_list_items")
            .select("""
                id,
                quantity,
                variant_id,
                size
            """)
            .eq("shopping_list", cart_id)
            .eq("product", payload.product_id)
        )

        # Variant products are identified by variant_id
        if payload.variant_id is not None:
            existing_query = existing_query.eq(
                "variant_id",
                payload.variant_id
            )

        else:
            # Non-variant products
            existing_query = existing_query.is_(
                "variant_id",
                "null"
            )

            if size is not None:
                existing_query = existing_query.eq(
                    "size",
                    size
                )
            else:
                existing_query = existing_query.is_(
                    "size",
                    "null"
                )

        existing_response = existing_query.execute()

        handle_db_error(existing_response)

        # ---------------------------------------------------------
        # 6. Add / update cart item
        # ---------------------------------------------------------

        if existing_response.data:

            existing_item = existing_response.data[0]

            new_quantity = (
                existing_item["quantity"]
                + payload.quantity
            )

            if (
                available_stock is not None
                and new_quantity > available_stock
            ):
                raise Exception(
                    f"Only {available_stock} item(s) available"
                )

            update_response = (
                client
                .table("shopping_list_items")
                .update({
                    "quantity": new_quantity
                })
                .eq("id", existing_item["id"])
                .execute()
            )

            handle_db_error(update_response)

        else:

            insert_data = {
                "shopping_list": cart_id,
                "product": payload.product_id,
                "variant_id": payload.variant_id,
                "quantity": payload.quantity,
                "size": size,
            }

            insert_response = (
                client
                .table("shopping_list_items")
                .insert(insert_data)
                .execute()
            )

            handle_db_error(insert_response)

        # ---------------------------------------------------------
        # 7. Recalculate cart totals
        # ---------------------------------------------------------

        await update_cart_totals(client, cart_id)

        return {
            "success": True,
            "message": "Product added to cart"
        }

    except Exception as e:
        raise Exception(
            f"Add to cart failed: {str(e)}"
        )

async def fetch_cart(token, user_id):
    client = get_user_client(token)

    # ---------------------------------------------------------
    # 1. Find user's cart
    # ---------------------------------------------------------

    cart_response = (
        client
        .table("user_shopping_list")
        .select("""
            id,
            subtotal,
            shopper_fee,
            est_total
        """)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    handle_db_error(cart_response)

    if not cart_response.data:
        return {
            "items": [],
            "subtotal": 0,
            "shopper_fee": 0,
            "est_total": 0,
            "total_items": 0
        }

    cart = cart_response.data[0]
    cart_id = cart["id"]

    # ---------------------------------------------------------
    # 2. Get cart items
    # ---------------------------------------------------------

    response = (
        client
        .table("shopping_list_items")
        .select("""
            id,
            product,
            variant_id,
            quantity,
            size
        """)
        .eq("shopping_list", cart_id)
        .execute()
    )

    handle_db_error(response)

    items = []

    # Calculate subtotal from actual current item prices
    calculated_subtotal = 0.0

    # ---------------------------------------------------------
    # 3. Build cart items
    # ---------------------------------------------------------

    for row in response.data or []:

        product_id = row["product"]
        variant_id = row.get("variant_id")
        quantity = row["quantity"]

        # -----------------------------------------------------
        # Get product
        # -----------------------------------------------------

        product_response = (
            supabase_admin
            .table("products")
            .select("""
                id,
                name,
                price,
                sale_price,
                sku,
                category_id
            """)
            .eq("id", product_id)
            .limit(1)
            .execute()
        )

        handle_db_error(product_response)

        if not product_response.data:
            continue

        product = product_response.data[0]

        # -----------------------------------------------------
        # Default product information
        # -----------------------------------------------------

        price = (
            product.get("sale_price")
            if product.get("sale_price") is not None
            else product.get("price")
        )

        sku = product.get("sku")
        size = row.get("size")
        color = None
        stock = None

        # -----------------------------------------------------
        # Get selected variant
        # -----------------------------------------------------

        if variant_id is not None:

            variant_response = (
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
                .eq("id", variant_id)
                .eq("product_id", product_id)
                .limit(1)
                .execute()
            )

            handle_db_error(variant_response)

            if not variant_response.data:
                raise ValueError(
                    f"Selected variant {variant_id} "
                    f"not found for product {product_id}"
                )

            variant = variant_response.data[0]

            # Variant price overrides product price
            if variant.get("price") is not None:
                price = variant["price"]

            sku = variant.get("sku") or sku
            size = variant.get("size") or size
            color = variant.get("color")
            stock = variant.get("stock")

        # -----------------------------------------------------
        # Validate price
        # -----------------------------------------------------

        if price is None:
            raise ValueError(
                f"Product '{product['name']}' has no valid price"
            )

        price = float(price)

        # -----------------------------------------------------
        # Calculate subtotal
        # -----------------------------------------------------

        item_subtotal = price * quantity
        calculated_subtotal += item_subtotal

        # -----------------------------------------------------
        # Get product image
        # -----------------------------------------------------

        image_url = None

        image_response = (
            supabase_admin
            .table("product_images")
            .select("""
                image_url,
                display_order
            """)
            .eq("product_id", product_id)
            .order("display_order")
            .limit(1)
            .execute()
        )

        handle_db_error(image_response)

        if image_response.data:

            image_path = image_response.data[0].get("image_url")

            if image_path:
                image_url = (
                    supabase
                    .storage
                    .from_("website-assets")
                    .get_public_url(image_path)
                )

        # -----------------------------------------------------
        # Add item
        # -----------------------------------------------------

        items.append({
            "id": row["id"],
            "product_id": product_id,
            "variant_id": variant_id,

            "name": product["name"],

            "price": price,
            "sku": sku,

            "image": image_url,

            "category_id": product.get("category_id"),

            "quantity": quantity,

            "size": size,
            "color": color,

            "stock": stock,

            "item_subtotal": round(item_subtotal, 2),
        })

    # ---------------------------------------------------------
    # 4. Calculate totals
    # ---------------------------------------------------------

    shopper_fee = round(
        calculated_subtotal * 0.02,
        2
    )

    est_total = round(
        calculated_subtotal + shopper_fee,
        2
    )

    # ---------------------------------------------------------
    # 5. Return cart
    # ---------------------------------------------------------

    return {
        "items": items,

        "subtotal": round(
            calculated_subtotal,
            2
        ),

        "shopper_fee": shopper_fee,

        "est_total": est_total,

        "total_items": sum(
            item["quantity"]
            for item in items
        )
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