from fastapi import APIRouter, Depends, HTTPException 
from pydantic import BaseModel , EmailStr , Field
from typing import Optional
from utils.logging_utils import set_system_logger
from utils.auth_utils import ALGORITHM, SECRET_KEY, oauth2scheme,  get_user_details
logger = set_system_logger("system_logger")
import uuid
from jose import jwt

# Secret key
# SECRET_KEY = uuid.uuid4().hex
# ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = 30 

test_router = APIRouter(dependencies=[Depends(oauth2scheme)]) 

@test_router.get("/test")
async def test_endpoint(user_details = Depends(get_user_details)):  
    user_details_role = user_details.get("role")

    return {"message": "Test endpoint is working!", "user_details_user_name": user_details.get("user_id"), "role": user_details_role}