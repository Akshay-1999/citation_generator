from db.config import Database
from utils.logging_utils import set_system_logger
from pathlib import Path

logger = set_system_logger("system_logger")

def calculate_md5(file_path : str) -> str:
    """Calculate MD5 checksum of a file."""
    import hashlib

    hash_md5 = hashlib.md5()
    try:
        logger.info(f"Calculating MD5 checksum for file: {file_path}")
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        checksum = hash_md5.hexdigest()
        logger.info(f"MD5 checksum calculated for file {file_path}: {checksum}")
        return checksum
    except Exception as e:
        logger.error(f"Error calculating MD5 checksum for file {file_path}: {e}")
        return str(e)

async def get_file_extension(file_path : str)-> str:
    file_extension = Path(file_path).suffix
    return(file_extension)

async def check_file_name(file_name : str)-> str:
    logger.info
    
async def log_file_upload(
        user_id : str , 
        filename : str , 
        file_path : str , 
        extension : str ,  
        file_size : int , 
        file_extension : str,
        md5 : str  ):
    """Log file upload details to the database."""
    logger.info(f"Getting DB connection pool for logging file upload: {filename}")
    pool = await Database.get_pool()
    async with pool.acquire() as connection:
        try:
            logger.info(f"Logging file upload: {filename}, Size: {file_size}, Uploader: {user_id}")
            await connection.execute(
                """
                INSERT INTO core.file_uploads (user_id, 
                filename, 
                file_path, 
                extension, 
                size_mb, 
                md5 ,
                created_at , 
                modified_at, 
                deleted_at)
                VALUES ($1, $2, $3, $4 , $5 , $6, now() , now() , null )
                """,
                user_id,
                filename,
                file_path, 
                file_extension, 
                file_size, 
                md5
            )
            logger.info(f"File upload logged successfully for file: {filename}")
        except Exception as e:
            logger.error(f"Error logging file upload for file {filename}: {e}")