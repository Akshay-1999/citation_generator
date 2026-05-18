import asyncio
from db.config import Database

async def run():
    pool = await Database.get_pool()
    async with pool.acquire() as conn:
        try:
            await conn.execute("ALTER TABLE core.bulk_screening_results ADD COLUMN matched_skills TEXT;")
            print("Column matched_skills added successfully.")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(run())
