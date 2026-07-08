"""
Update remaining local-path image_urls in the DB with Cloudinary URLs.

Run this after cloudinary_mapping.json has been fully populated by
the background upload script.

Usage:
    python -m backend.scripts.fix_cloudinary_urls

Scans all products in the DB whose image_url is a local file path
and replaces them with the Cloudinary URL from the mapping file.
"""

import os
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DATASET_DIR", "")

from database import SessionLocal
from models import Product

MAPPING_PATH = Path(__file__).resolve().parent.parent / "cloudinary_mapping.json"


def fix_urls(dry_run: bool = False) -> int:
    if not MAPPING_PATH.exists():
        print(f"Mapping file not found: {MAPPING_PATH}")
        return 0

    with open(MAPPING_PATH) as f:
        mapping: dict[str, str] = json.load(f)

    print(f"Loaded {len(mapping)} Cloudinary URLs from mapping file")

    db = SessionLocal()
    try:
        products = db.query(Product).all()
        fixed = 0
        skipped = 0

        for p in products:
            # If it's already a URL (starts with http), skip
            if p.image_url and p.image_url.startswith("http"):
                skipped += 1
                continue

            # Try to resolve from mapping
            cloud_url = mapping.get(p.image_url)
            if cloud_url:
                if not dry_run:
                    p.image_url = cloud_url
                fixed += 1
            else:
                skipped += 1

        if not dry_run:
            db.commit()

        print(f"Fixed: {fixed} products")
        print(f"Skipped (already URL or no mapping): {skipped}")
        print(f"Total scanned: {fixed + skipped}")
        return fixed
    finally:
        db.close()


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    fixed = fix_urls(dry_run=dry)
    if dry:
        print(f"\nDry-run mode. Run without --dry-run to apply changes.")
    else:
        print(f"\nDone! {fixed} products updated to Cloudinary URLs.")
