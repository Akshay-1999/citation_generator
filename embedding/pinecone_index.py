import os 
import asyncio
from pinecone import Pinecone, ServerlessSpec
from pinecone.grpc import PineconeGRPC as Pinecone
from utils.logger_instances import file_logger as logger
from dotenv import load_dotenv

load_dotenv()

pc = None
_pinecone_index = None

PINECONE_DIMENSION = 1536
PINECONE_METRIC = "cosine"

async def get_pinecone_index():
    global pc, _pinecone_index
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME")

    if pc is None:
        pc = Pinecone(api_key=api_key)

    if _pinecone_index is None:
        if not api_key or not index_name:
            logger.error("=== PINECONE_API_KEY or PINECONE_INDEX_NAME not found in environment variables ===")
            raise ValueError("PINECONE_API_KEY or PINECONE_INDEX_NAME not found in environment variables")
        
        # Automatically create or get the index
        _pinecone_index = await create_pinecone_index()

    return _pinecone_index

async def create_pinecone_index():
    """Asynchronously create Pinecone index if it doesn't exist."""
    global pc, _pinecone_index
    index_name = os.getenv("PINECONE_INDEX_NAME")
    api_key = os.getenv("PINECONE_API_KEY")
    
    if not index_name or not api_key:
        logger.error("=== PINECONE_API_KEY or PINECONE_INDEX_NAME not found in environment variables ===")
        raise ValueError("PINECONE_API_KEY or PINECONE_INDEX_NAME not found in environment variables")

    if pc is None:
        pc = Pinecone(api_key=api_key)

    logger.info(f"=== Creating/checking Pinecone index: {index_name} ===")
    loop = asyncio.get_event_loop()
    try:
        existing_index = await loop.run_in_executor(None, lambda: pc.list_indexes().names())
        logger.debug(f"Existing indexes: {existing_index}")
        
        if index_name in existing_index:
            logger.info(f"--- Index {index_name} already exists ---")
        else:
            logger.info(f"--- Index {index_name} does not exist, creating new index with dimension {PINECONE_DIMENSION} ---")
            await loop.run_in_executor(
                None,
                lambda: pc.create_index(
                    name=index_name,
                    dimension=PINECONE_DIMENSION,
                    metric=PINECONE_METRIC,
                    spec=ServerlessSpec(cloud="aws", region="us-east-1")
                )
            )
            logger.info(f"=== Index {index_name} created successfully ===")
            
        _pinecone_index = pc.Index(index_name)
        return _pinecone_index
        
    except Exception as e:
        logger.error(f"=== Failed to create Pinecone index: {str(e)} ===",exc_info=True)    
        raise

async def delete_pinecone_index(pinecone_filter: dict, namespace: str = None):
    index = await get_pinecone_index()
    if index is None:
        logger.warning("=== Pinecone index not found ===")
        return
    try:
        index.delete(filter=pinecone_filter, namespace=namespace)
        logger.info(f"=== Pinecone vectors deleted successfully from namespace: {namespace} ===")
    except Exception as e:
        logger.error(f"=== Failed to delete Pinecone vectors: {str(e)} ===", exc_info=True)    
        raise