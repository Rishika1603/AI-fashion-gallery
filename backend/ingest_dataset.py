import os
import random
import hashlib
import json
from PIL import Image
from backend.embeddings import get_image_embedding
from backend.vector_store import upsert_vectors, delete_index

DATASET_ROOT = os.getenv("DATASET_DIR", "/home/rishika-vishwakarma/Projects/AI-fashion-gallery/Clothes_Dataset")
if not os.path.exists(DATASET_ROOT):
    alt = "/home/rishika-vishwakarma/Projects/AI-fashion-gallery/Clothes_Dataset_small"
    if os.path.exists(alt):
        DATASET_ROOT = alt

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
    "Sweter": "Sweater"
}

def clean_pinecone():
    print("Deleting existing index to start fresh...")
    delete_index()
    # vector_store.get_index will auto-recreate it when called next

def ingest_data(sample_limit=None):
    if not os.path.exists(DATASET_ROOT):
        print(f"Dataset directory '{DATASET_ROOT}' not found.")
        return

    count = 0
    pinecone_batch = []
    
    print(f"Scanning {DATASET_ROOT}...")
    
    # Track counts per category for sampling
    category_counts = {}

    for root, dirs, files in os.walk(DATASET_ROOT):
        # Infer category
        raw_category = os.path.basename(root)
        category = CATEGORY_MAP.get(raw_category, raw_category)
        if raw_category == "Clothes_Dataset":
            category = "Uncategorized"
            
        if sample_limit and category_counts.get(category, 0) >= sample_limit:
            continue

        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                if sample_limit and category_counts.get(category, 0) >= sample_limit:
                    break
                
                file_path = os.path.join(root, file)
                print(f"Processing {file} ({category})...")
                
                try:
                    # Generate embedding
                    image = Image.open(file_path)
                    embedding = get_image_embedding(image)
                    
                    if not embedding:
                        print(f"Skipping {file}: Empty embedding")
                        continue

                    # Create deterministic metadata
                    name = os.path.splitext(file)[0].replace("_", " ").title()
                    abs_path = os.path.abspath(file_path)
                    
                    # Generate deterministic ID
                    product_id = hashlib.md5(abs_path.encode()).hexdigest()
                    
                    # Metadata for Pinecone
                    metadata = {
                        "name": name,
                        "category": category,
                        "style_code": f"DST-{random.randint(10000, 99999)}",
                        "price_min": float(random.randint(20, 100)),
                        "price_max": float(random.randint(110, 300)),
                        "image_url": abs_path, 
                        "in_stock": 1,
                        "likes": 0,
                        "color_swatches": json.dumps(["#000000"])
                    }

                    # Add to Pinecone batch
                    pinecone_batch.append((
                        product_id,
                        embedding,
                        metadata
                    ))
                    
                    count += 1
                    category_counts[category] = category_counts.get(category, 0) + 1
                    
                    # Upsert to Pinecone every 20 items
                    if len(pinecone_batch) >= 20:
                        upsert_vectors(pinecone_batch)
                        pinecone_batch = []
                        print(f"Upserted {count} items...")
                        
                except Exception as e:
                    print(f"Error processing {file}: {e}")

    # Upsert remaining
    if pinecone_batch:
        upsert_vectors(pinecone_batch)

    print(f"Ingestion complete. Indexed {count} products.")

if __name__ == "__main__":
    # To run a full ingestion, remove clean_pinecone() or keep it for fresh start
    # To run a sample, use ingest_data(sample_limit=10)
    # clean_pinecone() 
    ingest_data(sample_limit=10) # Run sample of 10 per category
