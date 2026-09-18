from __future__ import annotations

from app.db.supabase_client import supabase_admin, supabase


def _to_public_url(image_url: str | None) -> str:
    if not image_url:
        return "/placeholder.png"
    try:
        return supabase.storage.from_("website-assets").get_public_url(image_url)
    except Exception:
        return "/placeholder.png"


def _normalize_product(product: dict) -> dict:
    if not product:
        return product

    product_images = product.get("product_images") or []
    for image in product_images:
        image["public_url"] = _to_public_url(image.get("image_url"))

    product["product_images"] = product_images
    return product


async def get_user_wishlist_service(user_id: str):
    try:
        response = (
            supabase_admin.table("wishlist_items")
            .select(
                "* , products(*, categories!products_category_id_fkey(id, name, slug), product_images(id, image_url, display_order))"
            )
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )

        if hasattr(response, "error") and response.error:
            raise Exception(response.error.message)

        products = []
        for item in response.data or []:
            product = item.get("products")
            if not product:
                continue
            if product.get("active") is False:
                continue
            products.append(_normalize_product(product))

        return products
    except Exception as exc:
        print(f"Get user wishlist error: {exc}")
        raise


async def add_to_wishlist_service(user_id: str, product_id: int):
    try:
        product_resp = (
            supabase_admin.table("products")
            .select("id, active")
            .eq("id", product_id)
            .eq("active", True)
            .maybe_single()
            .execute()
        )

        if hasattr(product_resp, "error") and product_resp.error:
            raise Exception(product_resp.error.message)

        if not product_resp.data:
            raise ValueError("Product not found")

        existing = (
            supabase_admin.table("wishlist_items")
            .select("id")
            .eq("user_id", user_id)
            .eq("product_id", product_id)
            .limit(1)
            .execute()
        )

        if hasattr(existing, "error") and existing.error:
            raise Exception(existing.error.message)

        if existing.data:
            return {"success": True, "message": "Product already in wishlist", "data": {"product_id": product_id, "wishlisted": True}}

        insert = (
            supabase_admin.table("wishlist_items")
            .insert({"user_id": user_id, "product_id": product_id})
            .execute()
        )

        if hasattr(insert, "error") and insert.error:
            raise Exception(insert.error.message)

        return {"success": True, "message": "Product added to wishlist", "data": {"product_id": product_id, "wishlisted": True}}
    except ValueError:
        raise
    except Exception as exc:
        print(f"Add product to wishlist error: {exc}")
        raise


async def remove_from_wishlist_service(user_id: str, product_id: int):
    try:
        response = (
            supabase_admin.table("wishlist_items")
            .delete()
            .eq("user_id", user_id)
            .eq("product_id", product_id)
            .execute()
        )

        if hasattr(response, "error") and response.error:
            raise Exception(response.error.message)

        return {"success": True, "message": "Product removed from wishlist", "data": {"product_id": product_id, "wishlisted": False}}
    except Exception as exc:
        print(f"Remove product from wishlist error: {exc}")
        raise


async def is_product_wishlisted_service(user_id: str, product_id: int):
    try:
        response = (
            supabase_admin.table("wishlist_items")
            .select("id")
            .eq("user_id", user_id)
            .eq("product_id", product_id)
            .limit(1)
            .execute()
        )

        if hasattr(response, "error") and response.error:
            raise Exception(response.error.message)

        return {"success": True, "data": {"product_id": product_id, "wishlisted": bool(response.data)}}
    except Exception as exc:
        print(f"Check product wishlist error: {exc}")
        raise
