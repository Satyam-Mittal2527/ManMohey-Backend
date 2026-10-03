from collections import defaultdict

from app.db.supabase_client import supabase, supabase_admin
from app.services.filter_service import (
    get_category_filters,
    get_matching_product_ids,
    parse_selected_category_values,
    parse_selected_filter_values,
)


def _price_for_product(product):
    if product.get("sale_price") is not None:
        return float(product.get("sale_price"))
    if product.get("price") is not None:
        return float(product.get("price"))
    return None


def _has_inventory(product, variant_stock_map):
    product_stock = product.get("stock")
    if product_stock is not None and int(product_stock) > 0:
        return True

    product_id = product.get("id")
    if product_id in variant_stock_map and variant_stock_map[product_id] > 0:
        return True

    return False


def getCollectionPage_service(
    category_slug: str,
    selected_filters: dict | None = None,
    selected_category_ids: list[int] | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    availability: str | None = None,
):
    try:
        category = (
            supabase_admin
            .table("categories")
            .select("*")
            .eq("slug", category_slug)
            .single()
            .execute()
        )

        if not category.data:
            return None

        category_data = category.data

        children = (
            supabase_admin
            .table("categories")
            .select("*")
            .eq("parent_id", category_data["id"])
            .order("display_order")
            .execute()
        )

        child_categories = children.data or []
        child_category_ids = [row["id"] for row in child_categories]
        child_category_counts: dict[int, int] = {}
        if child_category_ids:
            category_product_rows = (
                supabase_admin
                .table("products")
                .select("category_id")
                .in_("category_id", child_category_ids)
                .eq("active", True)
                .execute()
            )
            for row in category_product_rows.data or []:
                category_id = int(row["category_id"])
                child_category_counts[category_id] = child_category_counts.get(category_id, 0) + 1

        for child in child_categories:
            child["count"] = child_category_counts.get(child["id"], 0)

        selected_category_values = selected_category_ids or []
        if selected_category_values:
            valid_categories = (
                supabase_admin
                .table("categories")
                .select("id")
                .in_("id", selected_category_values)
                .execute()
            )
            valid_ids = [row["id"] for row in (valid_categories.data or [])]
        else:
            valid_ids = [category_data["id"]]

        if not valid_ids:
            valid_ids = [category_data["id"]]

        products_response = (
            supabase_admin
            .table("products")
            .select("""
                *,
                categories!products_category_id_fkey(
                    id,
                    name,
                    slug
                ),
                product_images(
                    id,
                    image_url,
                    display_order
                )
            """)
            .eq("active", True)
            .in_("category_id", valid_ids)
            .execute()
        )

        raw_products = products_response.data or []

        product_ids = [product["id"] for product in raw_products]
        variant_map: dict[int, bool] = {}
        if product_ids:
            variants_response = (
                supabase_admin
                .table("product_variants")
                .select("product_id, stock")
                .in_("product_id", product_ids)
                .execute()
            )
            for row in variants_response.data or []:
                product_id = row["product_id"]
                variant_map[product_id] = (variant_map.get(product_id, False) or (int(row.get("stock") or 0) > 0))

        parsed_filters = selected_filters or {}
        matching_product_ids = set()
        if parsed_filters:
            matching_product_ids = get_matching_product_ids(parsed_filters)

        filtered_products = []
        for product in raw_products:
            product_id = product["id"]
            if parsed_filters and product_id not in matching_product_ids:
                continue

            effective_price = _price_for_product(product)
            if min_price is not None and effective_price is not None and effective_price < float(min_price):
                continue
            if max_price is not None and effective_price is not None and effective_price > float(max_price):
                continue

            if availability is not None:
                is_in_stock = _has_inventory(product, variant_map)
                if availability == "in_stock" and not is_in_stock:
                    continue
                if availability == "out_of_stock" and is_in_stock:
                    continue

            for image in product.get("product_images", []):
                image["public_url"] = (
                    supabase.storage
                    .from_("website-assets")
                    .get_public_url(image["image_url"])
                )

            filtered_products.append(product)

        filters = get_category_filters(category_data["id"])

        return {
            "category": category_data,
            "childCategories": child_categories,
            "filterGroups": filters,
            "products": filtered_products,
        }

    except Exception as e:
        print("Error fetching CollectionPage Service:", e)
        return None


