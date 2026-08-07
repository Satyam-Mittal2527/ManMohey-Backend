from app.db.supabase_client import supabase, supabase_admin
from app.services.filter_service import get_category_filters
from typing import List

def getCollectionPage_service(category_slug: str):

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
            .eq("category_id", category_data["id"])
            .eq("active", True)
            .execute()
        )
    
        
        for product in products.data:

            for image in product["product_images"]:

                image["public_url"] = (
                    supabase.storage
                    .from_("website-assets")
                    .get_public_url(image["image_url"])
                )
                
        filters = get_category_filters(category_data["id"])
        
        return {

            "category": category_data,

            "childCategories": children.data,

            "filterGroups": filters,

            "products": products.data

        }

    except Exception as e:

        print("Error fetching CollectionPage Service:",e)

        return None

def getProductById_service(product_slug: str):
    try:

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

        # Generate public URLs
        for image in product["product_images"]:
            image["public_url"] = (
                supabase.storage
                .from_("website-assets")
                .get_public_url(image["image_url"])
            )

        # Related products
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

            for image in item["product_images"]:
                image["public_url"] = (
                    supabase.storage
                    .from_("website-assets")
                    .get_public_url(image["image_url"])
                )

        product["RelatedProducts"] = related.data

        return product

    except Exception as e:
        print(f"Exception in getProductById_service: {e}")
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