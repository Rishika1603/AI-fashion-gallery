import os
import logging
import re
from types import SimpleNamespace
from typing import List, Optional

import google.genai as genai
from google.genai import types

from .scoring import normalize_score

logger = logging.getLogger(__name__)

# Configure Gemini
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GENAI_API_KEY:
    logger.warning("GEMINI_API_KEY not found in environment variables.")

# Do not construct the client eagerly: genai.Client() raises when no key is
# present, which would take the whole chat service down at import time.
client = genai.Client(api_key=GENAI_API_KEY) if GENAI_API_KEY else None

# Generation Config
generation_config = types.GenerateContentConfig(
    temperature=0.3,
    top_p=1,
    top_k=1,
    max_output_tokens=2048,
)


def _singular(word: str) -> str:
    """Very small stemmer so 'shirts' matches the category 'T-Shirt'."""
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _catalog_text_search(query_text: str, top_k: int = 5) -> List[dict]:
    """Keyword search over the local catalog.

    Used when the optional vector stack (CLIP + Pinecone) is unavailable,
    so the assistant still answers with real catalog products instead of
    telling the user nothing was found.
    """
    from sqlalchemy import or_

    from .database import SessionLocal
    from .models import Product

    terms = [
        _singular(t)
        for t in re.findall(r"[a-z0-9]+", (query_text or "").lower())
        if len(t) > 2
    ]
    if not terms:
        return []

    db = SessionLocal()
    try:
        clauses = []
        for term in terms:
            like = f"%{term}%"
            clauses.append(or_(Product.name.ilike(like), Product.category.ilike(like)))

        rows = db.query(Product).filter(or_(*clauses)).limit(500).all()

        scored = []
        for product in rows:
            haystack = _singular(f"{product.name or ''} {product.category or ''}".lower())
            hits = sum(1 for term in terms if term in haystack)
            if hits:
                scored.append((hits, product))

        scored.sort(key=lambda item: (-item[0], (item[1].name or "")))

        results = []
        for hits, product in scored[:top_k]:
            results.append(
                {
                    "product": SimpleNamespace(
                        id=str(product.id),
                        name=product.name,
                        category=product.category,
                        price_min=product.price_min,
                        price_max=product.price_max,
                        in_stock=bool(product.in_stock),
                        image_url=product.image_url or "",
                    ),
                    "score": 0.22 + 0.05 * hits,
                }
            )
        return results
    except Exception as e:
        logger.warning(f"Catalog text search failed: {e}")
        return []
    finally:
        db.close()


async def get_relevant_products(query_text: str, top_k: int = 5) -> List[dict]:
    """
    Retrieves top_k relevant products based on the query text.

    Prefers CLIP text embeddings + Pinecone vector search. Falls back to a
    keyword search over the local catalog when that stack is not deployed.
    Returns a list of dictionaries with "product" and "score".
    """
    try:
        from .embeddings import get_text_embedding_async
        from .vector_store import query_vectors_async

        query_embedding = await get_text_embedding_async(query_text)
        if query_embedding:
            matches = await query_vectors_async(query_embedding, top_k=top_k)

            scored_products = []
            for m in matches:
                md = m.get('metadata', {})
                if not md: continue

                # Build a dict that looks like the product object for compatibility
                # Or better, just return the dict needed for context
                product_data = {
                    "id": m['id'],
                    "name": md.get('name', 'Unknown'),
                    "category": md.get('category', 'Unknown'),
                    "price_min": md.get('price_min', 0),
                    "price_max": md.get('price_max', 0),
                    "in_stock": bool(md.get('in_stock', 1)),
                    "image_url": md.get('image_url', '')
                }

                # We wrap it in a SimpleNamespace or just use dict if we update the consumer
                # The consumer `generate_chat_response` expects `item["product"].id` access.
                # Let's use a simple class or namedtuple for backward compat within the function
                p_obj = SimpleNamespace(**product_data)

                scored_products.append({"product": p_obj, "score": m['score']})

            if scored_products:
                return scored_products
    except Exception as e:
        logger.warning(f"Vector search unavailable, using catalog text search: {e}")

    return _catalog_text_search(query_text, top_k)

async def generate_chat_response(user_message: str, history: Optional[List[dict]] = None) -> str:
    """
    Generates a response from the chatbot using RAG.
    """
    if not GENAI_API_KEY:
        return "I'm sorry, I'm not correctly configured (API Key missing). Please contact the administrator."

    # 1. Retrieve relevant products
    relevant_products = await get_relevant_products(user_message)
    
    # 2. Construct Context
    context_str = ""
    
    # Prepend chat history for context
    if history:
        context_str += "Previous Conversation:\n"
        for msg in history:
            role = "Customer" if msg['sender'] == 'user' else "Assistant"
            context_str += f"{role}: {msg['text']}\n"
        context_str += "\n"

    if relevant_products:
        print("\n--- Product Match Accuracy (Logging Only) ---")
        context_str += "Here are some products from our catalog that might be relevant:\n"
        for item in relevant_products:
            p = item["product"]
            score_pct = normalize_score(item["score"])
            print(f"Product ID: {p.id}, Name: {p.name}, Match Accuracy: {score_pct}%")
            context_str += f"- ID: {p.id}, Name: {p.name}, Category: {p.category}, Price: ${p.price_min}-{p.price_max}, In Stock: {'Yes' if p.in_stock else 'No'}, Match Accuracy: {score_pct}%\n"
        print("---------------------------------------------\n")
    else:
        context_str += "No specific products found for this query in the catalog.\n"

    # 3. Construct Prompt
    prompt = f"""You are a helpful and stylish expert shopping assistant for an online fashion store. Your primary rule is to ONLY provide information about products that are currently available in our catalog.
    Use the chat history provided to understand what the user has previously asked and what you have responded, so that you can maintain a coherent conversation.

    User Query: "{user_message}"
    
    Context (Catalog Data and Chat History):
    {context_str}
    
    Instructions:
    - If the user's query can be answered using the "Context" provided above, do so naturally and recommend the relevant items.
    - PRODUCT LINKS: When mentioning a product, ALWAYS create a clickable markdown link in this exact format: `[Product Name](product:ID)` (e.g., `[Red T-shirt](product:123)`). This allows the user to click the product name to see it.
    - STRICT CATEGORY MATCHING: Users often ask for specific types of clothing (e.g., "jackets"). If the user asks for a specific category:
        1. ONLY recommend products that belong to that category or are extremely close variants.
        2. If a product in the Context is a different category (e.g., "Blazer") and the user specifically asked for another (e.g., "Jacket"), do NOT recommend the "Blazer" unless you explicitly mention it is a stylish alternative. 
        3. Prioritize items where the name or category matches the user's keywords exactly.
    - If the user asks about products, categories, or features NOT present in the "Context", politely inform them that those items are not currently in our catalog. 
    - CRITICAL: Do NOT provide information about products that are not listed in the Context.
    - Even if the user provides partial information, use the Context to find the closest match.
    - Start your response directly. Do not say "Based on the context..." or "According to the catalog...".
    - Keep your tone professional, friendly, and concise.
    """
    
    # 4. Call Gemini
    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=generation_config,
        )
        return response.text
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return "I'm sorry, I'm having trouble thinking right now. Please try again later."
