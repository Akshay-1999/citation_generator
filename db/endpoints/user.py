from pydantic import BaseModel
from typing import Optional
from db.config import Database

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
            return {"error": "User with this email already exists."}
        await connection.execute(
            """
            INSERT INTO core.users (username, email, user_role, password)
            VALUES ($1, $2, $3, crypt($4, gen_salt('bf')))
            """,
            user_name, email, user_role, password
        )
        return {"message": f"User created successfully."}
