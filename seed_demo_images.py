import os
import re
from dotenv import load_dotenv
from supabase import create_client
from PIL import Image, ImageDraw, ImageFont


# ============================================================
# ENVIRONMENT
# ============================================================

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

BUCKET = "review-images"


# ============================================================
# HELPERS
# ============================================================

def get_public_url(path):

    return (
        f"{SUPABASE_URL}/storage/v1/object/public/"
        f"{BUCKET}/{path}"
    )


def load_font(size, bold=False):

    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",

        "/usr/share/fonts/truetype/liberation2/"
        "LiberationSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/liberation2/"
        "LiberationSans-Regular.ttf",
    ]

    for path in font_paths:

        if os.path.exists(path):

            return ImageFont.truetype(
                path,
                size
            )

    return ImageFont.load_default()


def draw_centered_text(
    draw,
    text,
    y,
    font,
    fill
):

    bbox = draw.textbbox(
        (0, 0),
        text,
        font=font
    )

    width = bbox[2] - bbox[0]

    x = (
        600 - width
    ) // 2

    draw.text(
        (x, y),
        text,
        font=font,
        fill=fill
    )


# ============================================================
# CREATE PLACEHOLDER PNG
# ============================================================

def create_review_image(
    product_name,
    rating,
    review_number
):

    image = Image.new(
        "RGB",
        (600, 750),
        "#f8f5f0"
    )

    draw = ImageDraw.Draw(
        image
    )

    # --------------------------------------------------------
    # Fonts
    # --------------------------------------------------------

    font_header = load_font(
        26,
        bold=True
    )

    font_product = load_font(
        20,
        bold=True
    )

    font_label = load_font(
        18
    )

    font_rating = load_font(
        28
    )

    font_small = load_font(
        14
    )

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    draw_centered_text(
        draw,
        "MANMOHEY",
        30,
        font_header,
        "#333333"
    )

    # --------------------------------------------------------
    # Main image area
    # --------------------------------------------------------

    draw.rounded_rectangle(
        (70, 90, 530, 570),
        radius=25,
        fill="#eee7df"
    )

    # --------------------------------------------------------
    # Head
    # --------------------------------------------------------

    draw.ellipse(
        (255, 140, 345, 230),
        fill="#d9b39b"
    )

    # --------------------------------------------------------
    # Body / clothing
    # --------------------------------------------------------

    draw.polygon(
        [
            (235, 245),
            (365, 245),
            (420, 500),
            (300, 550),
            (180, 500)
        ],
        fill="#7c3f58"
    )

    # --------------------------------------------------------
    # Left arm
    # --------------------------------------------------------

    draw.polygon(
        [
            (235, 255),
            (165, 390),
            (200, 410),
            (270, 320)
        ],
        fill="#7c3f58"
    )

    # --------------------------------------------------------
    # Right arm
    # --------------------------------------------------------

    draw.polygon(
        [
            (365, 255),
            (435, 390),
            (400, 410),
            (330, 320)
        ],
        fill="#7c3f58"
    )

    # --------------------------------------------------------
    # Decorative pattern
    # --------------------------------------------------------

    pattern_color = "#d8b06a"

    for x, y in [
        (260, 350),
        (300, 380),
        (340, 350),
        (280, 420),
        (320, 420),
    ]:

        draw.ellipse(
            (
                x - 7,
                y - 7,
                x + 7,
                y + 7
            ),
            fill=pattern_color
        )

    # --------------------------------------------------------
    # Customer Review
    # --------------------------------------------------------

    draw_centered_text(
        draw,
        "Customer Review",
        595,
        font_label,
        "#666666"
    )

    # --------------------------------------------------------
    # Product name
    # --------------------------------------------------------

    product_text = product_name[:38]

    draw_centered_text(
        draw,
        product_text,
        630,
        font_product,
        "#222222"
    )

    # --------------------------------------------------------
    # Rating
    # --------------------------------------------------------

    stars = (
        "★" * rating
        +
        "☆" * (5 - rating)
    )

    draw_centered_text(
        draw,
        stars,
        675,
        font_rating,
        "#d8a23c"
    )

    # --------------------------------------------------------
    # Demo label
    # --------------------------------------------------------

    draw_centered_text(
        draw,
        f"Demo Review #{review_number}",
        715,
        font_small,
        "#999999"
    )

    # --------------------------------------------------------
    # Convert to PNG bytes
    # --------------------------------------------------------

    from io import BytesIO

    buffer = BytesIO()

    image.save(
        buffer,
        format="PNG"
    )

    return buffer.getvalue()