def build_collection_page_filters(request_query_params) -> dict:
    selected_filters = parse_selected_filter_values(request_query_params)
    selected_category_ids = parse_selected_category_values(request_query_params)

    min_price = None
    max_price = None
    if request_query_params.get("min_price"):
        try:
            min_price = float(request_query_params.get("min_price"))
        except ValueError:
            min_price = None

    if request_query_params.get("max_price"):
        try:
            max_price = float(request_query_params.get("max_price"))
        except ValueError:
            max_price = None

    availability = request_query_params.get("availability")
    if availability not in {"in_stock", "out_of_stock"}:
        availability = None

    return {
        "selected_filters": selected_filters,
        "selected_category_ids": selected_category_ids,
        "min_price": min_price,
        "max_price": max_price,
        "availability": availability,
    }

def search_products_service(search_term: str):
    try:
        products = (
            supabase_admin
            .table("products")
            .select("""
                *,
                categories!products_category_id_fkey(
                    id,
                    name,
                    slug
                ),
                product_images(
                    id,
                    image_url,
                    display_order
                )
            """)
            .ilike("name", f"%{search_term}%")
            .eq("active", True)
            .order("name")
            .limit(48)
            .execute()
        )

        for product in products.data or []:
            for image in product.get("product_images", []):
                image["public_url"] = (
                    supabase.storage
                    .from_("website-assets")
                    .get_public_url(image["image_url"])
                )

        return products.data or []
    except Exception as e:
        print("Error searching products:", e)
        return None

def getProductById_service(product_slug: str):
    try:

        # ---------------------------------------------------------
        # 1. Get product
        # ---------------------------------------------------------

        response = (
            supabase_admin
            .table("products")
            .select("""
                *,
                categories!products_category_id_fkey(
                    id,
                    name,
                    slug
                ),
                product_images(
                    id,
                    image_url,
                    display_order
                )
            """)
            .eq("slug", product_slug)
            .eq("active", True)
            .single()
            .execute()
        )

        if not response.data:
            return None

        product = response.data

        # ---------------------------------------------------------
        # 2. Generate public image URLs
        # ---------------------------------------------------------

        for image in product.get("product_images", []):

            image["public_url"] = (
                supabase.storage
                .from_("website-assets")
                .get_public_url(image["image_url"])
            )

        # ---------------------------------------------------------
        # 3. Get product variants
        # ---------------------------------------------------------

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
            .eq("product_id", product["id"])
            .order("id")
            .execute()
        )

        product["variants"] = variants_response.data or []

        # ---------------------------------------------------------
        # 4. Related products
        # ---------------------------------------------------------

        related = (
            supabase_admin
            .table("products")
            .select("""
                *,
                product_images(
                    id,
                    image_url,
                    display_order
                )
            """)
            .eq("category_id", product["category_id"])
            .neq("id", product["id"])
            .eq("active", True)
            .limit(8)
            .execute()
        )

        for item in related.data:

            for image in item.get("product_images", []):

                image["public_url"] = (
                    supabase.storage
                    .from_("website-assets")
                    .get_public_url(image["image_url"])
                )

        product["RelatedProducts"] = related.data

        # ---------------------------------------------------------
        # 5. Return product
        # ---------------------------------------------------------

        return product

    except Exception as e:

        print(
            f"Exception in getProductById_service: {e}"
        )

        return None

def getCollectionProducts_service(collection_slug: str):

    try:

        collection = (
            supabase_admin
            .table("collections")
            .select("*")
            .eq("slug", collection_slug)
            .eq("active", True)
            .single()
            .execute()
        )

        if not collection.data:
            return None

        collection_data = collection.data

        products = (
            supabase_admin
            .table("collection_products")
            .select("""
                display_order,

                products(
                    id,
                    name,
                    slug,
                    price,
                    sale_price,
                    featured,
                    stock,

                    categories!products_category_id_fkey(
                        id,
                        name,
                        slug
                    ),

                    product_images(
                        id,
                        image_url,
                        display_order
                    )
                )
            """)
            .eq("collection_id", collection_data["id"])
            .order("display_order")
            .execute()
        )

        formatted_products = []

        for item in products.data:

            product = item["products"]

            for image in product["product_images"]:

                image["public_url"] = (
                    supabase.storage
                    .from_("website-assets")
                    .get_public_url(image["image_url"])
                )

            formatted_products.append(product)

        return {
            "collection": collection_data,
            "products": formatted_products
        }

    except Exception as e:

        print(e)

        return None