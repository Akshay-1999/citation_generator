import shutil
from fastapi import APIRouter, HTTPException , UploadFile , Depends , Request , File
from routes.auth import login_required
from utils.logger_instances import file_logger as logger
from embedding.pinecone_index import delete_pinecone_index
import os
from pydantic import BaseModel
from typing import List, Dict, Any
from hashlib import md5


file_router = APIRouter()

@file_router.post("/upload")
async def upload_file(request: Request, file: UploadFile = File(...) , session = Depends(login_required)): 
    if session is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    else:
        user_id = session.get('user_id')
        user_email = session.get('email')
        logger.info(f"=== Started file upload for user: {user_email} ===")
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
            logger.error(f"=== Error reading file {file.filename} for user {user_email}: {e} ===")
            raise HTTPException(status_code=500, detail="Error processing file")
        await file.seek(0)
        mdf_checksum = md5_hash.hexdigest()
        file_size = file.size
        from routes.endpoint.filesendpoint import check_file_exists , get_file_extension
        extension = await get_file_extension(file.filename)
        if extension is None:
            logger.warning(f"=== User {user_email} attempted to upload a disallowed file type: {file.filename} ===")
            raise HTTPException(status_code=400, detail="File type not allowed")
        if extension:
            result = await check_file_exists(file.filename , user_id)
            if result is not None:
                old_file_name, old_md5, inner_file_path, file_id = result
                logger.info(f"--- Checking MD5: new={mdf_checksum} vs old={old_md5} ---")
                if mdf_checksum == old_md5:
                    logger.info("--- File with same name and content already exists ---")
                    raise HTTPException(status_code=400, detail="A file with the same name and data is already in the database")
                else:
                    logger.info("--- File with same name but different content detected ---")
                    # Remove the old file
                    if os.path.exists(inner_file_path):
                        logger.info(f"--- Removing old file for user {user_email}: {inner_file_path} ---")
                        os.remove(inner_file_path)
                        from embedding.pinecone_index import delete_pinecone_index
                        filter = {"file_name": {"$in": file.filename} , "user_id": {"$in": user_id}}
                        namespace = f"estuate-data-{user_id}"
                        await delete_pinecone_index(pinecone_filter=filter, namespace=namespace)
                        logger.info(f"--- Old file vectors removed successfully from namespace: {namespace} ---")
                    else:
                        logger.error(f"=== File not found for user {user_email}: {inner_file_path} ===")
                        raise HTTPException(status_code=404, detail="File not found")
                    with open(inner_file_path, "wb") as buffer:
                        shutil.copyfileobj(file.file, buffer)
                    from routes.endpoint.filesendpoint import log_file_update
                    await log_file_update(file_id=file_id , md5=mdf_checksum , file_size=file_size)
                    logger.info(f"--- File saved successfully for user {user_email} ---")
                    return {"filename": file.filename, "file_id": str(file_id), "md5": mdf_checksum, "size": file_size , "extension": extension , "message": "File updated successfully"}
            else:
                logger.info(f"--- No duplicate found for {file.filename}. Proceeding with upload ---")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"File saved successfully for user {user_email}: {file.filename}")
        from routes.endpoint.filesendpoint import log_file_upload
        file_id = await log_file_upload(
            user_id=user_id,
            filename=file.filename,
            file_path=file_path,
            extension=extension,
            file_size=file_size,
            md5=mdf_checksum
        )   
        from embedding.embedder import store_embeddings
        await store_embeddings(specific_files=[file_path], user_id=user_id)
        logger.info(f"=== File upload and embedding process completed for user {user_email} (ID: {file_id}): {file.filename} ===")
        return {"filename": file.filename, "file_id": file_id, "md5": mdf_checksum, "size": file_size , "extension": extension , "message": "File uploaded successfully."}
 
@file_router.get("/list_files")
async def list_files(session = Depends(login_required)):
    user_id = session["user_id"]
    from routes.endpoint.filesendpoint import get_user_files
    files = await get_user_files(user_id)
    return files

@file_router.delete("/delete_file/{file_id}")
async def delete_file(file_id: str, session = Depends(login_required)):
    user_id = session["user_id"]
    from routes.endpoint.filesendpoint import delete_file
    result = await delete_file(file_id, user_id)
    return result