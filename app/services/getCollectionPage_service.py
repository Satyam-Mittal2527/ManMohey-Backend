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


def _build_review_summary(reviews: list[dict]) -> dict:
    distribution = {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0}
    total_rating = 0

    for review in reviews:
        rating_value = int(review.get("rating") or 0)
        if 1 <= rating_value <= 5:
            distribution[str(rating_value)] = distribution.get(str(rating_value), 0) + 1
            total_rating += rating_value

    total_reviews = len(reviews)
    average_rating = round(total_rating / total_reviews, 1) if total_reviews else 0.0

    return {
        "average_rating": average_rating,
        "total_reviews": total_reviews,
        "rating_distribution": distribution,
    }


def _resolve_product_id(product_identifier: str | int | None) -> int | None:
    if product_identifier is None:
        return None

    try:
        return int(product_identifier)
    except (TypeError, ValueError):
        pass

    value = str(product_identifier).strip()
    if not value:
        return None

    try:
        result = (
            supabase_admin
            .table("products")
            .select("id")
            .eq("slug", value)
            .single()
            .execute()
        )
        data = result.data or {}

        if isinstance(data, list):
            if not data:
                return None
            record = data[0]
        elif isinstance(data, dict):
            record = data
        else:
            return None

        product_id = record.get("id") if isinstance(record, dict) else None
        if product_id is None:
            return None
        return int(product_id)
    except Exception:
        return None


def get_product_reviews_service(product_identifier: str | int | None, page: int = 1, limit: int = 10):
    try:
        product_id = _resolve_product_id(product_identifier)
        if product_id is None:
            return {"reviews": [], "summary": _build_review_summary([])}

        page = max(1, int(page))
        limit = min(50, max(1, int(limit)))
        offset = (page - 1) * limit

        reviews_response = (
            supabase_admin
            .table("reviews")
            .select("id, product_id, user_id, rating, comment, is_verified_purchase, is_approved, created_at")
            .eq("product_id", product_id)
            .eq("is_approved", True)
            .order("created_at", desc=True)
            .execute()
        )

        reviews = sorted(
            reviews_response.data or [],
            key=lambda item: item.get("created_at") or "",
            reverse=True,
        )
        if not reviews:
            return {"reviews": [], "summary": _build_review_summary([])}

        visible_reviews = reviews[offset: offset + limit]
        review_ids = [review["id"] for review in visible_reviews if review.get("id")]

        images_response = {"data": []}
        if review_ids:
            images_response = (
                supabase_admin
                .table("review_images")
                .select("id, review_id, image_url, display_order")
                .in_("review_id", review_ids)
                .order("display_order")
                .execute()
            )

        images_by_review: dict[str, list[dict]] = {}
        for image in images_response.data or []:
            review_id = image.get("review_id")
            if review_id is None:
                continue
            images_by_review.setdefault(str(review_id), []).append({
                "id": image.get("id"),
                "image_url": image.get("image_url"),
                "display_order": image.get("display_order", 1),
            })

        user_ids = list({review["user_id"] for review in reviews if review.get("user_id")})
        profile_map: dict[str, dict] = {}
        if user_ids:
            profiles_response = (
                supabase_admin
                .table("profiles")
                .select("id, first_name, last_name")
                .in_("id", user_ids)
                .execute()
            )
            for profile in profiles_response.data or []:
                profile_map[str(profile.get("id"))] = profile

        formatted_reviews = []
        for review in visible_reviews:
            user_id = str(review.get("user_id") or "")
            profile = profile_map.get(user_id, {})
            first_name = profile.get("first_name") or ""
            last_name = profile.get("last_name") or ""
            display_name = " ".join(part for part in [first_name, last_name] if part).strip() or "Customer"

            review_images = sorted(
                images_by_review.get(str(review.get("id")), []),
                key=lambda item: item.get("display_order", 1) or 1,
            )

            formatted_reviews.append({
                "id": review.get("id"),
                "product_id": review.get("product_id"),
                "user_id": review.get("user_id"),
                "rating": int(review.get("rating") or 0),
                "comment": review.get("comment") or "",
                "is_verified_purchase": bool(review.get("is_verified_purchase")),
                "created_at": review.get("created_at"),
                "user": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "display_name": display_name,
                },
                "images": review_images,
            })

        return {
            "reviews": formatted_reviews,
            "summary": _build_review_summary(reviews),
        }
    except Exception as exc:
        print(f"Exception in get_product_reviews_service: {exc}")
        return {"reviews": [], "summary": _build_review_summary([])}


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