import os
import json
import uuid
import logging
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, Request, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Load environment variables from .env file in the same directory
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

from datetime import datetime
from typing import List, Optional
import io

# Database imports
from .database import engine, Base, get_db
from .models import Product, ChatMessage
from .schemas import (
    ProductSchema,
    SearchResult,
    PaginatedProducts,
    ChatHistoryResponse,
)
from pydantic import BaseModel
from PIL import Image

from fastapi.staticfiles import StaticFiles

# Structured logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Fashion AI Gallery API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
DATASET_DIR = "/home/rishika-vishwakarma/Projects/AI-fashion-gallery/Clothes_Dataset"
if os.path.exists(DATASET_DIR):
    app.mount("/static/dataset", StaticFiles(directory=DATASET_DIR), name="dataset")
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)
app.mount("/static/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Create database tables
Base.metadata.create_all(bind=engine)

# Optional AI/ML deps
try:
    from .embeddings import (
        get_image_embedding_async,
        cosine_similarity,
        normalize_score,
        get_text_embedding_async,
    )
    have_embeddings = True
except Exception as e:
    have_embeddings = False
    _embedding_error = str(e)
    logger.warning(f"Embeddings disabled: {e}")

try:
    from .vector_store import query_vectors_async, fetch_vectors_async, get_index_stats_async
    have_vector_store = True
except Exception as e:
    have_vector_store = False
    _vector_error = str(e)
    logger.warning(f"Vector store disabled: {e}")

# Try-On Service Import (Safe)
try:
    from .tryon import tryon_service
    try_on_available = True
except Exception as e:
    logger.warning(f"Virtual Try-On service could not be loaded: {e}")
    try_on_available = False
    class DummyTryOn:
        def process_tryon(self, u, g):
            raise HTTPException(status_code=503, detail="Try-On service unavailable")
    tryon_service = DummyTryOn()

# Chatbot
try:
    from .chat_service import generate_chat_response
    have_chat = True
except Exception as e:
    have_chat = False
    _chat_error = str(e)
    logger.warning(f"Chat service disabled: {e}")


def get_image_url(request_url, file_path):
    if not file_path:
        return None
    file_path = str(file_path).replace("\\", "/")
    base_url = str(request_url.base_url).rstrip("/")

    # Handle absolute paths (e.g., C:/Users/... or /home/... or /mnt/c/Users/...)
    # Try to find DATASETS/Clothes_Dataset pattern anywhere in the path
    if "DATASETS/Clothes_Dataset/" in file_path:
        # Extract the part after DATASETS/Clothes_Dataset/
        relative = file_path.split("DATASETS/Clothes_Dataset/", 1)[-1]
        return f"{base_url}/static/dataset/{relative}"
    elif "Clothes_Dataset/" in file_path:
        # Extract the part after Clothes_Dataset/
        relative = file_path.split("Clothes_Dataset/", 1)[-1]
        return f"{base_url}/static/dataset/{relative}"
    elif file_path.startswith("uploads/"):
        return f"{base_url}/static/uploads/{file_path.replace('uploads/', '', 1)}"
    elif file_path.startswith("/"):
        # Absolute Linux path, try to extract Clothes_Dataset part
        if "Clothes_Dataset/" in file_path:
            relative = file_path.split("Clothes_Dataset/", 1)[-1]
            return f"{base_url}/static/dataset/{relative}"
        return file_path

    return file_path

@app.get("/")
async def root():
    return {"message": "Welcome to Fashion AI Gallery API", "mode": "minimal"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

CATEGORY_MAPPING = {
    "Tops": ["Blazer", "Hoodie", "Jacket", "Denim Jacket", "Sport Jacket", "T-Shirt", "Shirt", "Polo Shirt", "Sweater", "Coat", "Dress"],
    "Bottoms": ["Trousers", "Shorts", "Jeans", "Skirt"],
}

@app.get("/api/products", response_model=PaginatedProducts)
async def get_products(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
):
    if not have_vector_store:
        # fallback: read directly from SQLite
        db = next(get_db())
        try:
            q = db.query(Product)
            if category:
                if category in CATEGORY_MAPPING:
                    q = q.filter(Product.category.in_(CATEGORY_MAPPING[category]))
                else:
                    q = q.filter(Product.category == category)
            total = q.count()
            rows = q.offset((page - 1) * limit).limit(limit).all()
            products = []
            for row in rows:
                data = {
                    "id": str(row.id),
                    "name": row.name,
                    "style_code": row.style_code or "",
                    "price_min": float(row.price_min or 0),
                    "price_max": float(row.price_max or 0),
                    "image_url": get_image_url(request, row.image_url),
                    "category": row.category or "",
                    "color_swatches": row.color_swatches or [],
                    "social_label": getattr(row, "social_label", None),
                    "likes": int(row.likes or 0),
                }
                products.append(ProductSchema(**data))
            total_pages = max((total + limit - 1) // limit, 0)
            return {"products": products, "total": total, "page": page, "pages": total_pages}
        finally:
            db.close()

    try:
        query_embedding = await get_text_embedding_async("stylish fashion clothing")
    except Exception:
        return {"products": [], "total": 0, "page": page, "pages": 0}

    filter_query = {}
    if category:
        if category in CATEGORY_MAPPING:
            filter_query = {"category": {"$in": CATEGORY_MAPPING[category]}}
        else:
            filter_query = {"category": {"$eq": category}}

    fetch_limit = limit * page
    matches = await query_vectors_async(
        query_embedding=query_embedding, top_k=fetch_limit, filter=filter_query if filter_query else None
    )
    start_idx = (page - 1) * limit
    page_matches = matches[start_idx : start_idx + limit]
    products = []
    for m in page_matches:
        md = m.get("metadata", {}) or {}
        if not md:
            continue
        colors = md.get("color_swatches", [])
        if isinstance(colors, str):
            try:
                colors = json.loads(colors)
            except Exception:
                colors = []
        products.append(
            ProductSchema(
                id=m["id"],
                name=md.get("name", "Unknown"),
                style_code=md.get("style_code", ""),
                price_min=float(md.get("price_min", 0)),
                price_max=float(md.get("price_max", 0)),
                image_url=get_image_url(request, md.get("image_url", "")),
                category=md.get("category", ""),
                color_swatches=colors,
                social_label=md.get("social_label"),
                likes=int(md.get("likes", 0)),
            )
        )
    try:
        stats = await get_index_stats_async()
        total_count = stats.get("total_vector_count", 0) if isinstance(stats, dict) else getattr(stats, "total_vector_count", 0)
    except Exception:
        total_count = 0
    if total_count == 0:
        total_count = 1000
    total_pages = (total_count + limit - 1) // limit
    return {"products": products, "total": total_count, "page": page, "pages": total_pages}


@app.get("/api/products/{product_id}", response_model=ProductSchema)
async def get_product_by_id(request: Request, product_id: str):
    if not have_vector_store:
        raise HTTPException(status_code=404, detail="Product not found")
    vectors = await fetch_vectors_async([product_id])
    if not vectors or product_id not in vectors:
        raise HTTPException(status_code=404, detail="Product not found")
    vec = vectors[product_id]
    md = vec.get("metadata", {}) or {}
    colors = md.get("color_swatches", [])
    if isinstance(colors, str):
        try:
            colors = json.loads(colors)
        except Exception:
            colors = []
    product = ProductSchema(
        id=product_id,
        name=md.get("name", "Unknown"),
        style_code=md.get("style_code", ""),
        price_min=float(md.get("price_min", 0)),
        price_max=float(md.get("price_max", 0)),
        image_url=get_image_url(request, md.get("image_url", "")),
        category=md.get("category", ""),
        color_swatches=colors,
        social_label=md.get("social_label"),
        likes=int(md.get("likes", 0)),
    )
    return product

# Allowed image extensions for upload endpoints
_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

def _safe_upload_path(original_filename: str) -> str:
    suffix = Path(original_filename).suffix.lower() if original_filename else ".bin"
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{suffix}'. Allowed: jpg, jpeg, png, webp")
    return os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}{suffix}")

@app.post("/api/search-by-photo", response_model=List[SearchResult])
@limiter.limit(os.getenv("RATE_LIMIT_SEARCH", "20/minute"))
async def search_by_photo(request: Request, file: UploadFile = File(...)):
    if not have_embeddings:
        raise HTTPException(status_code=503, detail="Image search unavailable: embeddings feature not installed")
    file_path = _safe_upload_path(file.filename)
    contents = await file.read()
    async with aiofiles.open(file_path, "wb") as out_file:
        await out_file.write(contents)
    try:
        image = Image.open(io.BytesIO(contents))
        query_embedding = await get_image_embedding_async(image)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file")
    finally:
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except Exception:
            pass
    matches = await query_vectors_async(query_embedding, top_k=5)
    results = []
    for m in matches:
        md = m.get("metadata", {}) or {}
        if not md:
            continue
        colors = md.get("color_swatches", [])
        if isinstance(colors, str):
            try:
                colors = json.loads(colors)
            except Exception:
                colors = []
        product = ProductSchema(
            id=m["id"],
            name=md.get("name", "Unknown"),
            style_code=md.get("style_code", ""),
            price_min=float(md.get("price_min", 0)),
            price_max=float(md.get("price_max", 0)),
            image_url=get_image_url(request, md.get("image_url", "")),
            category=md.get("category", ""),
            color_swatches=colors,
            social_label=md.get("social_label"),
            likes=int(md.get("likes", 0)),
        )
        results.append(
            SearchResult(
                product=product,
                match_score=float(normalize_score(m["score"])) / 100.0,
                matched_color=colors[0] if colors else "#000000",
            )
        )
    return results

@app.post("/api/try-on")
@limiter.limit(os.getenv("RATE_LIMIT_TRYON", "5/minute"))
async def virtual_try_on(
    request: Request,
    user_image: UploadFile = File(...),
    garment_image_url: str = Form(None),
    garment_image_file: UploadFile = File(None),
):
    if not try_on_available:
        raise HTTPException(status_code=503, detail="Try-On service unavailable")
    if not user_image:
        raise HTTPException(status_code=400, detail="User image is required")
    user_bytes = await user_image.read()
    garment_bytes = None
    if garment_image_file:
        garment_bytes = await garment_image_file.read()
    elif garment_image_url:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(garment_image_url)
            if resp.status_code == 200:
                garment_bytes = resp.content
    if not garment_bytes:
        raise HTTPException(status_code=400, detail="Could not retrieve garment image")
    try:
        result_bytes = tryon_service.process_tryon(user_bytes, garment_bytes)
        return Response(content=result_bytes, media_type="image/png")
    except Exception as e:
        logger.error(f"Try-On processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Virtual Try-On processing failed: {str(e)}")

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

from sqlalchemy.orm import Session
from fastapi import Depends

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    if not have_chat:
        raise HTTPException(status_code=503, detail="Chat service unavailable")
    session_id = request.session_id or str(uuid.uuid4())
    user_msg = ChatMessage(session_id=session_id, sender='user', text=request.message)
    db.add(user_msg)
    db.commit()
    history_msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp.asc())
        .limit(10)
        .all()
    )
    history = [{"sender": msg.sender, "text": msg.text} for msg in history_msgs]
    response_text = await generate_chat_response(request.message, history=history)
    bot_msg = ChatMessage(session_id=session_id, sender='bot', text=response_text)
    db.add(bot_msg)
    db.commit()
    return {"response": response_text, "session_id": session_id}

@app.get("/api/chat/history/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(session_id: str, db: Session = Depends(get_db)):
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp.asc())
        .all()
    )
    return {"messages": messages}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
