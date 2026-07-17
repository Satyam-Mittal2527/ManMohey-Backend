from app.db.supabase_client import supabase, supabase_admin

def getProducts_service(collection_name: str):
    try:
        if(collection_name == "collections"):
            response = (
                supabase_admin
                .table("Collections")
                .select("*")
                .execute()
            )
        else:
            response = (
                supabase_admin
                .table("Collections")
                .select("*")
                .eq("product", collection_name)
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
        print(f"Exception in Products_service: {e}")
        return []

def getProductById_service(product_id: str, collection_name: str):
    try:
        response = (
            supabase_admin
            .table("Collections")
            .select("*")
            .eq("id", product_id)
            .execute()
        )

        product = response.data[0] if response.data else None

        if product:
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
        product["RelatedProducts"] = getProducts_service(collection_name)
        return product

    except Exception as e:
        print(f"Exception in getProductById_service: {e}")
        return None