from dotenv import load_dotenv
import asyncpg
import os
import asyncpg
import json
import asyncio
import ssl

load_dotenv()
DB_USER = os.getenv("db_user")
DB_PASSWORD = os.getenv("db_password")
DB_HOST = os.getenv("db_host")
DB_PORT = os.getenv("db_port")
DB_NAME = os.getenv("db_name")
ENV = os.getenv("ENV")

# print("Database URL:", DATABASE_URL)  # For debugging purposes only; remove in production

class Database:
    _pool = None
    @classmethod
    async def get_pool(cls):
        if cls._pool is None:
            use_ssl = False if ENV == "local" else True
            ssl_context = None
            if use_ssl:
                ssl_context = ssl.create_default_context()
                
            cls._pool = await asyncpg.create_pool(
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                min_size=2,
                max_size=10,
                ssl=ssl_context
            )
        return cls._pool
    @classmethod
    async def close_pool(cls):
        if cls._pool:
            await cls._pool.close()
            cls._pool = None   
