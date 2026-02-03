from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from cryptography.fernet import Fernet
import json
import secrets
import hashlib
import base64
import time
from typing import Optional
import os
from utils.logging_utils import set_system_logger

logger = set_system_logger("system_logger")


class auth_manger:
    def __init__(self , secret_key: str , max_age: int = 3600):
        self.serializer = URLSafeTimedSerializer(secret_key)
        self.max_age = max_age  
        key_material = hashlib.sha256(secret_key.encode()).digest()
        self.cipher = Fernet(base64.urlsafe_b64encode(key_material))

    def create_authtoken(self , userdata: dict=None) -> str:
        if userdata:
            data_json = json.dumps(userdata).encode()
            encrypted_data = self.cipher.encrypt(data_json)
            token = self.serializer.dumps(encrypted_data.decode())
            return token
        else:
            logger.error("Invalid userdata provided for token creation.")
            return None
        
    def validate_authtoken(self , token: str) -> Optional[dict]:
        try:
            encrypted_data = self.serializer.loads(token, max_age=self.max_age)
            decrpted_data = self.cipher.decrypt(encrypted_data.encode())
            return json.loads(decrpted_data.decode())
        except (BadSignature, SignatureExpired, Exception) as e:
            logger.error(f"Token validation error: {e}")
            return None

