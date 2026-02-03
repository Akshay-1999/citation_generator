from itsdangerous import URLSafeTimedSerializer , BadSignature , SignatureExpired  
from cryptography.fernet import Fernet
import json
import secrets
import hashlib
import base64
import time
from typing import Optional
import os

#class to manage token generation and validation

class auth_manger:

    def __init__(self , secret_key: str , max_age: int = 3600):
        self.serializer = URLSafeTimedSerializer(secret_key)
        self.max_age = max_age  
        key_material = hashlib.sha256(secret_key.encode()).digest()
        self.cipher = Fernet(base64.urlsafe_b64encode(key_material))      

    def create_authtoken(self , userdata: dict) -> str:    
        token_data = {
            **userdata,
            "jti": secrets.token_hex(16),
            "issued_at": time.time()
        }                      

