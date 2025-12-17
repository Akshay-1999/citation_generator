from fastapi import APIRouter, HTTPException , Depends
from pydantic import BaseModel , EmailStr , Field
from typing import Optional
from utils.logging_utils import set_system_logger
from utils.auth_utils import oauth2scheme 
# from utils.auth_utils import get_user_details

logger = set_system_logger("system_logger")

userrouter = APIRouter(dependencies=[Depends(oauth2scheme)])  

class User(BaseModel):
    user_name: str = Field(..., example="john_doe")
    email: EmailStr = Field(..., example="john@example.com")
    user_role: str = Field(..., example="admin")
    password: str = Field(..., example="strongpassword123")
    
@userrouter.post("/create_user")
async def create_user_endpoint(user: User ):
    from db.endpoints.user import create_user
    # if not login:
    #     raise HTTPException(status_code=401, detail="Unauthorized")
    # if token['access_token_role'] != 'admin':
    #     raise HTTPException(status_code=403, detail="Forbidden: Admin access required")
    try:
        logger.info(f"Attempting to create user with email: {user.email}")
        result = await create_user(user.user_name, user.email, user.user_role, user.password)
        return result
    except Exception as e:
        logger.error(f"Error creating user with email {user.email}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@userrouter.get("/get_user/{email}")
async def get_user_endpoint(email: EmailStr):
    from db.endpoints.user import get_user
    try:
        logger.info(f"Fetching user with email: {email}")
        user_data = await get_user(email)
        if user_data:
            return user_data
        else:
            raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logger.error(f"Error fetching user with email {email}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        