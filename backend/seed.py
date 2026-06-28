from .database import SessionLocal, engine, Base
from .models import Product
from PIL import Image
from io import BytesIO
from .ingest_dataset import CATEGORY_MAP

import os
import random

try:
    from .embeddings import get_image_embedding
    have_embeddings = True
except Exception:
    have_embeddings = False

DATASET_ROOT = "/home/rishika-vishwakarma/Projects/AI-fashion-gallery/Clothes_Dataset"

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
                image_url=abs_path,
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
