from collections import defaultdict

from app.db.supabase_client import supabase_admin


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

    # Fetch all active filter groups
    groups = (
        supabase_admin
        .table("filter_groups")
        .select("*")
        .eq("active", True)
        .order("display_order")
        .execute()
    )

    # Fetch all filter options mapped to this category
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

    # Group options by filter group
    options_by_group = defaultdict(list)

    for row in category_options.data:

        option = row.get("filter_options")

        if option is None:
            continue

        options_by_group[option["group_id"]].append({
            "id": option["id"],
            "name": option["name"],
            "slug": option["slug"],
            "hex_code": option.get("hex_code"),
            "value": option.get("value"),
            "display_order": option["display_order"],
            "count": 0
        })

    filters = {}

    for group in groups.data:

        if group["type"] == "range":

            # For now hardcoded.
            # Later compute from products.
            filters[group["key"]] = {
                "displayName": group["name"],
                "type": "range",
                "min": 0,
                "max": 10000
            }

            continue

        options = sorted(
            options_by_group[group["id"]],
            key=lambda option: option["display_order"]
        )

        # Don't expose display_order to the frontend
        for option in options:
            option.pop("display_order", None)

        filters[group["key"]] = {
            "displayName": group["name"],
            "type": group["type"],
            "options": options
        }

    return filters