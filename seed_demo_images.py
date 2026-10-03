import os
import re
import html
import requests
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError(
        "SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is missing"
    )

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY
)

BUCKET = "website-assets"


def slugify(text):
    return re.sub(
        r"[^a-z0-9]+",
        "-",
        text.lower()
    ).strip("-")


def escape(text):
    return html.escape(text)


def create_svg(product_name, category_name):
    """
    Creates a simple demo fashion-product illustration.
    """

    name = escape(product_name)
    category = escape(category_name)

    svg = f"""<svg
        xmlns="http://www.w3.org/2000/svg"
        width="600"
        height="750"
        viewBox="0 0 600 750">

        <rect width="600" height="750" fill="#f8f5f0"/>

        <!-- Header -->
        <text
            x="300"
            y="55"
            text-anchor="middle"
            font-family="Arial, sans-serif"
            font-size="22"
            font-weight="bold"
            fill="#333">
            MANMOHEY
        </text>

        <!-- Product area -->
        <rect
            x="100"
            y="100"
            width="400"
            height="500"
            rx="20"
            fill="#eee7df"/>

        <!-- Fashion illustration -->
        <circle
            cx="300"
            cy="205"
            r="45"
            fill="#d9b39b"/>

        <path
            d="M235 270
               Q300 235 365 270
               L405 470
               Q300 535 195 470
               Z"
            fill="#7c3f58"/>

        <path
            d="M235 285
               L185 370
               L220 390
               L270 325
               Z"
            fill="#7c3f58"/>

        <path
            d="M365 285
               L415 370
               L380 390
               L330 325
               Z"
            fill="#7c3f58"/>

        <!-- Product category -->
        <text
            x="300"
            y="555"
            text-anchor="middle"
            font-family="Arial, sans-serif"
            font-size="18"
            fill="#666">
            {category}
        </text>

        <!-- Product name -->
        <text
            x="300"
            y="640"
            text-anchor="middle"
            font-family="Arial, sans-serif"
            font-size="20"
            font-weight="bold"
            fill="#222">
            {name[:38]}
        </text>

        <text
            x="300"
            y="690"
            text-anchor="middle"
            font-family="Arial, sans-serif"
            font-size="15"
            fill="#888">
            Demo Product
        </text>

    </svg>"""

    return svg


def get_public_url(path):
    return (
        f"{SUPABASE_URL}/storage/v1/object/public/"
        f"{BUCKET}/{path}"
    )


def main():

    print("Fetching products...")

    response = (
        supabase
        .table("products")
        .select("""
            id,
            name,
            slug,
            category_id,
            categories(
                id,
                name,
                slug
            )
        """)
        .eq("active", True)
        .execute()
    )

    products = response.data or []

    print(f"Found {len(products)} active products")

    success = 0

    for product in products:

        product_id = product["id"]
        product_name = product["name"]
        slug = product["slug"]

        category = product.get("categories") or {}

        category_name = category.get(
            "name",
            "Fashion"
        )

        filename = f"{slug}.svg"

        storage_path = f"products/{filename}"

        print(
            f"\n[{success + 1}/{len(products)}] "
            f"{product_name}"
        )

        # ----------------------------------------
        # Create SVG
        # ----------------------------------------

        svg_content = create_svg(
            product_name,
            category_name
        )

        svg_bytes = svg_content.encode("utf-8")

        # ----------------------------------------
        # Upload to Supabase Storage
        # ----------------------------------------

        try:

            supabase.storage \
                .from_(BUCKET) \
                .upload(
                    storage_path,
                    svg_bytes,
                    {
                        "content-type": "image/svg+xml",
                        "upsert": "true",
                    }
                )

        except Exception as e:

            # If file already exists, try update
            try:

                supabase.storage \
                    .from_(BUCKET) \
                    .update(
                        storage_path,
                        svg_bytes,
                        {
                            "content-type": "image/svg+xml",
                            "upsert": "true",
                        }
                    )

            except Exception as upload_error:

                print(
                    f"  ❌ Upload failed: "
                    f"{upload_error}"
                )

                continue

        # ----------------------------------------
        # Delete existing product image records
        # ----------------------------------------

        try:

            (
                supabase
                .table("product_images")
                .delete()
                .eq("product_id", product_id)
                .execute()
            )

        except Exception as e:

            print(
                f"  ⚠️ Could not delete old image "
                f"records: {e}"
            )

        # ----------------------------------------
        # Insert image record
        #
        # IMPORTANT:
        # Store STORAGE PATH, not public URL.
        # ----------------------------------------

        try:

            (
                supabase
                .table("product_images")
                .insert({
                    "product_id": product_id,
                    "image_url": storage_path,
                    "alt_text": product_name,
                    "display_order": 1,
                })
                .execute()
            )

        except Exception as e:

            print(
                f"  ❌ Database insert failed: {e}"
            )

            continue

        print(
            f"  ✅ Uploaded: {storage_path}"
        )

        print(
            f"  🔗 {get_public_url(storage_path)}"
        )

        success += 1

    print("\n================================")
    print("IMAGE SEEDING COMPLETE")
    print("================================")
    print(f"Products processed: {len(products)}")
    print(f"Successful: {success}")


if __name__ == "__main__":
    main()