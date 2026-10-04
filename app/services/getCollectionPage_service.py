import math

from app.db.supabase_client import supabase, supabase_admin
from app.services.filter_service import (
    get_category_filters,
    get_matching_product_ids,
    parse_selected_category_values,
    parse_selected_filter_values,
)


def _apply_price_filters(query, min_price, max_price):
    """Filter using sale price when present, otherwise regular price."""
    bounds = []
    if min_price is not None:
        bounds.append(f"gte.{float(min_price)}")
    if max_price is not None:
        bounds.append(f"lte.{float(max_price)}")

    if bounds:
        sale_bounds = ",".join(f"sale_price.{bound}" for bound in bounds)
        regular_bounds = ",".join(f"price.{bound}" for bound in bounds)
        query = query.or_(
            f"and({sale_bounds}),and(sale_price.is.null,{regular_bounds}),"
            "and(sale_price.is.null,price.is.null)"
        )

    return query


def _apply_listing_filters(query, valid_ids, parsed_filters, matching_product_ids, min_price, max_price):
    query = query.eq("active", True).in_("category_id", valid_ids)
    if parsed_filters:
        query = query.in_("id", sorted(matching_product_ids))
    return _apply_price_filters(query, min_price, max_price)


def _get_availability_product_ids(valid_ids, parsed_filters, matching_product_ids, min_price, max_price):
    """Resolve inventory filters against IDs before the paginated product query."""
    candidates = []
    offset = 0
    batch_size = 1000

    while True:
        query = supabase_admin.table("products").select("id, stock")
        query = _apply_listing_filters(
            query,
            valid_ids,
            parsed_filters,
            matching_product_ids,
            min_price,
            max_price,
        )
        response = query.order("id").range(offset, offset + batch_size - 1).execute()
        rows = response.data or []
        candidates.extend(rows)
        if len(rows) < batch_size:
            break
        offset += batch_size

    candidate_ids = [int(product["id"]) for product in candidates]
    variant_stock_ids = set()
    for start in range(0, len(candidate_ids), 500):
        variant_offset = 0
        while True:
            variants = (
                supabase_admin
                .table("product_variants")
                .select("product_id")
                .in_("product_id", candidate_ids[start:start + 500])
                .gt("stock", 0)
                .order("product_id")
                .range(variant_offset, variant_offset + 999)
                .execute()
            )
            rows = variants.data or []
            variant_stock_ids.update(int(row["product_id"]) for row in rows)
            if len(rows) < 1000:
                break
            variant_offset += 1000

    in_stock_ids = {
        int(product["id"])
        for product in candidates
        if int(product.get("stock") or 0) > 0 or int(product["id"]) in variant_stock_ids
    }
    return set(candidate_ids), in_stock_ids


def getCollectionPage_service(
    category_slug: str,
    selected_filters: dict | None = None,
    selected_category_ids: list[int] | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    availability: str | None = None,
    page: int = 1,
    limit: int = 20,
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

        page = max(1, int(page))
        limit = min(100, max(1, int(limit)))
        offset = (page - 1) * limit
        parsed_filters = selected_filters or {}
        matching_product_ids = get_matching_product_ids(parsed_filters) if parsed_filters else set()

        availability_ids = None
        if availability is not None:
            if parsed_filters and not matching_product_ids:
                availability_ids = set()
            else:
                candidate_ids, in_stock_ids = _get_availability_product_ids(
                    valid_ids,
                    parsed_filters,
                    matching_product_ids,
                    min_price,
                    max_price,
                )
                if availability == "in_stock":
                    availability_ids = in_stock_ids
                elif availability == "out_of_stock":
                    availability_ids = candidate_ids - in_stock_ids

        if (parsed_filters and not matching_product_ids) or availability_ids == set():
            raw_products = []
            total = 0
        else:
            products_query = (
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
                """, count="exact")
            )
            products_query = _apply_listing_filters(
                products_query,
                valid_ids,
                parsed_filters,
                matching_product_ids,
                min_price,
                max_price,
            )
            if availability_ids is not None:
                products_query = products_query.in_("id", sorted(availability_ids))
            products_response = (
                products_query
                .order("id", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
            raw_products = products_response.data or []
            total = products_response.count or 0

        for product in raw_products:
            for image in product.get("product_images", []):
                image["public_url"] = (
                    supabase.storage
                    .from_("website-assets")
                    .get_public_url(image["image_url"])
                )

        filters = get_category_filters(category_data["id"])
        total_pages = (total + limit - 1) // limit

        return {
            "category": category_data,
            "childCategories": child_categories,
            "filterGroups": filters,
            "products": raw_products,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": total_pages,
                "hasNextPage": page < total_pages,
            },
        }

    except Exception as e:
        print("Error fetching CollectionPage Service:", e)
        return None


def build_collection_page_filters(request_query_params) -> dict:
    selected_filters = parse_selected_filter_values(request_query_params)
    selected_category_ids = parse_selected_category_values(request_query_params)

    min_price = None
    max_price = None
    if request_query_params.get("min_price") is not None:
        try:
            min_price = float(request_query_params.get("min_price"))
            if not math.isfinite(min_price):
                min_price = None
        except ValueError:
            min_price = None

    if request_query_params.get("max_price") is not None:
        try:
            max_price = float(request_query_params.get("max_price"))
            if not math.isfinite(max_price):
                max_price = None
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

def search_products_service(search_term: str, page: int = 1, limit: int = 20):
    try:
        page = max(1, int(page))
        limit = min(100, max(1, int(limit)))
        offset = (page - 1) * limit
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
            """, count="exact")
            .ilike("name", f"%{search_term}%")
            .eq("active", True)
            .order("name")
            .order("id")
            .range(offset, offset + limit - 1)
            .execute()
        )

        for product in products.data or []:
            for image in product.get("product_images", []):
                image["public_url"] = (
                    supabase.storage
                    .from_("website-assets")
                    .get_public_url(image["image_url"])
                )

        total = products.count or 0
        total_pages = (total + limit - 1) // limit
        return {
            "products": products.data or [],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": total_pages,
                "hasNextPage": page < total_pages,
            },
        }
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

def getCollectionProducts_service(collection_slug: str, page: int = 1, limit: int = 20):

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

        page = max(1, int(page))
        limit = min(100, max(1, int(limit)))
        offset = (page - 1) * limit

        products = (
            supabase_admin
            .table("collection_products")
            .select("""
                display_order,
            product_id,

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
            """, count="exact")
            .eq("collection_id", collection_data["id"])
            .order("display_order")
            .order("product_id")
            .range(offset, offset + limit - 1)
            .execute()
        )

        formatted_products = []

        for item in products.data or []:

            product = item["products"]
            if not product:
                continue

            for image in product.get("product_images", []):

                image["public_url"] = (
                    supabase.storage
                    .from_("website-assets")
                    .get_public_url(image["image_url"])
                )

            formatted_products.append(product)

        return {
            "collection": collection_data,
            "products": formatted_products,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": products.count or 0,
                "totalPages": ((products.count or 0) + limit - 1) // limit,
                "hasNextPage": page < ((products.count or 0) + limit - 1) // limit,
            },
        }

    except Exception as e:

        print(e)

        return None