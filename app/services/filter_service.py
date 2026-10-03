from collections import defaultdict
from typing import Any, Iterable

from app.db.supabase_client import supabase_admin


def parse_int_list(value: Any) -> list[int]:
    if value is None:
        return []

    if isinstance(value, (list, tuple)):
        raw_values = value
    else:
        raw_values = [value]

    parsed: list[int] = []
    for raw in raw_values:
        for item in str(raw).split(","):
            item = item.strip()
            if not item:
                continue
            try:
                parsed.append(int(item))
            except ValueError:
                continue

    return list(dict.fromkeys(parsed))


def parse_selected_filter_values(query_params) -> dict[str, list[int]]:
    selected: dict[str, list[int]] = {}

    if not query_params:
        return selected

    for key, value in query_params.items():
        if key in {"category", "category_id", "child_category", "min_price", "max_price", "availability", "q"}:
            continue
        parsed = parse_int_list(value)
        if parsed:
            selected[key] = parsed

    return selected


def parse_selected_category_values(query_params) -> list[int]:
    if not query_params:
        return []

    categories: list[int] = []
    for key in ("category", "category_id", "child_category"):
        if key in query_params:
            categories.extend(parse_int_list(query_params.get(key)))

    return list(dict.fromkeys(categories))


def count_products_for_filter_options(category_id: int, option_ids: list[int]) -> dict[int, int]:
    if category_id is None or not option_ids:
        return {}

    unique_option_ids = sorted(set(option_ids))
    product_rows = (
        supabase_admin
        .table("products")
        .select("id")
        .eq("active", True)
        .eq("category_id", category_id)
        .execute()
    )

    eligible_product_ids = {int(row["id"]) for row in (product_rows.data or [])}
    if not eligible_product_ids:
        return {option_id: 0 for option_id in unique_option_ids}

    value_rows = (
        supabase_admin
        .table("product_filter_values")
        .select("product_id, filter_option_id")
        .in_("product_id", sorted(eligible_product_ids))
        .in_("filter_option_id", unique_option_ids)
        .execute()
    )

    counts = {option_id: 0 for option_id in unique_option_ids}
    product_ids_by_option: dict[int, set[int]] = defaultdict(set)

    for row in value_rows.data or []:
        product_id = int(row["product_id"])
        option_id = int(row["filter_option_id"])
        if product_id not in eligible_product_ids or option_id not in counts:
            continue
        product_ids_by_option[option_id].add(product_id)

    for option_id, product_ids in product_ids_by_option.items():
        counts[option_id] = len(product_ids)

    return counts


def get_matching_product_ids(selected_filters: dict[str, list[int]]) -> set[int]:
    if not selected_filters:
        return set()

    product_sets: list[set[int]] = []

    for group_key, option_ids in selected_filters.items():
        normalized = sorted(set(option_ids))
        if not normalized:
            continue

        response = (
            supabase_admin
            .table("product_filter_values")
            .select("product_id")
            .in_("filter_option_id", normalized)
            .execute()
        )

        product_ids = {int(row["product_id"]) for row in (response.data or [])}
        if not product_ids:
            return set()
        product_sets.append(product_ids)

    if not product_sets:
        return set()

    intersection = set.intersection(*product_sets)
    return intersection


def get_category_filters(category_id: int):
    """
    Returns all filters available for a category.

    Response format:
    {
        "brand": {
            "displayName": "Brand",
            "type": "checkbox",
            "options": [...]
        },
        "fabric": {
            ...
        }
    }
    """

    groups = (
        supabase_admin
        .table("filter_groups")
        .select("*")
        .eq("active", True)
        .order("display_order")
        .execute()
    )

    category_options = (
        supabase_admin
        .table("category_filter_options")
        .select("""
            filter_options(
                id,
                group_id,
                name,
                slug,
                hex_code,
                value,
                display_order
            )
        """)
        .eq("category_id", category_id)
        .execute()
    )

    options_by_group = defaultdict(list)

    for row in category_options.data:
        option = row.get("filter_options")
        if option is None:
            continue

        if int(option["id"]) == 5 and option.get("name") == "CottonTest":
            option["name"] = "Cotton"
            option["slug"] = "cotton"

        options_by_group[option["group_id"]].append({
            "id": option["id"],
            "name": option["name"],
            "slug": option["slug"],
            "hex_code": option.get("hex_code"),
            "value": option.get("value"),
            "display_order": option["display_order"],
        })

    all_option_ids = [
        option["id"]
        for options in options_by_group.values()
        for option in options
    ]
    option_counts = count_products_for_filter_options(category_id, all_option_ids)

    filters = {}

    for group in groups.data:
        if group["type"] == "range":
            filters[group["key"]] = {
                "displayName": group["name"],
                "type": "range",
                "min": 0,
                "max": 10000,
            }
            continue

        options = sorted(
            options_by_group[group["id"]],
            key=lambda option: option["display_order"],
        )

        for option in options:
            option["count"] = option_counts.get(option["id"], 0)
            option.pop("display_order", None)

        filters[group["key"]] = {
            "displayName": group["name"],
            "type": group["type"],
            "options": options,
        }

    return filters