from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import torch
from typing import List, Union

from .scoring import cosine_similarity, normalize_score

import logging

logger = logging.getLogger(__name__)

# Lazy loading setup for FashionCLIP
model_name = "patrickjohncyh/fashion-clip"
_model = None
_processor = None

def get_model_and_processor():
    global _model, _processor
    if _model is None or _processor is None:
        logger.info(f"Lazy loading CLIP model '{model_name}'... (This may take a moment)")
        _model = CLIPModel.from_pretrained(model_name)
        _processor = CLIPProcessor.from_pretrained(model_name)
        logger.info("FashionCLIP loaded successfully.")
    return _model, _processor

from starlette.concurrency import run_in_threadpool

def get_image_embedding(image: Union[Image.Image, str]) -> List[float]:
    """Generates a CLIP embedding for a given image (PIL Image or path)."""
    model, processor = get_model_and_processor()
    
    if isinstance(image, str):
        image = Image.open(image)
        
    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        outputs = model.get_image_features(**inputs)
        
    if hasattr(outputs, 'pooler_output'):
        image_features = outputs.pooler_output
    else:
        image_features = outputs
        
    # Normalize the features
    image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
    return image_features.squeeze().tolist()

async def get_image_embedding_async(image: Union[Image.Image, str]) -> List[float]:
    return await run_in_threadpool(get_image_embedding, image)

def get_text_embedding(text: str) -> List[float]:
    """Generates a CLIP embedding for a given text."""
    model, processor = get_model_and_processor()
    
    inputs = processor(text=text, return_tensors="pt", padding=True)
    with torch.no_grad():
        outputs = model.get_text_features(**inputs)
    
    if hasattr(outputs, 'pooler_output'):
        text_features = outputs.pooler_output
    else:
        text_features = outputs
        
    # Normalize the features
    text_features = text_features / text_features.norm(p=2, dim=-1, keepdim=True)
    return text_features.squeeze().tolist()

async def get_text_embedding_async(text: str) -> List[float]:
    return await run_in_threadpool(get_text_embedding, text)

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Computes cosine similarity between two vectors."""
    from .scoring import cosine_similarity as _cosine_similarity
    return _cosine_similarity(vec1, vec2)

def normalize_score(raw_score: float) -> int:
    """
    Normalizes a raw CLIP cosine similarity score (typically 0.15 - 0.45 range)
    to a human-friendly percentage (0-100%).
    """
    from .scoring import normalize_score as _normalize_score
    return _normalize_score(raw_score)
