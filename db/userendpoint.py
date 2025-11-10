from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

userrouter = APIRouter()  

@userrouter.post("/create_user")
async def create_user_endpoint(user_name: str, email: str, user_role: str, password: str):
    from db.endpoints.user import create_user
    try:
        result = await create_user(user_name, email, user_role, password)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))