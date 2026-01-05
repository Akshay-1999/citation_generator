from fastapi import APIRouter, HTTPException , Depends
from pydantic import BaseModel , EmailStr , Field
from typing import Optional , Literal
from utils.logging_utils import set_system_logger
from utils.auth_utils import oauth2scheme,  get_user_details
from db.endpoints.user import create_user

logger = set_system_logger("system_logger")

userrouter = APIRouter()  

class User(BaseModel):
    user_name: str = Field(..., example="john_doe")
    email: EmailStr = Field(..., example="john@example.com")
    user_role: str = Literal ["admin", "user", "guest"]
    password: str = Field(..., example="strongpassword123") 

@userrouter.post("/create_user")
async def create_user_endpoint(user: User, user_details = Depends(get_user_details)):
    from db.endpoints.user import create_user
    user_details_role = user_details.get("role")
    if user_details_role != "admin":
        logger.error(f"Unauthorized user creation attempt by user_id: {user_details.get('user_id')}")
        raise HTTPException(status_code=403, detail="Operation not permitted. Admin role required.")
    try:
        logger.info(f"Attempting to create user with email: {user.email}")
        result = await create_user(user.user_name, user.email, user.user_role, user.password)
        return result
    except Exception as e:
        logger.error(f"Error creating user with email {user.email}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@userrouter.get("/get_user/{email}")
async def get_user_endpoint(email: EmailStr , user_details = Depends(get_user_details)):
    if user_details.get("role") not in ["admin"]:
        logger.error(f"Unauthorized user fetch attempt by user_id: {user_details.get('user_id')}")
        raise HTTPException(status_code=403, detail="Operation not permitted.")
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

@userrouter.put("/update_password/{email}")
async def update_user_password_endpoint(email: EmailStr, new_password: str, user_details = Depends(get_user_details)):
    if user_details.get("role") not in ["admin", "user"]:
        logger.error(f"Unauthorized password update attempt by user_id: {user_details.get('user_id')}")
    if user_details.get("email") != email and user_details.get("role") != "admin":
        logger.error(f"User_id: {user_details.get('user_id')} attempted to change another user's password.")
        raise HTTPException(status_code=403, detail="Operation not permitted.")
    from db.endpoints.user import update_user_password
    try:
        logger.info(f"Updating password for user with email: {email}")
        result = await update_user_password(email, new_password)
        return result
    except Exception as e:
        logger.error(f"Error updating password for user with email {email}: {e}")
        raise HTTPException(status_code=500, detail=str(e))