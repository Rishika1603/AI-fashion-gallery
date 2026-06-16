import os
import time
import logging
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

logger = logging.getLogger(__name__)

try:
    from pinecone import Pinecone, ServerlessSpec
    logger.debug("Pinecone client imported successfully.")
except ImportError as e:
    logger.error(f"Error importing Pinecone: {e}")
    # Fallback or exit
    raise

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

if not PINECONE_API_KEY:
    raise RuntimeError(
        "PINECONE_API_KEY is not set. "
        f"Looked for .env at: {os.path.join(os.path.dirname(__file__), '.env')}"
    )

logger.info(f"PINECONE_API_KEY loaded (starts: {PINECONE_API_KEY[:4]}...)")
logger.info(f"PINECONE_INDEX_NAME: {PINECONE_INDEX_NAME}")

pc = None

def get_client():
    global pc
    if pc:
        return pc
    try:
        pc = Pinecone(api_key=PINECONE_API_KEY)
        return pc
    except Exception as e:
        logger.error(f"Error initializing Pinecone client: {e}")
        return None

_index_cache = None

def get_index():
    """Returns the Pinecone index, creating it if it doesn't exist."""
    global _index_cache
    if _index_cache:
        return _index_cache
        
    client = get_client()
    if not client:
        return None
    
    try:
        if PINECONE_INDEX_NAME not in client.list_indexes().names():
            logger.info(f"Index '{PINECONE_INDEX_NAME}' not found. Creating it...")
            client.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=512, # FashionCLIP dimension
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
            # Wait for index to be ready
            while not client.describe_index(PINECONE_INDEX_NAME).status['ready']:
                time.sleep(1)
            logger.info(f"Index '{PINECONE_INDEX_NAME}' created successfully.")
    except Exception as e:
        logger.error(f"Error checking/creating index: {e}")
        return None

    _index_cache = client.Index(PINECONE_INDEX_NAME)
    return _index_cache

def upsert_vectors(vectors: list):
    """
    Upserts a list of vectors to Pinecone.
    vectors: List of (id, embedding, metadata) tuples.
    """
    index = get_index()
    if not index:
        return
        
    # Pinecone expects list of (id, values, metadata)
    # Batching is recommended for large datasets, but for now we'll do simple chunks
    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i + batch_size]
        try:
            index.upsert(vectors=batch)
            logger.info(f"Upserted batch {i} to {i+len(batch)}")
        except Exception as e:
            logger.error(f"Error upserting batch {i}: {e}")

from starlette.concurrency import run_in_threadpool

def query_vectors(query_embedding: list, top_k: int = 5, filter: dict = None):
    """
    Queries Pinecone for the most similar vectors.
    """
    index = get_index()
    if not index:
        return []

    try:
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            filter=filter
        )
        return results['matches']
    except Exception as e:
        logger.error(f"Error querying vectors: {e}")
        return []

async def query_vectors_async(query_embedding: list, top_k: int = 5, filter: dict = None):
    return await run_in_threadpool(query_vectors, query_embedding, top_k, filter)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Testing Pinecone connection...")
    try:
        idx = get_index()
        if idx:
            logger.info(f"Successfully connected to index: {PINECONE_INDEX_NAME}")
            logger.info(f"Stats: {idx.describe_index_stats()}")
        else:
            logger.error("Failed to get index.")
    except Exception as e:
        logger.error(f"Connection failed: {e}")

def fetch_vectors(ids: list):
    """
    Fetches vectors by ID.
    Returns a dictionary of id -> vector data.
    """
    index = get_index()
    if not index:
        return {}
    try:
        response = index.fetch(ids=ids)
        return response['vectors']
    except Exception as e:
        logger.error(f"Error fetching vectors: {e}")
        return {}

async def fetch_vectors_async(ids: list):
    return await run_in_threadpool(fetch_vectors, ids)

def get_index_stats():
    """Returns index statistics such as total vector count."""
    index = get_index()
    if not index:
        return {}
    try:
        return index.describe_index_stats()
    except Exception as e:
        logger.error(f"Error getting index stats: {e}")
        return {}

async def get_index_stats_async():
    return await run_in_threadpool(get_index_stats)

def delete_index():
    """Deletes the Pinecone index."""
    client = get_client()
    if not client:
        return
    
    if PINECONE_INDEX_NAME in client.list_indexes().names():
        try:
            client.delete_index(PINECONE_INDEX_NAME)
            logger.info(f"Index '{PINECONE_INDEX_NAME}' deleted.")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Error deleting index: {e}")
