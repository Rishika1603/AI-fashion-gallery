"""Rebuild the product catalog from the bundled Cloudinary URL mapping.

The original catalog was seeded from the ``Clothes_Dataset`` folder, which is
far too large to ship in a container image. ``cloudinary_mapping.json`` already
contains every product image hosted on Cloudinary, so the catalog can be
rebuilt from it alone — no dataset, no local image files, no embeddings.

The script is idempotent: it only seeds when the products table is empty.

Usage:
    python -m backend.seed_from_mapping [--force]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from .database import Base, SessionLocal, engine
from .models import Product

MAPPING_PATH = Path(__file__).resolve().parent / "cloudinary_mapping.json"

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

COLOR_PALETTE = [
    "#0f172a",
    "#1e293b",
    "#334155",
    "#475569",
    "#64748b",
    "#94a3b8",
    "#111827",
    "#312e81",
    "#4c1d95",
    "#7c2d12",
    "#3f6212",
    "#134e4a",
]


def _normalize_key(path: str) -> tuple[str, str]:
    """Return ``(category, filename)`` for any of the mapping's key shapes.

    The mapping stores the same file three times: as an absolute path, as
    ``<Category>/<file>`` and as a bare filename. All three collapse to the
    same ``(category, filename)`` pair so each product is seeded once.
    """
    normalized = path.replace("\\", "/")
    if "Clothes_Dataset/" in normalized:
        normalized = normalized.split("Clothes_Dataset/", 1)[1]
    normalized = normalized.lstrip("/")

    parts = [part for part in normalized.split("/") if part]
    if not parts:
        return "", ""
    if len(parts) >= 2:
        return parts[-2], parts[-1]
    return "", parts[-1]


def build_catalog(mapping: dict[str, str]) -> list[dict]:
    # Pass 1: resolve a category for every filename seen under a category
    # folder. The mapping also stores bare filenames, which carry no category.
    filename_to_category: dict[str, str] = {}
    for path in mapping:
        category, filename = _normalize_key(path)
        if category and filename:
            filename_to_category.setdefault(filename, category)

    catalog: dict[tuple[str, str], dict] = {}

    for path, url in mapping.items():
        category, filename = _normalize_key(path)
        if not filename or not url:
            continue

        if not category:
            category = filename_to_category.get(filename, "")

        key = (category, filename)
        if key in catalog:
            continue

        raw_category = category or "Uncategorized"
        digest = hashlib.md5(f"{raw_category}/{filename}".encode()).hexdigest()

        stem = Path(filename).stem.replace("_", " ").title()
        price_min = float(20 + int(digest[8:12], 16) % 80)
        price_max = price_min + float(10 + int(digest[12:16], 16) % 190)
        swatch = COLOR_PALETTE[int(digest[16:18], 16) % len(COLOR_PALETTE)]

        catalog[key] = {
            "name": stem,
            "style_code": f"DST-{int(digest[:8], 16) % 90000 + 10000}",
            "price_min": price_min,
            "price_max": price_max,
            "image_url": url,
            "category": CATEGORY_MAP.get(raw_category, raw_category),
            "color_swatches": [swatch],
            "social_label": None,
            "likes": int(digest[20:24], 16) % 500,
            "in_stock": 1,
            "embedding": None,
        }

    return list(catalog.values())


def seed(force: bool = False) -> int:
    if not MAPPING_PATH.exists():
        print(f"ERROR: mapping not found at {MAPPING_PATH}", file=sys.stderr)
        return 0

    Base.metadata.create_all(bind=engine)
    session = SessionLocal()

    try:
        existing = session.query(Product).count()
        if existing and not force:
            print(f"Catalog already present ({existing} products) — skipping seed.")
            return existing

        if force and existing:
            print(f"Removing {existing} existing products (--force)...")
            session.query(Product).delete()
            session.commit()

        mapping = json.loads(MAPPING_PATH.read_text())
        products = build_catalog(mapping)
        session.bulk_save_objects([Product(**item) for item in products])
        session.commit()

        print(f"Seeded {len(products)} products into {engine.url}")
        return len(products)
    finally:
        session.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force", action="store_true", help="re-seed even if products already exist"
    )
    args = parser.parse_args()
    seed(force=args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
