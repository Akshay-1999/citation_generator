
auth_token='.eJwVzkeSgkAAAMC_eLcKUdLBw5AGyUjmQiGyhIFByfD63e0X9KkE__hPmavZ4WOobQds9460lzMHJRY4Vsvw7pyqVW3kvTIE9foiiq_3mDTmraAm8Y0ZvPrkkVolmt-bw1PsT0kKCTknFSl8GQ_FVvNBjWPul4z1ehtBAbfOHu41V1DZ7uNLmCqS3OW25kSq5khBNxuolZrVIKFP0W0i0jMuKku5Wed3vknpWbaJj_AwgSsGnPKsrsp29dDnwDU-WlRYy1aoOsZAzC04BHnkwukpAvOvwpdFxkOWimxCjJ8yC1E58OPoUqR5pDw4_LWnmXAXpoWPV_rVYQ_WeiSRIEUhQ0_FMChaiY7-O747w-IIVrrZ0a7GJAHGwKw648U18aLLpe4Rsn7JW_EL7vfTLwfyeF4.aYHCWg.wnFJZKs4OBPbqMNv_ZKM2e96Iu4'
#auth_token = '.eJwVwUmSgjAAAMC_eLcKRYwc5pBIACERkEXhQhGXQBBZVBjy-qnpXnD4D3WcNXzz7Q4vNuldKOKSh0hE2bhv4ogchdka63dNYQvyyK2VB7qOppk2hWS2e2KG-Sz7qr-R6-mT3fLRV8T0OdhFNUE-0MZIQvdoecBdPuJWlKDMxJKJUrtnplA_UHnqrNS3XOqrnt0kIIkWBZ6UaZ7uJ8ga0nGS5Uw4m-z7VEsk8T343SrGjkrVp2rtDLboM48W2cyR0q4suJ_n43fG1kRDWyOon0wSmWdQ4xNzim0TfAISq-fXwQFoNSAYpSLgdkj50OqOQc5XfKLoEsjOGPGojTvgEP_r95bHtIsdveFAEe7WuIxoXoVJDI7-IxmgkO0Ggrdh1FXrTTgJnzzARJ9-fhZ_mRZ4ow.aYG5oA.WEAR0cCHxQ0Em1aVi12Td3fHxVI'
#auth_token = '.eJwVwdvWQkAYANB36d5aYRQXXQwKIcKH5qalciqnUmN4-n_9e69K_E8dSgJbvT09nX0dHLemXtOwOmMvk_tf3qm1u6-GvNS-T9qMrbUu6t5w7db0L9GD0fMigyByAzp77HBStXo0QyXNuk0olFOat0nA6CYA3Wq4eNqDjvpPmpxG1FVYyIJUbWmevCzfBxkGMpK4myb5DZWUcPccnZpNDIvdk1F7O5hpy_eFx4InkEtk4ulywYUvrjtaeNegdYjwMa4FEKnsuTKzDNcUWQXD_aw4kXkPayPC8w-hW8HTeQPxOG4z9YhsB7V2_IBLuliSCSp6l8HFvX0xVXypFisxZi3d6pLvLRZMKstAYXKiOC8jKrAzUz72gvs8iVxNhBvkNIussKGUfQ6li3e71R_98nkH.aYGVOw.AMULxQdt66v3aNcDjGzyjOrxxDM'
from utils.auth_utils import auth_manger
import os
from dotenv import load_dotenv

load_dotenv()
secret_key = os.getenv("secret_key")
auth_manager_instance = auth_manger(secret_key=secret_key)
user_data = auth_manager_instance.validate_authtoken(auth_token)
print(user_data)

if user_data and user_data.get("authenticated"):
    user_id = user_data.get("user_id")
    print(user_id)
    authenticated = user_data.get("authenticated")
    print(authenticated)
else:
    print("Invalid or expired token")

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
