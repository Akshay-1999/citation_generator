from pydantic import BaseModel
from typing import Optional
from db.config import Database
from utils.logging_utils import set_system_logger
logger = set_system_logger("system_logger")

async def get_or_create_candiate(
    recruiter_id: str,
    candiate_name: str,
    candiate_email: str,
    candiate_phone_number: str,
    job_position: str,
    client: str,
    years_of_experience: float,
    job_id: str
):
    logger.info("--- Getting DB connection pool for creating candiate ---")
    pool = await Database.get_pool()
    async with pool.acquire() as connection:
        candiate_row = await connection.fetchrow(
            """
            SELECT * FROM interview.candidates WHERE candidate_email = $1
            """,
            candiate_email,
        )
        session_row = await connection.fetchrow(
            """
            SELECT session_id , job_id , interview_token FROM interview.interview_sessions WHERE job_id = $1
            """,
            job_position,
        )z
        

    


