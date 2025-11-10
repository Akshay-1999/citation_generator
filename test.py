from db.config import Database

async def test_db_connection():
    pool = await Database.get_pool()
    async with pool.acquire() as connection:
        if connection is None:
            print("Failed to acquire a database connection.")
        else:
            print("Database connection acquired successfully.")
            row = await connection.fetchrow("SELECT * FROM CORE.USERS LIMIT 1;")
            print("Sample row from CORE.USERS:", row)
        result = await connection.fetchval("SELECT 1;")
        assert result == 1

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_db_connection())