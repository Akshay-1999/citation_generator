from db.config import Database
from utils.logging_utils import set_system_logger
from pathlib import Path

logger = set_system_logger("system_logger")

async def get_file_extension(file_name : str)-> str:
    allowed_format = ['.pdf' , '.txt' , '.doc' , '.docx']
    file_extension = Path(file_name).suffix
    if file_extension not in allowed_format:
        logger.error(f"File extension {file_extension} is not allowed")
        return None
    return(file_extension)

async def check_file_exists(file_name : str , md5 : str , user_id : str)-> str:
    logger.info(f"Checking if file name {file_name} already exists")
    pool = await Database.get_pool()
    async with pool.acquire() as connection:
        try:
            row = await connection.fetchrow(
                """
                SELECT filename
                FROM core.files
                WHERE filename = $1 and md5 = $2 and user_id = $3 and deleted_at is null 
                """,
                file_name,
                md5,
                user_id
            )
            if row:
                logger.info(f"File name {file_name} already exists")
                return True
            else:
                logger.info(f"File name {file_name} does not exist")
                return False
        except Exception as e:
            logger.error(f"Error checking file name {file_name}: {e}")
            return False
    
async def log_file_upload(
        user_id : str , 
        filename : str , 
        file_path : str , 
        extension : str ,  
        file_size : int , 
        md5 : str  ):
    """Log file upload details to the database."""
    logger.info(f"Getting DB connection pool for logging file upload: {filename}")
    pool = await Database.get_pool()
    async with pool.acquire() as connection:
        try:
            logger.info(f"Logging file upload: {filename}, Size: {file_size}, Uploader: {user_id}")
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
                processing_state)
                VALUES ($1, $2, $3, $4 , $5 , $6, now() , now() , null , 'not_processed')
                """,
                user_id,
                filename,
                file_path, 
                extension, 
                file_size, 
                md5
            )
            logger.info(f"File upload logged successfully for file: {filename}")
        except Exception as e:
            logger.error(f"Error logging file upload for file {filename}: {e}")