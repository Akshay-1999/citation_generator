from db.config import Database
from utils.logging_utils import set_system_logger
logger = set_system_logger("system_logger")

async def check_file(file_path: str)-> str:
    logger.info("getting db connection")
    pool = await Database.get_pool()
    async with pool.acquire() as connection:
        row = await connection.fetchrow(
        )