import asyncio
from utils.logging_utils import set_system_logger
# from utils.auth_utils import get_user_details 
from db.endpoints.auth import authenticate_user
from pydantic import BaseModel
import json


class user_out(BaseModel):
    user_id: str
    role: str
    email: str

def return_res():
    val = dict(user_id='abc', role='dfr', email='test@example.com')
    return user_out(**val)

if __name__ == "__main__":
    val = return_res()
    print(val)