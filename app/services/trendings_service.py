from app.db.supabase_client import supabase, supabase_admin

def trendings_service():
    try:
        response = (
            supabase_admin
            .table("Collections")
            .select("*")
            .eq("category", "Trendings")
            .execute()
        )

        products = response.data or []

        for product in products:
            if product.get("product_image1"):
                product["image1_url"] = (
                    supabase.storage
                    .from_("website-assets")
                    .get_public_url(product["product_image1"])
                )

            if product.get("product_image2"):
                product["image2_url"] = (
                    supabase.storage
                    .from_("website-assets")
                    .get_public_url(product["product_image2"])
                )
            if product.get("product_image3"):
                product["image3_url"] = (
                    supabase.storage
                    .from_("website-assets")
                    .get_public_url(product["product_image3"])
                )

        return products

    except Exception as e:
        print(f"Exception in new_arrivals_service: {e}")
        return []