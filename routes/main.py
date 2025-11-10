from fastapi import APIRouter, HTTPException

mainrouter = APIRouter()

@mainrouter.get("/status")
async def status():
    return {"status": "API is running"}