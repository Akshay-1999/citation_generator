from fastapi import APIRouter , UploadFile , Depends
from utils.auth_utils import oauth2scheme,  get_user_details
from utils.logging_utils import set_system_logger

logger = set_system_logger("system_logger")


file_router = APIRouter(Depends = get_user_details)

@file_router.post("/upload_file")
async def upload_file(file_path: str , user_detail = get_user_details):
    user_email = get_user_details.get('emil')
    logger.info(f"started file processing for the user {user_email}")
    from routes.endpoint.filesendpoint import calculate_md5 , get_file_extension
    
