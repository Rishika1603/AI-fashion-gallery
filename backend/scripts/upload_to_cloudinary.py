"""
Upload all dataset images to Cloudinary and save a URL mapping.

Usage:
    python -m backend.scripts.upload_to_cloudinary

Requires CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET
set in the environment or in backend/.env
"""

import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend directory
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

import cloudinary
import cloudinary.uploader

# Config
CLOUDINARY_ROOT_FOLDER = "fashion_gallery"
MAPPING_FILE = Path(__file__).resolve().parent.parent / "cloudinary_mapping.json"

# Dataset roots (same fallback logic as seed.py)
DATASET_ROOTS = [
    os.getenv("DATASET_DIR", ""),
    "/home/rishika-vishwakarma/Projects/AI-fashion-gallery/Clothes_Dataset",
    "/home/rishika-vishwakarma/Projects/AI-fashion-gallery/Clothes_Dataset_small",
]

# Category mapping (same as seed.py)
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


def find_dataset_root() -> str | None:
    for root in DATASET_ROOTS:
        if root and os.path.isdir(root):
            return root
    return None


def upload_images(dataset_root: str) -> dict[str, str]:
    """Upload all images to Cloudinary. Returns {local_abs_path: cloudinary_url}."""
    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    )

    mapping: dict[str, str] = {}
    # Load existing mapping if available (to skip already-uploaded)
    if MAPPING_FILE.exists():
        with open(MAPPING_FILE) as f:
            existing = json.load(f)
            # Only keep entries where the local file still exists
            mapping = {k: v for k, v in existing.items() if os.path.exists(k)}
        print(f"Loaded {len(mapping)} existing mappings from {MAPPING_FILE}")

    total = 0
    uploaded = 0
    skipped = 0

    for root, dirs, files in os.walk(dataset_root):
        raw_category = os.path.basename(root)
        category = CATEGORY_MAP.get(raw_category, raw_category)
        if raw_category == os.path.basename(dataset_root.rstrip("/")):
            category = "Uncategorized"

        for file in sorted(files):
            if not file.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                continue

            abs_path = os.path.abspath(os.path.join(root, file))
            total += 1

            # Skip if already mapped
            if abs_path in mapping:
                skipped += 1
                continue

            # Upload to Cloudinary in category folder
            public_id = f"{CLOUDINARY_ROOT_FOLDER}/{category}/{os.path.splitext(file)[0]}"

            try:
                result = cloudinary.uploader.upload(
                    abs_path,
                    public_id=public_id,
                    overwrite=True,
                    resource_type="image",
                )
                url = result["secure_url"]
                mapping[abs_path] = url
                uploaded += 1
                print(f"  [{uploaded}] {category}/{file} -> {url}")

                # Save mapping every 100 uploads
                if uploaded % 100 == 0:
                    with open(MAPPING_FILE, "w") as f:
                        json.dump(mapping, f, indent=2)
                    print(f"  [checkpoint] Saved {len(mapping)} mappings")

            except Exception as e:
                print(f"  [FAIL] {file}: {e}")

    # Final save
    with open(MAPPING_FILE, "w") as f:
        json.dump(mapping, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Done! Total images: {total}")
    print(f"Uploaded: {uploaded}")
    print(f"Skipped (already mapped): {skipped}")
    print(f"Mapping saved to: {MAPPING_FILE}")
    print(f"{'='*60}")

    return mapping


if __name__ == "__main__":
    dataset_root = find_dataset_root()
    if not dataset_root:
        print("ERROR: No dataset directory found. Set DATASET_DIR or ensure Clothes_Dataset exists.")
        sys.exit(1)

    print(f"Dataset root: {dataset_root}")
    print(f"Cloudinary folder: {CLOUDINARY_ROOT_FOLDER}")
    print(f"Mapping file: {MAPPING_FILE}")
    print()

    if not os.getenv("CLOUDINARY_CLOUD_NAME"):
        print("ERROR: CLOUDINARY_CLOUD_NAME not set in .env or environment")
        sys.exit(1)

    upload_images(dataset_root)
