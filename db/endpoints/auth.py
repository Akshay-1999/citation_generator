from db.config import Database
import asyncio


async def authenticate_user(email: str, password: str) -> str:
    pool = await Database.get_pool()
    try:
        async with pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                SELECT user_id, password , user_role
                FROM core.users
                WHERE email = $1
                AND password = crypt($2, password);
                """,
                email,
                password,
            )
            if row:
                return row['user_id'], row['password'], row['user_role']
            else:
                return "Authentication failed."
    except Exception as e:
        print(f"Error during authentication: {e}")
