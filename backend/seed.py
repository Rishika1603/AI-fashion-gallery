from .database import SessionLocal, engine, Base
from .models import Product
from PIL import Image
from io import BytesIO

import os
import json
import random
from pathlib import Path

try:
    from .embeddings import get_image_embedding
    have_embeddings = True
except Exception:
    have_embeddings = False

CATEGORY_MAP = {
    "Blazer": "Blazer",
    "Celana_Panjang": "Trousers",
    "Celana_Pendek": "Shorts",
    "Gaun": "Dress",
    "Hoodie": "Hoodie",
    "Jaket": "Jacket",
    "Jaket_Denim": "Denim Jacket",
    "Jaket_Olahraga": "Sport Jacket",
    "Jeans": "Jeans",
    "Kaos": "T-Shirt",
    "Kemeja": "Shirt",
    "Mantel": "Coat",
    "Polo": "Polo Shirt",
    "Rok": "Skirt",
    "Sweter": "Sweater",
}

# --- Cloudinary URL mapping ---
CLOUDINARY_MAPPING_PATH = Path(__file__).resolve().parent / "cloudinary_mapping.json"
_cloudinary_map: dict[str, str] | None = None

def _load_cloudinary_map() -> dict[str, str]:
    global _cloudinary_map
    if _cloudinary_map is None:
        if CLOUDINARY_MAPPING_PATH.exists():
            with open(CLOUDINARY_MAPPING_PATH) as f:
                _cloudinary_map = json.load(f)
            print(f"Loaded Cloudinary mapping ({len(_cloudinary_map)} URLs)")
        else:
            _cloudinary_map = {}
            print("No Cloudinary mapping found — using local file paths")
    return _cloudinary_map

def _resolve_image_url(abs_path: str) -> str:
    """Return Cloudinary URL if available, else fall back to local path."""
    mapping = _load_cloudinary_map()
    return mapping.get(abs_path, abs_path)

DATASET_ROOT = os.getenv("DATASET_DIR", "/home/rishika-vishwakarma/Projects/AI-fashion-gallery/Clothes_Dataset")
if not os.path.exists(DATASET_ROOT):
    alt = "/home/rishika-vishwakarma/Projects/AI-fashion-gallery/Clothes_Dataset_small"
    if os.path.exists(alt):
        DATASET_ROOT = alt

# Re-create tables to update schema (WARNING: Data loss if exists, ok for seed)
# In production, use Alembic migrations
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

def seed_data(limit_per_category: int | None = None):
    db = SessionLocal()

    # Check if data already exists
    if db.query(Product).first():
        print("Database already seeded.")
        return

    if not os.path.exists(DATASET_ROOT):
        print(f"Dataset directory '{DATASET_ROOT}' not found.")
        return

    categories_count = {}
    seeded = 0

    for root, dirs, files in os.walk(DATASET_ROOT):
        raw_category = os.path.basename(root)
        category = CATEGORY_MAP.get(raw_category, raw_category)
        if raw_category == "Clothes_Dataset":
            category = "Uncategorized"

        if limit_per_category and categories_count.get(category, 0) >= limit_per_category:
            continue

        for file in files:
            if not file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                continue
            if limit_per_category and categories_count.get(category, 0) >= limit_per_category:
                break

            abs_path = os.path.abspath(os.path.join(root, file))
            name = os.path.splitext(file)[0].replace("_", " ").title()
            image_url = _resolve_image_url(abs_path)

            try:
                embedding = None
                if have_embeddings:
                    with open(abs_path, "rb") as img_f:
                        image = Image.open(BytesIO(img_f.read()))
                    embedding = get_image_embedding(image)
            except Exception as e:
                print(f"Failed embedding for {abs_path}: {e}")
                embedding = None

            product = Product(
                name=name,
                style_code=f"DST-{random.randint(10000, 99999)}",
                price_min=float(random.randint(20, 100)),
                price_max=float(random.randint(110, 300)),
                image_url=image_url,
                category=category,
                color_swatches=["#000000"],
                social_label=None,
                likes=0,
                in_stock=1,
                embedding=embedding,
            )
            db.add(product)
            categories_count[category] = categories_count.get(category, 0) + 1
            seeded += 1

    db.commit()
    print(f"Database seeded successfully with {seeded} products.")

if __name__ == "__main__":
    seed_data()
