from pydantic import BaseModel
from typing import Optional
from db.config import Database
from utils.logging_utils import set_system_logger
logger = set_system_logger("system_logger")

async def create_user(user_name: str, email: str, user_role: str, password: str): 
    logger.info("Getting DB connection pool for user creation")
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
        logger.info(f"Creating user {user_name} with email {email}")
        await connection.execute(
            """
            INSERT INTO core.users (username, email, user_role, password, created_at , is_active)
            VALUES ($1, $2, $3, crypt($4, gen_salt('bf')), now(), true)
            """,
            user_name, email, user_role, password
        )
        logger.info(f"User {user_name} created successfully.")
        return {"message": f"User created successfully. Username: {user_name}, Email: {email}"}

async def get_user(email: str):
    logger.info("Getting DB connection pool for fetching user")
    pool = await Database.get_pool()
    async with pool.acquire() as connection:
        logger.info(f"Fetching user with email: {email}")
        row = await connection.fetchrow(
            """
            SELECT user_id, username, email, user_role, created_at, is_active
            FROM core.users
            WHERE email = $1
            """,
            email,
        )
        if row:
            user_data = dict(
                user_id=str(row['user_id']),
                username=row['username'],
                email=row['email'],
                user_role=row['user_role'],
                created_at=row['created_at'],
                is_active=row['is_active']
            )
            logger.info(f"User data retrieved for email: {email}")
            return user_data
        else:
            logger.error(f"No user found with email: {email}")
            return None

async def update_user_password(email: str, new_password: str):
    logger.info("Getting DB connection pool for updating user password")
    pool = await Database.get_pool()
    async with pool.acquire() as connection:
        logger.info(f"Updating password for user with email: {email}")
        result = await connection.execute(
            """
            UPDATE core.users
            SET password = crypt($1, gen_salt('bf'))
            WHERE email = $2
            """,
            new_password, email
        )
        if result == "UPDATE 0":
            logger.error(f"No user found with email: {email} to update password.")
            return {"error": "No user found with the provided email."}
        logger.info(f"Password updated successfully for user with email: {email}")
        return {"message": "Password updated successfully."}

async def delete_user(email: str):
    logger.info("Getting DB connection pool for deleting user")
    pool = await Database.get_pool()
    async with pool.acquire() as connection:
        logger.info(f"Deleting user with email: {email}")
        result = await connection.execute(
            """
            UPDATE core.users 
            SET is_active = false            
            WHERE email = $1
            """,
            email
        )
        if result == "UPDATE 0":
            logger.error(f"No user found with email: {email} to delete.")
            return {"error": "No user found with the provided email."}
        logger.info(f"User with email: {email} deleted successfully.")
        return {"message": "User deleted successfully."}