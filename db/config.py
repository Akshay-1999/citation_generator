from dotenv import load_dotenv
import asyncpg
import os
import asyncpg
import json
import asyncio
import ssl
from utils.logger_instances import db_logger as logger


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
            # Robust SSL handling: Default to False, only True if explicitly set to 'production' 
            # and host is not localhost. Local Postgres typically rejects SSL.
            use_ssl = (ENV == "production" and DB_HOST not in ["localhost", "127.0.0.1"])
            
            ssl_context = None
            if use_ssl:
                if logger:
                    logger.info("=== Using SSL for Database Connection ===")

                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
            cls._pool = await asyncpg.create_pool(
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                min_size=2,
                max_size=10,
                ssl=ssl_context,
                statement_cache_size=0
            )
        return cls._pool
    @classmethod
    async def close_pool(cls):
        if cls._pool:
            await cls._pool.close()
            cls._pool = None   
