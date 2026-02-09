# TODO: Load auth_token from environment variables instead of hardcoding
auth_token = os.getenv("AUTH_TOKEN")
from utils.auth_utils import auth_manger
import os
from dotenv import load_dotenv

load_dotenv()
secret_key = os.getenv("secret_key")
auth_manager_instance = auth_manger(secret_key=secret_key)

if auth_token:
    user_data = auth_manager_instance.validate_authtoken(auth_token)
    print(user_data)

    if user_data and user_data.get("authenticated"):
        user_id = user_data.get("user_id")
        print(user_id)
        authenticated = user_data.get("authenticated")
        print(authenticated)
    else:
        print("Invalid or expired token")
else:
    print("AUTH_TOKEN environment variable not set")

# from db.endpoints.auth import authenticate_user
# import asyncio

# async def test_authenticate():
#     email = "akshay.patil@estuate.com"
#     password = "akshay@123"
#     user_data = await authenticate_user(email, password)
#     if user_data:
#         print("Authentication successful")
#         print(user_data)
#     else:
#         print("Authentication failed")


# if __name__ == "__main__":
#     asyncio.run(test_authenticate())
