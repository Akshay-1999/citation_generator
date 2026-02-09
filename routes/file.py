import shutil
from fastapi import APIRouter, HTTPException , UploadFile , Depends , Request , File
from routes.auth import login_required
from utils.logging_utils import set_system_logger
import os
from hashlib import md5
logger = set_system_logger("system_logger")


file_router = APIRouter()

@file_router.post("/upload_file")
async def upload_file(request: Request, file: UploadFile = File(...) , session = Depends(login_required)): 
    if session is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    else:
        user_id = request.state.user
        user_email = request.state.email
        logger.info(f"started file upload for the user {user_email}")
        UPLOAD_DIR = "uploaded_files"
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        md5_hash = md5()
        try:
            while True:
                contents = await file.read(1024 * 1024)  # Read in 1MB chunks
                if not contents:
                    break
                md5_hash.update(contents)
        except Exception as e:
            logger.error(f"Error reading file {file.filename} for user {user_email}: {e}")
            raise HTTPException(status_code=500, detail="Error processing file")
        mdf_checksum = md5_hash.hexdigest()
        file_size = file.size
        from routes.endpoint.filesendpoint import check_file_exists , get_file_extension
        extension = await get_file_extension(file.filename)
        if extension is None:
            logger.warning(f"User {user_email} attempted to upload a file with disallowed extension: {file.filename}")
            raise HTTPException(status_code=400, detail="File type not allowed")
        if extension:
            check_file_exists = await check_file_exists(file.filename , mdf_checksum , user_id)
            if check_file_exists == True:
                logger.info(f"User {user_email} attempted to upload a duplicate file: {file.filename}")
                raise HTTPException(status_code=400, detail="File with same name and content already exists")
            logger.info(f"No duplicate found for file {file.filename} uploaded by user {user_email}. Proceeding with upload.")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"File saved successfully for user {user_email}: {file.filename}")
        from routes.endpoint.filesendpoint import log_file_upload
        await log_file_upload(
            user_id=user_id,
            filename=file.filename,
            file_path=file_path,
            extension=extension,
            file_size=file_size,
            md5=mdf_checksum
        )   
        logger.info(f"File upload process completed for user {user_email}: {file.filename}")
        return {"filename": file.filename, "md5": mdf_checksum, "size": file_size , "extension": extension , "message": "File uploaded successfully will let you know once the processing is done"}


