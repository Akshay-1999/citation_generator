from db.endpoints.auth import authenticate_user
from fastapi import HTTPException, Depends , APIRouter , status
from pydantic import BaseModel , EmailStr
from typing import Optional
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from utils.logging_utils import set_system_logger
import uuid
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt

logger = set_system_logger("system_logger")

oauth2scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
authrouter = APIRouter()

# Secret key
SECRET_KEY = uuid.uuid4().hex
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1


class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[str] = None
    role: Optional[str] = None

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@authrouter.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user_data = await authenticate_user(form_data.username, form_data.password)
    if not user_data:
        logger.error("Incorrect email or password during login attempt.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"user_id": (user_data['user_id']),
              "role": user_data['role'],
              "email": form_data.username
              }, expires_delta=access_token_expires
    )
    logger.info(f"Access token created for user_id: {user_data['user_id']}")
    return {"access_token": access_token, "token_type": "bearer"}

async def get_user_details(token: str = Depends(oauth2scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise credentials_exception