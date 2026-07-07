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
from .models import Product, ChatMessage, TryOnRequest
from .schemas import (
    ProductSchema,
    SearchResult,
    PaginatedProducts,
    ChatHistoryResponse,
    TryOnRequestCreate,
    TryOnRequestOut,
    AdminLoginRequest,
    AdminRejectRequest,
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
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173")
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

# Upload directory for try-on request images
TRYON_UPLOAD_DIR = "tryon_uploads"
if not os.path.exists(TRYON_UPLOAD_DIR):
    os.makedirs(TRYON_UPLOAD_DIR)

# Serve try-on results
os.makedirs("tryon_results", exist_ok=True)
app.mount("/static/tryon_results", StaticFiles(directory="tryon_results"), name="tryon_results")

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
    try_on_available = tryon_service.available
except Exception as e:
    logger.warning(f"Virtual Try-On service could not be loaded: {e}")
    try_on_available = False
    tryon_service = None

# Fashn.ai Comprehensive Service — OPTIONAL / LAZY
# Imported lazily inside route handlers so the app still starts when
# FASHN_API_KEY is not set. If you never use Fashn, this is skipped.
try:
    from .fashn_service import get_fashn_client, FashnAIClient
    _fashn_import_ok = True
except Exception as e:
    _fashn_import_ok = False
    _fashn_import_error = str(e)
    logger.warning(f"Fashn.ai service not available: {e}")

# Chatbot — OPTIONAL / LAZY
# Imported lazily so missing genai/pinecone/torch don't break startup.
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


# ── Fashn.ai Comprehensive Feature Routes ────────────────────────────
# Fully optional: endpoints register unconditionally, but return 503
# unless FASHN_API_KEY is configured and the service imports cleanly.
_fashn_enabled = False
try:
    from .fashn_service import get_fashn_client
    _fashn_enabled = True
except Exception as e:
    logger.warning("Fashn.ai routes disabled on import: %s", e)

from fastapi import UploadFile, File, Form
from typing import List as TypingList


def _fashn_guard():
    if not _fashn_enabled:
        raise HTTPException(
            status_code=503,
            detail="Fashn.ai service is not configured on this deployment",
        )
    from .fashn_service import get_fashn_client
    client = get_fashn_client()
    if client is None:
        raise HTTPException(
            status_code=503,
            detail="Fashn.ai service unavailable. Set FASHN_API_KEY in .env",
        )
    return client


async def _read_image(file: UploadFile = None, url: str = None) -> Optional[bytes]:
    """Read image from either an uploaded file or a URL string."""
    if file and file.filename:
        return await file.read()
    if url:
        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.content
            raise HTTPException(status_code=400, detail=f"Could not fetch image from URL: {url}")
    return None


# ── Status ────────────────────────────────────────────────────────────

@app.get("/api/fashn/status")
async def fashn_status():
    """Check Fashn.ai availability and list capabilities."""
    client = get_fashn_client()
    return {
        "available": client is not None,
        "features": [
            "tryon-max",
            "product-to-model",
            "face-to-model",
            "model-create",
            "edit",
            "reframe",
            "image-to-video",
            "background-remove",
        ],
    }


# ── Try-On Max ────────────────────────────────────────────────────────

class FashnTryOnRequest(BaseModel):
    garment_url: Optional[str] = None
    model_url: Optional[str] = None
    prompt: Optional[str] = None
    resolution: str = "1k"
    generation_mode: Optional[str] = None
    num_images: int = 1
    output_format: str = "png"
    return_base64: bool = False


@app.post("/api/fashn/tryon")
@limiter.limit("10/minute")
async def fashn_tryon(
    request: Request,
    garment_file: UploadFile = File(None),
    model_file: UploadFile = File(None),
    garment_url: str = Form(None),
    model_url: str = Form(None),
    prompt: str = Form(None),
    resolution: str = Form("1k"),
    generation_mode: str = Form(None),
    num_images: int = Form(1),
    output_format: str = Form("png"),
    return_base64: bool = Form(False),
):
    """Virtual Try-On Max — place garment on a model."""
    client = _fashn_guard()
    garment = await _read_image(garment_file, garment_url)
    model = await _read_image(model_file, model_url)
    if not garment or not model:
        raise HTTPException(status_code=400, detail="Both garment and model images are required")
    result = await client.try_on(
        product_image=garment,
        model_image=model,
        prompt=prompt,
        resolution=resolution,
        generation_mode=generation_mode,
        num_images=num_images,
        output_format=output_format,
        return_base64=return_base64,
    )
    return Response(content=result, media_type=f"image/{output_format}")


# ── Product to Model ─────────────────────────────────────────────────

class ProductToModelRequest(BaseModel):
    product_url: Optional[str] = None
    prompt: Optional[str] = None
    face_reference_url: Optional[str] = None
    aspect_ratio: Optional[str] = None
    resolution: str = "1k"
    generation_mode: Optional[str] = None
    num_images: int = 1
    output_format: str = "png"


@app.post("/api/fashn/product-to-model")
@limiter.limit("10/minute")
async def fashn_product_to_model(
    request: Request,
    product_file: UploadFile = File(None),
    product_url: str = Form(None),
    prompt: str = Form(None),
    face_reference_file: UploadFile = File(None),
    face_reference_url: str = Form(None),
    aspect_ratio: str = Form(None),
    resolution: str = Form("1k"),
    generation_mode: str = Form(None),
    num_images: int = Form(1),
    output_format: str = Form("png"),
):
    """Product to Model — generate a model wearing the product."""
    client = _fashn_guard()
    product = await _read_image(product_file, product_url)
    if not product:
        raise HTTPException(status_code=400, detail="Product image is required")
    face_ref = await _read_image(face_reference_file, face_reference_url) if face_reference_file or face_reference_url else None
    result = await client.product_to_model(
        product_image=product,
        prompt=prompt,
        face_reference=face_ref,
        aspect_ratio=aspect_ratio or None,
        resolution=resolution,
        generation_mode=generation_mode,
        num_images=num_images,
        output_format=output_format,
    )
    return Response(content=result, media_type=f"image/{output_format}")


# ── Face to Model ────────────────────────────────────────────────────

class FaceToModelRequest(BaseModel):
    face_url: Optional[str] = None
    prompt: Optional[str] = None
    aspect_ratio: str = "2:3"
    resolution: str = "1k"
    generation_mode: Optional[str] = None
    num_images: int = 1
    output_format: str = "jpeg"


@app.post("/api/fashn/face-to-model")
@limiter.limit("10/minute")
async def fashn_face_to_model(
    request: Request,
    face_file: UploadFile = File(None),
    face_url: str = Form(None),
    prompt: str = Form(None),
    aspect_ratio: str = Form("2:3"),
    resolution: str = Form("1k"),
    generation_mode: str = Form(None),
    num_images: int = Form(1),
    output_format: str = Form("jpeg"),
):
    """Face to Model — transform a face/headshot into an upper-body avatar."""
    client = _fashn_guard()
    face = await _read_image(face_file, face_url)
    if not face:
        raise HTTPException(status_code=400, detail="Face image is required")
    result = await client.face_to_model(
        face_image=face,
        prompt=prompt,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        generation_mode=generation_mode,
        num_images=num_images,
        output_format=output_format,
    )
    return Response(content=result, media_type=f"image/{output_format}")


# ── Model Create ─────────────────────────────────────────────────────

class ModelCreateRequest(BaseModel):
    model_name: Optional[str] = None
    image_url: Optional[str] = None


@app.post("/api/fashn/model-create")
@limiter.limit("10/minute")
async def fashn_model_create(
    request: Request,
    image_file: UploadFile = File(None),
    image_url: str = Form(None),
    model_name: str = Form(None),
):
    """Create an AI model from model photos for use in virtual try-ons."""
    client = _fashn_guard()
    img = await _read_image(image_file, image_url)
    if not img:
        raise HTTPException(status_code=400, detail="Model image is required")
    result = await client.model_create(
        model_image=img,
        model_name=model_name,
    )
    return {"prediction_id": result.get("id"), "status": result.get("status", "processing")}


# ── Edit ─────────────────────────────────────────────────────────────

class EditRequest(BaseModel):
    image_url: Optional[str] = None
    prompt: str
    mask_url: Optional[str] = None
    resolution: str = "1k"
    generation_mode: Optional[str] = None
    num_images: int = 1
    output_format: str = "png"


@app.post("/api/fashn/edit")
@limiter.limit("10/minute")
async def fashn_edit(
    request: Request,
    image_file: UploadFile = File(None),
    image_url: str = Form(None),
    prompt: str = Form(...),
    mask_file: UploadFile = File(None),
    mask_url: str = Form(None),
    resolution: str = Form("1k"),
    generation_mode: str = Form(None),
    num_images: int = Form(1),
    output_format: str = Form("png"),
):
    """Edit — restyle / adjust / fix details while preserving subject identity."""
    client = _fashn_guard()
    img = await _read_image(image_file, image_url)
    if not img:
        raise HTTPException(status_code=400, detail="Image is required")
    mask = await _read_image(mask_file, mask_url) if mask_file or mask_url else None
    result = await client.edit(
        image=img,
        prompt=prompt,
        mask=mask,
        resolution=resolution,
        generation_mode=generation_mode,
        num_images=num_images,
        output_format=output_format,
    )
    return Response(content=result, media_type=f"image/{output_format}")


# ── Reframe (Change Aspect Ratio) ────────────────────────────────────

class ReframeRequest(BaseModel):
    image_url: Optional[str] = None
    aspect_ratio: str = "1:1"
    resolution: str = "1k"
    generation_mode: Optional[str] = None
    num_images: int = 1
    output_format: str = "png"


@app.post("/api/fashn/reframe")
@limiter.limit("10/minute")
async def fashn_reframe(
    request: Request,
    image_file: UploadFile = File(None),
    image_url: str = Form(None),
    aspect_ratio: str = Form("1:1"),
    resolution: str = Form("1k"),
    generation_mode: str = Form(None),
    num_images: int = Form(1),
    output_format: str = Form("png"),
):
    """Reframe — change aspect ratio by smart crop or out-paint."""
    client = _fashn_guard()
    img = await _read_image(image_file, image_url)
    if not img:
        raise HTTPException(status_code=400, detail="Image is required")
    result = await client.reframe(
        image=img,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        generation_mode=generation_mode,
        num_images=num_images,
        output_format=output_format,
    )
    return Response(content=result, media_type=f"image/{output_format}")


# ── Image to Video ───────────────────────────────────────────────────

class ImageToVideoRequest(BaseModel):
    image_url: Optional[str] = None
    prompt: Optional[str] = None
    duration: int = 5
    resolution: str = "720p"


@app.post("/api/fashn/image-to-video")
@limiter.limit("5/minute")
async def fashn_image_to_video(
    request: Request,
    image_file: UploadFile = File(None),
    image_url: str = Form(None),
    prompt: str = Form(None),
    duration: int = Form(5),
    resolution: str = Form("720p"),
):
    """Image to Video — animate a still image into a short MP4 clip."""
    client = _fashn_guard()
    img = await _read_image(image_file, image_url)
    if not img:
        raise HTTPException(status_code=400, detail="Image is required")
    result_url = await client.image_to_video(
        image=img,
        prompt=prompt,
        duration=duration,
        resolution=resolution,
    )
    return {"video_url": result_url}


# ── Background Remove ────────────────────────────────────────────────

class BackgroundRemoveRequest(BaseModel):
    image_url: Optional[str] = None
    return_base64: bool = False


@app.post("/api/fashn/background-remove")
@limiter.limit("20/minute")
async def fashn_background_remove(
    request: Request,
    image_file: UploadFile = File(None),
    image_url: str = Form(None),
    return_base64: bool = Form(False),
):
    """Background Remove — remove background, return transparent PNG."""
    client = _fashn_guard()
    img = await _read_image(image_file, image_url)
    if not img:
        raise HTTPException(status_code=400, detail="Image is required")
    result = await client.background_remove(
        image=img,
        return_base64=return_base64,
    )
    return Response(content=result, media_type="image/png")


# ── Feature discovery ────────────────────────────────────────────────

@app.get("/api/fashn/features")
async def fashn_features():
    """Return detailed info about each available Fashn.ai feature."""
    return {
        "features": [
            {
                "id": "tryon-max",
                "name": "Virtual Try-On Max",
                "description": "Place a product (garment, accessory) on a model image with enhanced fidelity",
                "inputs": ["garment_image", "model_image", "prompt", "resolution", "generation_mode"],
                "lifecycle": "preview",
            },
            {
                "id": "product-to-model",
                "name": "Product to Model",
                "description": "Generate a model wearing the product from product photo alone",
                "inputs": ["product_image", "prompt", "face_reference", "aspect_ratio"],
                "lifecycle": "preview",
            },
            {
                "id": "face-to-model",
                "name": "Face to Model",
                "description": "Transform a face/headshot into a try-on ready upper-body avatar",
                "inputs": ["face_image", "prompt", "aspect_ratio"],
                "lifecycle": "experimental",
            },
            {
                "id": "model-create",
                "name": "Model Create",
                "description": "Create an AI model from model photos for virtual try-ons",
                "inputs": ["model_image", "name"],
                "lifecycle": "experimental",
            },
            {
                "id": "edit",
                "name": "Edit",
                "description": "Restyle shots, adjust views, fix details while preserving identity and product",
                "inputs": ["image", "prompt", "mask", "image_context"],
                "lifecycle": "experimental",
            },
            {
                "id": "reframe",
                "name": "Reframe",
                "description": "Change aspect ratio by smart crop or out-paint",
                "inputs": ["image", "aspect_ratio"],
                "lifecycle": "experimental",
            },
            {
                "id": "image-to-video",
                "name": "Image to Video",
                "description": "Create short MP4 videos from a single image",
                "inputs": ["image", "duration", "resolution"],
                "lifecycle": "experimental",
            },
            {
                "id": "background-remove",
                "name": "Background Remove",
                "description": "Remove image background to transparent PNG",
                "inputs": ["image"],
                "lifecycle": "experimental",
            },
        ],
        "excluded_features": ["model-swap"],
    }

# ── Admin Configuration ───────────────────────────────────────────────

ADMIN_KEY = os.getenv("ADMIN_KEY", "admin123")  # Change in production!
from fastapi import Header, Depends, HTTPException, status

async def verify_admin(authorization: str = Header(None, alias="Authorization")):
    """Dependency to verify admin access via Bearer token."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or token != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin credentials")
    return True

# ── Try-On Request / Admin Approval Routes ────────────────────────────

@app.post("/api/tryon/request", response_model=TryOnRequestOut)
async def create_tryon_request(
    session_id: str = Form(...),
    person_image: UploadFile = File(...),
    garment_image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """User submits a try-on request. Admin must approve before execution."""
    # Save uploaded images
    req_id = str(uuid.uuid4())[:8]
    person_ext = Path(person_image.filename or "person.png").suffix or ".png"
    garment_ext = Path(garment_image.filename or "garment.png").suffix or ".png"
    person_path = os.path.join(TRYON_UPLOAD_DIR, f"{req_id}_person{person_ext}")
    garment_path = os.path.join(TRYON_UPLOAD_DIR, f"{req_id}_garment{garment_ext}")

    person_bytes = await person_image.read()
    garment_bytes = await garment_image.read()
    with open(person_path, "wb") as f:
        f.write(person_bytes)
    with open(garment_path, "wb") as f:
        f.write(garment_bytes)

    record = TryOnRequest(
        session_id=session_id,
        person_image_path=person_path,
        garment_image_path=garment_path,
        status="pending",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    logger.info("Try-on request #%d created (session=%s)", record.id, session_id)
    return record


@app.get("/api/tryon/requests", response_model=List[TryOnRequestOut])
async def list_user_requests(
    session_id: str = Query(...),
    db: Session = Depends(get_db),
):
    """List try-on requests for a given session."""
    records = (
        db.query(TryOnRequest)
        .filter(TryOnRequest.session_id == session_id)
        .order_by(TryOnRequest.created_at.desc())
        .all()
    )
    result = []
    for r in records:
        result.append(TryOnRequestOut(
            id=r.id,
            session_id=r.session_id,
            status=r.status,
            admin_note=r.admin_note,
            result_url=f"/static/tryon_results/{r.id}.png" if r.result_path and os.path.exists(r.result_path) else None,
            created_at=r.created_at,
        ))
    return result


@app.get("/api/admin/tryon/pending", response_model=List[TryOnRequestOut])
async def admin_pending_requests(
    _=Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """Admin views all pending requests."""
    records = (
        db.query(TryOnRequest)
        .filter(TryOnRequest.status == "pending")
        .order_by(TryOnRequest.created_at.asc())
        .all()
    )
    return [
        TryOnRequestOut(
            id=r.id,
            session_id=r.session_id,
            status=r.status,
            admin_note=r.admin_note,
            created_at=r.created_at,
        )
        for r in records
    ]


@app.get("/api/admin/tryon/request/{request_id}", response_model=TryOnRequestOut)
async def admin_get_request_detail(
    request_id: int,
    _=Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """Admin views full detail of a specific request (including image paths)."""
    record = db.query(TryOnRequest).filter(TryOnRequest.id == request_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Request not found")
    return TryOnRequestOut(
        id=record.id,
        session_id=record.session_id,
        status=record.status,
        admin_note=record.admin_note,
        result_url=f"/static/tryon_results/{record.id}.png" if record.result_path and os.path.exists(record.result_path) else None,
        created_at=record.created_at,
    )


@app.post("/api/admin/tryon/approve/{request_id}")
async def admin_approve_tryon(
    request_id: int,
    _=Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """Admin approves a try-on request — executes the try-on using free HF Space backend."""
    record = db.query(TryOnRequest).filter(TryOnRequest.id == request_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Request not found")
    if record.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {record.status}")

    # Execute try-on
    if not try_on_available:
        # Mark as rejected since no backend available
        record.status = "rejected"
        record.admin_note = "Try-On service is not available. Configure an API key."
        db.commit()
        raise HTTPException(status_code=503, detail="Try-On service unavailable")

    try:
        with open(record.person_image_path, "rb") as f:
            person_bytes = f.read()
        with open(record.garment_image_path, "rb") as f:
            garment_bytes = f.read()

        result_bytes = tryon_service.process_tryon(person_bytes, garment_bytes)

        # Save result
        os.makedirs("tryon_results", exist_ok=True)
        result_path = f"tryon_results/{record.id}.png"
        with open(result_path, "wb") as f:
            f.write(result_bytes)

        record.status = "completed"
        record.result_path = os.path.abspath(result_path)
        db.commit()
        logger.info("Try-on request #%d approved and completed", request_id)
        return {"status": "completed", "result_url": f"/static/tryon_results/{record.id}.png"}

    except Exception as e:
        logger.error(f"Try-on execution failed for request #{request_id}: {e}")
        record.status = "rejected"
        record.admin_note = f"Processing failed: {str(e)}"
        db.commit()
        return {"status": "failed", "error": str(e)}


@app.post("/api/admin/tryon/reject/{request_id}")
async def admin_reject_tryon(
    request_id: int,
    body: AdminRejectRequest,
    _=Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """Admin rejects a try-on request."""
    record = db.query(TryOnRequest).filter(TryOnRequest.id == request_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Request not found")
    if record.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {record.status}")

    record.status = "rejected"
    record.admin_note = body.note or "Rejected by admin"
    db.commit()
    logger.info("Try-on request #%d rejected: %s", request_id, record.admin_note)
    return {"status": "rejected", "note": record.admin_note}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
