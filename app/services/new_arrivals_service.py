from app.db.supabase_client import supabase, supabase_admin

# Products = [
#     {
#         "ProductId": "Saree%201",
#         "Product_name": "Silk Saree 1",
#         "Product_price": "$400",
#         "Product_image": "/Test_saree.png",
#         "Product_images": ["/saree_icon.png", "/Test_saree.png", "/Test_saree.png"]
#     },
#     {
#         "ProductId": "Saree%202",
#         "Product_name": "Silk Saree 2",
#         "Product_price": "$500",
#         "Product_image": "/Test_saree.png",
#         "Product_images": ["/Test_saree.png", "/Test_saree.png"]
#     },
#     {
#         "ProductId": "Saree%203",
#         "Product_name": "Silk Saree 3",
#         "Product_price": "$600",
#         "Product_image": "/Test_saree.png",
#         "Product_images": ["/Test_saree.png", "/Test_saree.png"]
#     },
#     {
#         "ProductId": "Saree%204",
#         "Product_name": "Silk Saree 4",
#         "Product_price": "8400",
#         "Product_image": "/Test_saree.png",
#         "Product_images": ["/Test_saree.png", "/Test_saree.png"]
#     },
#     {
#         "ProductId": "Kurti%202",
#         "Product_name": "Kurti 2",
#         "Product_price": "8400",
#         "Product_image": "/Test_saree.png",
#         "Product_images": ["/Test_saree.png", "/Test_saree.png"]
#     },
#     {
#         "ProductId": "Saree%201",
#         "Product_name": "Silk Saree 1",
#         "Product_price": "$400",
#         "Product_image": "/Test_saree.png",
#         "Product_images": ["/saree_icon.png", "/Test_saree.png", "/Test_saree.png"]
#     },
#     {
#         "ProductId": "Saree%202",
#         "Product_name": "Silk Saree 2",
#         "Product_price": "$500",
#         "Product_image": "/Test_saree.png",
#         "Product_images": ["/Test_saree.png", "/Test_saree.png"]
#     },
#     {
#         "ProductId": "Saree%203",
#         "Product_name": "Silk Saree 3",
#         "Product_price": "$600",
#         "Product_image": "/Test_saree.png",
#         "Product_images": ["/Test_saree.png", "/Test_saree.png"]
#     },
#     {
#         "ProductId": "Saree%204",
#         "Product_name": "Silk Saree 4",
#         "Product_price": "8400",
#         "Product_image": "/Test_saree.png",
#         "Product_images": ["/Test_saree.png", "/Test_saree.png"]
#     },
#     {
#         "ProductId": "Kurti%202",
#         "Product_name": "Kurti 2",
#         "Product_price": "8400",
#         "Product_image": "/Test_saree.png",
#         "Product_images": ["/Test_saree.png", "/Test_saree.png"]
#     },
#     {
#         "ProductId": "Saree%201",
#         "Product_name": "Silk Saree 1",
#         "Product_price": "$400",
#         "Product_image": "/Test_saree.png",
#         "Product_images": ["/saree_icon.png", "/Test_saree.png", "/Test_saree.png"]
#     },
#     {
#         "ProductId": "Saree%202",
#         "Product_name": "Silk Saree 2",
#         "Product_price": "$500",
#         "Product_image": "/Test_saree.png",
#         "Product_images": ["/Test_saree.png", "/Test_saree.png"]
#     },
#     {
#         "ProductId": "Saree%203",
#         "Product_name": "Silk Saree 3",
#         "Product_price": "$600",
#         "Product_image": "/Test_saree.png",
#         "Product_images": ["/Test_saree.png", "/Test_saree.png"]
#     },
#     {
#         "ProductId": "Saree%204",
#         "Product_name": "Silk Saree 4",
#         "Product_price": "8400",
#         "Product_image": "/Test_saree.png",
#         "Product_images": ["/Test_saree.png", "/Test_saree.png"]
#     },
#     {
#         "ProductId": "Kurti%202",
#         "Product_name": "Kurti 2",
#         "Product_price": "8400",
#         "Product_image": "/Test_saree.png",
#         "Product_images": ["/Test_saree.png", "/Test_saree.png"]
#     }
# ]


def new_arrivals_service():
    try:
        response = (
            supabase_admin
            .table("NewArrivals")
            .select("*")
            .execute()
        )

        products = response.data or []

        for product in products:
            if product.get("product_image_path1"):
                product["image1_url"] = (
                    supabase.storage
                    .from_("website-assets")
                    .get_public_url(product["product_image_path1"])
                )

            if product.get("product_image_path2"):
                product["image2_url"] = (
                    supabase.storage
                    .from_("website-assets")
                    .get_public_url(product["product_image_path2"])
                )

        return products

    except Exception as e:
        print(f"Exception in new_arrivals_service: {e}")
        return []