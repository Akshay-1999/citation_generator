from utils.auth_utils import auth_manger
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel,EmailStr
from typing import Optional
from dotenv import load_dotenv
from fastapi.responses import RedirectResponse, HTMLResponse
import os
from db.endpoints.auth import authenticate_user
from utils.logging_utils import set_system_logger
from fastapi import APIRouter, Request, Form,Depends, HTTPException,status


logger = set_system_logger("system_logger")

load_dotenv()
secret_key = os.getenv("secret_key")
auth_manager_instance = auth_manger(secret_key=secret_key)

auth_router = APIRouter()

class AuthRequest(BaseModel):
    email: EmailStr
    password: str

def set_secure_cookie(response, key: str, value: str, max_age: int = 3600):
    """Helper to set secure cookie with all security flags"""
    response.set_cookie(
        key=key,
        value=value,
        max_age=max_age,
        httponly=True,     # Prevent XSS - JavaScript cannot access
        secure=True,       # Only send over HTTPS
        samesite="lax",    # CSRF protection
        path="/"           # Available on all paths
    )


def login_required(request: Request):
    authenticated = getattr(request.state, "authenticated", False)
    user = getattr(request.state, "user", None)
    role = getattr(request.state, "role", None)
    return {"user": user, "role": role} if authenticated else None

@auth_router.post("/login")
async def login(auth_request: AuthRequest):
    try:
        user_data = await authenticate_user(auth_request.email, auth_request.password)
    except Exception as e:
        logger.error(f"Error during login attempt for email: {auth_request.email}, error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    if user_data is None:
        logger.warning(f"Failed login attempt for email: {auth_request.email}")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = auth_manager_instance.create_authtoken(user_data)
    response = RedirectResponse(url="/", status_code=302)
    set_secure_cookie(response, key="auth_token", value=token)
    return response



    
