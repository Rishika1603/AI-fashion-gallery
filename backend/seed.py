from .database import SessionLocal, engine, Base
from .models import Product
from .embeddings import get_image_embedding
import requests
from PIL import Image
from io import BytesIO

# Re-create tables to update schema (WARNING: Data loss if exists, ok for seed)
# In production, use Alembic migrations
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

def seed_data():
    db = SessionLocal()
    
    # Check if data already exists
    if db.query(Product).first():
        print("Database already seeded.")
        return

    products_data = [
        {
            "name": "Oversized Graphic Hoodie",
            "style_code": "STR-2024-H01",
            "price_min": 55.0,
            "price_max": 55.0,
            "image_url": "https://images.unsplash.com/photo-1556821840-3a63f95609a7?q=80&w=2787&auto=format&fit=crop",
            "category": "Hoodies",
            "color_swatches": ["#111111", "#ffffff", "#6366f1"],
            "social_label": "Trending",
            "likes": 1240
        },
        {
            "name": "Cargo Tech Pants",
            "style_code": "TR-BT-09",
            "price_min": 85.0,
            "price_max": 95.0,
            "image_url": "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?q=80&w=2787&auto=format&fit=crop",
            "category": "Pants",
            "color_swatches": ["#1a1a1a", "#2d3436", "#00d084"],
            "social_label": "Bestseller",
            "likes": 850
        },
        {
            "name": "Retro High-Top Sneakers",
            "style_code": "SNK-VNT-88",
            "price_min": 120.0,
            "price_max": 120.0,
            "image_url": "https://images.unsplash.com/photo-1552346154-21d32810aba3?q=80&w=2670&auto=format&fit=crop",
            "category": "Footwear",
            "color_swatches": ["#ffffff", "#ff3b5c", "#111111"],
            "social_label": "Limited Edition",
            "likes": 2100
        },
        {
            "name": "Minimalist Wool Overcoat",
            "style_code": "WTR-C01",
            "price_min": 180.0,
            "price_max": 220.0,
            "image_url": "https://images.unsplash.com/photo-1539571480139-1c4e79ca5ca7?q=80&w=2787&auto=format&fit=crop",
            "category": "Outerwear",
            "color_swatches": ["#e17055", "#636e72", "#2d3436"],
            "social_label": "Editor's Choice",
            "likes": 540
        },
        {
            "name": "Distressed Denim Jacket",
            "style_code": "DNM-J02",
            "price_min": 75.0,
            "price_max": 75.0,
            "image_url": "https://images.unsplash.com/photo-1551537482-f2075a1d41f2?q=80&w=2787&auto=format&fit=crop",
            "category": "Jackets",
            "color_swatches": ["#74b9ff", "#ffffff", "#111111"],
            "social_label": "Trending",
            "likes": 920
        },
        {
            "name": "Silk Pattern Shirt",
            "style_code": "SHR-SLK-05",
            "price_min": 45.0,
            "price_max": 50.0,
            "image_url": "https://images.unsplash.com/photo-1596755094514-f87034a264c6?q=80&w=2788&auto=format&fit=crop",
            "category": "Shirts",
            "color_swatches": ["#fdcb6e", "#ffffff", "#00b894"],
            "social_label": "Popular",
            "likes": 410
        }
    ]

    for p_data in products_data:
        print(f"Processing {p_data['name']}...")
        
        # Download image for embedding
        try:
            response = requests.get(p_data["image_url"], headers={"User-Agent": "Mozilla/5.0"})
            image = Image.open(BytesIO(response.content))
            embedding = get_image_embedding(image)
        except Exception as e:
            print(f"Failed to process image for {p_data['name']}: {e}")
            embedding = None

        product = Product(
            name=p_data["name"],
            style_code=p_data["style_code"],
            price_min=p_data["price_min"],
            price_max=p_data["price_max"],
            image_url=p_data["image_url"],
            category=p_data["category"],
            color_swatches=p_data["color_swatches"],
            social_label=p_data["social_label"],
            likes=p_data["likes"],
            in_stock=1,
            embedding=embedding
        )
        db.add(product)
    
    db.commit()
    print("Database seeded successfully with embeddings.")

if __name__ == "__main__":
    seed_data()
