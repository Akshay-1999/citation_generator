from db.config import Database
import uu
import asyncio
from utils.logging_utils import set_system_logger
from pydantic import BaseModel , EmailStr 

logger = set_system_logger("system_logger")


async def authenticate_user(email: EmailStr, password: str):
    logger.info(f"getting db connection pool for authentication")
    pool = await Database.get_pool()
    try:
        async with pool.acquire() as connection:
            logger.info(f"Authenticating user with email: {email}")
            row = await connection.fetchrow(
                """
                SELECT user_id, password , user_role , is_active
                FROM core.users
                WHERE email = $1
                AND password = crypt($2, password)
                AND is_active = true;
                """,
                email,
                password,
            )
            if row:
                logger.info(f"Authentication successful for email: {email}")
                # token_data = {"user_id": str(row['user_id']), "role": row['user_role'], "email": email, "password": row['password'], "is_active" : row['is_active']}
                user_data = dict(user_id=str(row['user_id']), role=row['user_role'], is_active=row['is_active'] , authenticated=True)
                return user_data
            else:
                logger.error(f"Authentication failed for email: {email}")
                return None
    except Exception as e:  
        print(f"Error during authentication: {e}")

