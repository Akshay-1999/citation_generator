from db.config import Database
import uu
import asyncio
from utils.logger_instances import auth_logger as logger
from pydantic import EmailStr 


async def authenticate_user(email: EmailStr, password: str):
    logger.info(f"--- getting db connection pool for authentication ---")
    pool = await Database.get_pool()
    try:
        async with pool.acquire() as connection:
            logger.info(f"--- Authenticating user with email: {email} ---")
            row = await connection.fetchrow(
                """
                SELECT user_id, username, password , user_role , is_active , email
                FROM core.users
                WHERE email = $1
                AND password = crypt($2, password)
                AND is_active = true;
                """,
                email,
                password,
            )
            if row:
                logger.info(f"=== Authentication successful for email: {email} ===")
                user_data = dict(
                    user_id=str(row['user_id']), 
                    username=row['username'],
                    role=row['user_role'], 
                    is_active=row['is_active'], 
                    email=row['email']
                )
                return user_data
            else:
                logger.error(f"=== Authentication failed for email: {email} ===")
                return None
    except Exception as e:      
        logger.error(f"=== Error during authentication: {e} ===")
        return None

