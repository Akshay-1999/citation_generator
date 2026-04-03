import asyncio
import os
import sys

# Add current directory to path so we can import db.config
sys.path.append(os.getcwd())

from db.config import Database

async def migrate():
    print("--- Starting Database Migration ---")
    pool = await Database.get_pool()
    async with pool.acquire() as conn:
        try:
            print("--- Adding columns to core.document_chunks ---")
            await conn.execute("""
                ALTER TABLE core.document_chunks 
                ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL,
                ADD COLUMN IF NOT EXISTS modified_at TIMESTAMPTZ DEFAULT now(),
                ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT false;
            """)
            print("=== Migration Successful ===")
        except Exception as e:
            print(f"=== Migration Failed: {e} ===")
        finally:
            await Database.close_pool()

if __name__ == "__main__":
    asyncio.run(migrate())