# ============================================================
# MAIN
# ============================================================

def main():

    print("Fetching reviews...")

    # --------------------------------------------------------
    # Fetch reviews with product information
    # --------------------------------------------------------

    response = (
        supabase
        .table("reviews")
        .select("""
            id,
            product_id,
            user_id,
            rating,
            comment,
            products(
                id,
                name,
                slug
            )
        """)
        .order(
            "created_at",
            desc=False
        )
        .execute()
    )

    reviews = response.data or []

    print(
        f"Found {len(reviews)} reviews"
    )

    if not reviews:

        print(
            "No reviews found."
        )

        return

    success = 0

    # ========================================================
    # PROCESS EACH REVIEW
    # ========================================================

    for index, review in enumerate(
        reviews,
        start=1
    ):

        review_id = review["id"]
        user_id = review["user_id"]
        product_id = review["product_id"]
        rating = review["rating"]

        product = review.get(
            "products"
        ) or {}

        product_name = product.get(
            "name",
            f"Product {product_id}"
        )

        print("\n================================")

        print(
            f"[{index}/{len(reviews)}] Review"
        )

        print(
            f"Product ID : {product_id}"
        )

        print(
            f"Product    : {product_name}"
        )

        print(
            f"Review ID  : {review_id}"
        )

        print(
            f"User ID    : {user_id}"
        )

        print(
            f"Rating     : {rating}"
        )

        # ----------------------------------------------------
        # Create PNG placeholder
        # ----------------------------------------------------

        image_bytes = create_review_image(
            product_name=product_name,
            rating=rating,
            review_number=index
        )

        # ----------------------------------------------------
        # Storage path
        # ----------------------------------------------------

        storage_path = (
            f"{user_id}/"
            f"{review_id}/"
            f"1.png"
        )

        print(
            f"Storage path: {storage_path}"
        )

        # ----------------------------------------------------
        # Upload to Supabase Storage
        # ----------------------------------------------------

        try:

            supabase.storage \
                .from_(BUCKET) \
                .upload(
                    storage_path,
                    image_bytes,
                    {
                        "content-type":
                            "image/png",
                        "upsert":
                            "true",
                    }
                )

        except Exception as e:

            print(
                f"  ⚠️ Upload failed, "
                f"trying update: {e}"
            )

            try:

                supabase.storage \
                    .from_(BUCKET) \
                    .update(
                        storage_path,
                        image_bytes,
                        {
                            "content-type":
                                "image/png",
                            "upsert":
                                "true",
                        }
                    )

            except Exception as upload_error:

                print(
                    f"  ❌ Upload failed: "
                    f"{upload_error}"
                )

                continue

        # ----------------------------------------------------
        # Public URL
        # ----------------------------------------------------

        public_url = get_public_url(
            storage_path
        )

        # ----------------------------------------------------
        # Remove existing DB record
        # ----------------------------------------------------

        try:

            (
                supabase
                .table("review_images")
                .delete()
                .eq(
                    "review_id",
                    review_id
                )
                .eq(
                    "display_order",
                    1
                )
                .execute()
            )

        except Exception as e:

            print(
                f"  ⚠️ Could not delete "
                f"old image record: {e}"
            )

        # ----------------------------------------------------
        # Insert database record
        # ----------------------------------------------------

        try:

            (
                supabase
                .table("review_images")
                .insert({
                    "review_id": review_id,
                    "image_path": storage_path,
                    "image_url": public_url,
                    "display_order": 1,
                })
                .execute()
            )

        except Exception as e:

            print(
                f"  ❌ Database insert failed: "
                f"{e}"
            )

            # ------------------------------------------------
            # Remove uploaded file
            # ------------------------------------------------

            try:

                supabase.storage \
                    .from_(BUCKET) \
                    .remove([
                        storage_path
                    ])

            except Exception:
                pass

            continue

        print(
            f"  ✅ Uploaded: "
            f"{storage_path}"
        )

        print(
            f"  🔗 {public_url}"
        )

        success += 1

    # ========================================================
    # SUMMARY
    # ========================================================

    print("\n================================")
    print("REVIEW IMAGE SEEDING COMPLETE")
    print("================================")

    print(
        f"Reviews processed: "
        f"{len(reviews)}"
    )

    print(
        f"Successful: "
        f"{success}"
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()