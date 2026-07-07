from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ProductSchema(BaseModel):
    id: str
    name: str
    style_code: str
    price_min: float
    price_max: float
    image_url: Optional[str] = None
    category: str
    color_swatches: List[str]
    social_label: Optional[str] = None
    likes: int

    class Config:
        from_attributes = True

class SearchResult(BaseModel):
    product: ProductSchema
    match_score: float
    matched_color: str

class PaginatedProducts(BaseModel):
    products: List[ProductSchema]
    total: int
    page: int
    pages: int

class ChatMessageSchema(BaseModel):
    id: int
    session_id: str
    sender: str
    text: str
    timestamp: datetime

    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatHistoryResponse(BaseModel):
    messages: List[ChatMessageSchema]

# ── Try-On Request Schemas ────────────────────────────────────────────

class TryOnRequestCreate(BaseModel):
    session_id: str

class TryOnRequestOut(BaseModel):
    id: int
    session_id: str
    status: str
    admin_note: Optional[str] = None
    result_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class AdminLoginRequest(BaseModel):
    password: str

class AdminRejectRequest(BaseModel):
    note: Optional[str] = None

