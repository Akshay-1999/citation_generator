from fastapi import APIRouter, HTTPException

mainrouter = APIRouter()

@mainrouter.get("/")
async def status():
    return {"status": "API is running"}