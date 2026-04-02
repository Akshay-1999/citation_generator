from db.config import Database
from utils.logging_utils import set_system_logger
from pathlib import Path
import uuid
from typing import List

logger = set_system_logger("system_logger")

async def get_file_extension(file_name : str)-> str:
    allowed_format = ['.pdf']
    file_extension = Path(file_name).suffix
    if file_extension not in allowed_format:
        logger.error(f"=== File extension {file_extension} is not allowed ===")
        return None
    return file_extension

async def check_file_exists(file_name : str  , user_id : str)-> str:
    logger.info(f"--- Checking if file name {file_name} already exists ---")
    pool = await Database.get_pool()
    async with pool.acquire() as connection:
        try:
            row = await connection.fetchrow(
                """
                SELECT filename , md5 , file_path , file_id
                FROM core.files
                WHERE filename = $1 AND user_id = $2 AND deleted_at IS NULL 
                """,
                file_name,
                user_id
            )
            if row:
                logger.info(f"--- File name {file_name} already exists ---")
                filename = row["filename"]
                md5 = row["md5"]
                file_path = row["file_path"]
                file_id = row["file_id"]
                return filename, md5, file_path, file_id
            else:
                logger.info(f"--- File name {file_name} does not exist ---")
                return None
        except Exception as e:
            logger.error(f"=== Error checking file name {file_name}: {e} ===")
            return None
    
async def log_file_upload(
        user_id : str , 
        filename : str , 
        file_path : str , 
        extension : str ,  
        file_size : int , 
        md5 : str  ):
    """Log file upload details to the database."""
    logger.info(f"--- Getting DB connection pool for logging file upload: {filename} ---")
    pool = await Database.get_pool()
    async with pool.acquire() as connection:
        try:
            logger.info(f"--- Logging file upload: {filename}, Size: {file_size}, Uploader: {user_id} ---")
            await connection.execute(
                """
                INSERT INTO core.files (user_id, 
                filename, 
                file_path, 
                extension, 
                size_mb, 
                md5 ,
                created_at , 
                modified_at, 
                deleted_at,
                is_deleted,
                processing_state)
                VALUES ($1, $2, $3, $4 , $5 , $6, now() , now() , null , 'false' , 'not_processed')
                """,
                user_id,
                filename,
                file_path, 
                extension, 
                file_size, 
                md5
            )
            logger.info(f"=== File upload logged successfully for file: {filename} ===")
        except Exception as e:
            logger.error(f"=== Error logging file upload for file {filename}: {e} ===")

async def log_file_update(file_id : str , md5 : str , file_size : int):
    """Log file update details to the database."""
    logger.info(f"--- Getting DB connection pool for logging file update: {file_id} ---")
    pool = await Database.get_pool()
    async with pool.acquire() as connection:
        try:
            logger.info(f"--- Logging file update: {file_id}, MD5: {md5}, File size: {file_size} ---")
            await connection.execute(
                """
                UPDATE core.files
                SET md5 = $1, size_mb = $2, modified_at = now()
                WHERE file_id = $3
                """,
                md5,
                file_size,
                file_id
            )
            logger.info(f"=== File update logged successfully for file: {file_id} ===")
        except Exception as e:
            logger.error(f"=== Error logging file update for file {file_id}: {e} ===")

async def get_document_id(doc_name : str , user_id : str)-> str:
    """Get document id from the database."""
    logger.info(f"--- Getting DB connection pool for getting document id: {doc_name} ---")
    pool = await Database.get_pool()
    async with pool.acquire() as connection:
        try:
            logger.info(f"--- Getting document id: {doc_name} ---")
            row = await connection.fetchrow(
                """
                SELECT file_id
                FROM core.files
                WHERE filename = $1 AND user_id = $2 AND deleted_at IS NULL
                """,
                doc_name,
                user_id
            )
            if row:
                logger.info(f"--- File ID found: {row['file_id']} ---")
                return row["file_id"]
            else:
                logger.info(f"file id not found for file: {doc_name}")
                return None
        except Exception as e:
            logger.error(f"=== Error getting document id for file {doc_name}: {e} ===")
            return None

async def get_documents_by_status(status : str , user_id : str)-> List[str]:
    """Get documents by status from the database."""
    logger.info(f"--- Getting DB connection pool for getting documents by status: {status} ---")
    pool = await Database.get_pool()
    async with pool.acquire() as connection:
        try:
            logger.info(f"--- Getting documents by status: {status} ---")
            rows = await connection.fetch(
                """
                SELECT file_path
                FROM core.files
                WHERE processing_state = $1 AND user_id = $2 AND deleted_at IS NULL
                """,
                status,
                user_id
            )
            if rows:
                logger.info(f"Documents found for status: {status}")
                return [row["file_path"] for row in rows]
            else:
                logger.info(f"Documents not found for status: {status}")
                return []
        except Exception as e:
            logger.error(f"=== Error getting documents by status: {e} ===")
            return []

async def add_chunks_data(chunks_data):
    """
    Bulk insert function for multiple chunks at once.
    chunks_data should be a list of tuples: (document_id, chunk_index, metadata, result)
    """
    if not chunks_data:
        logger.info("--- No chunks data to insert ---")
        return
        
    try:
        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            # Prepare data for bulk insert
            insert_data = []
            for document_id, chunk_index, metadata, result in chunks_data:
                chunk_id = str(uuid.uuid4())
                insert_data.append((
                    document_id,
                    chunk_id,
                    chunk_index,
                    metadata.get("chunk_name", ""),
                    result,
                    metadata.get("fallback_triggered", False),
                    metadata.get("processing_tool", ""),
                    metadata.get("number_of_pages", 0),
                    metadata.get("file_name", ""),
                    metadata.get("start_timestamp"),
                    metadata.get("processing_time", 0),
                    metadata.get("task_id", "N/A"),
                    metadata.get("fallback_reason", "N/A")
                ))
            
            # Use execute_values for bulk insert
            await conn.executemany(
                """
                INSERT INTO core.document_chunks (document_id, chunk_id, chunk_index, tmp_file_name, result, fallback_trigger, processing_tool, number_of_pages, file_name, start_timestamp, processing_time, task_id, fallback_reason)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                insert_data
            )
            logger.info(f"=== Bulk inserted {len(chunks_data)} chunks for document_id={document_id} ===")
    except Exception as e:
        logger.error(f"Failed to bulk insert chunks data: {e}", exc_info=True)
        raise

async def update_file_status(file_path : str , status : str , user_id : str):
    """Update file status in the database."""
    logger.info(f"--- Getting DB connection pool for updating file status: {file_path} ---")
    pool = await Database.get_pool()
    async with pool.acquire() as connection:
        try:
            logger.info(f"--- Updating file status: {file_path}, Status: {status} ---")
            await connection.execute(
                """
                UPDATE core.files
                SET processing_state = $1, modified_at = now()
                WHERE file_path = $2 AND user_id = $3
                """,
                status,
                file_path,
                user_id
            )
            logger.info(f"=== File status updated successfully for file: {file_path} ===")
        except Exception as e:
            logger.error(f"=== Error updating file status for file {file_path}: {e} ===")