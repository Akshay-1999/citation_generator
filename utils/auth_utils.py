from db.endpoints.auth import authenticate_user
from fastapi import HTTPException, Depends , APIRouter , status
from pydantic import BaseModel , EmailStr
from typing import Optional
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from db.endpoints.user import get_user
from utils.logging_utils import set_system_logger

logger = set_system_logger("system_logger")

oauth2scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

class UserIn(BaseModel):
    email: EmailStr
    password: str

# class Authresponse (BaseModel):
#     user_id: str
#     role: str
#     hashed_password: str
#     # is_active: bool


authrouter = APIRouter()

@authrouter.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    logger.info(f"Received authentication request for user: {form_data.username}")
    user_data = await authenticate_user(email=form_data.username, password=form_data.password)
    if isinstance(user_data, str):
        logger.error(f"Authentication failed for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    logger.info(f"Authentication successful for user: {form_data.username}")
    return {"access_token_username": user_data['user_id'] , "access_token_role": user_data['role'], "token_type": "bearer"}

