from pydantic import BaseModel
from typing import Optional
from db.config import Database
from utils.logging_utils import set_system_logger
logger = set_system_logger("system_logger")

async def create_user(user_name: str, email: str, user_role: str, password: str): 
    pool = await Database.get_pool()
    async with pool.acquire() as connection:
        row = await connection.fetchrow(
            """
            select user_id from core.users where email = $1
            """,
            email,
        )
        if row:
            logger.error("User with this email already exists.")
            return {"error": "User with this email already exists."}
        await connection.execute(
            """
            INSERT INTO core.users (username, email, user_role, password)
            VALUES ($1, $2, $3, crypt($4, gen_salt('bf')))
            """,
            user_name, email, user_role, password
        )
        logger.info(f"User {user_name} created successfully.")
        return {"message": f"User created successfully."}


async def get_user(email: str) -> Optional[dict]:
    pool = await Database.get_pool()
    async with pool.acquire() as connection:
        row = await connection.fetchrow(
            """
            SELECT user_id, username, email, user_role
            FROM core.users
            WHERE email = $1
            """,
            email,
        )
        if row:
            logger.info(f"User found with email: {email}")
            return {
                "user_id": str(row['user_id']),
                "username": row['username'],
                "email": row['email'],
                "user_role": row['user_role']
            }
        else:
            logger.error(f"No user found with email: {email}")
            return None