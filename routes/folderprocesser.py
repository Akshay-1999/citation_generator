import hashlib
import os
import shutil
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pathlib import Path
import uuid

from routes.auth import login_required
from utils.logging_utils import set_system_logger
from routes.endpoint.filesendpoint import check_file_exists, log_file_upload, log_file_update, get_file_extension
from embedding.embedder import store_embeddings
from embedding.pinecone_index import delete_pinecone_index
from agents.agents_main import ResumeMappingAgent
from routes.endpoint.bulk_processing import process_resumes_to_excel

logger = set_system_logger("system_logger")
folder_processer_router = APIRouter()

class FolderProcesserRequest(BaseModel):
    folder_path: str
    job_description: Optional[str] = None

def calculate_md5(file_path: str) -> str:
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


async def scan_folder(folder_path):
    folder_data = {}
    for root, _, filenames in os.walk(folder_path):
        for file in filenames:
            extension = await get_file_extension(file)
            if extension is not None:
                file_data = {
                    "file_name" : file,
                    "file_path" : os.path.join(root, file),
                    "extension" : extension,
                    "md5" : calculate_md5(os.path.join(root, file)),
                    "file_size" : os.path.getsize(os.path.join(root, file))
                } 
            folder_data[file] = file_data
    return folder_data

async def write_file_to_folder(source_path: str, target_path: str) -> bool:
    try:
        shutil.copy2(source_path, target_path)
        return True
    except Exception as e:
        logger.error(f"=== Error copying file from {source_path} to {target_path}: {e} ===")
        return False

@folder_processer_router.post("/process_folder")
async def process_folder(folder_request: FolderProcesserRequest, session = Depends(login_required)):
    if session is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id = session.get('user_id')
    user_email = session.get('email')
    folder_path = folder_request.folder_path
    job_description = folder_request.job_description
    if job_description is None:
        raise HTTPException(status_code=400, detail="Job description is required")

    logger.info(f"=== Started folder processing for user: {user_email}, Path: {folder_path} ===")
    file_to_process = []
    file_to_map = []
    folder_data = await scan_folder(folder_path)
    for file in folder_data.values():
        file_name = file["file_name"]
        file_to_map.append(file_name)
        file_path = file["file_path"]
        extension = file["extension"]
        md5 = file["md5"]
        file_size = file["file_size"]
        
        file_exists = await check_file_exists(file_name, user_id)
        if file_exists:
            old_file_name, old_md5, old_file_path, old_file_id = file_exists
            if old_md5 == md5:
                continue
            
            filter = {"file_name": {"$in": [file_name]}, "user_id": {"$in": [user_id]}}
            namespace = f"estuate-data-{user_id}"
            await delete_pinecone_index(pinecone_filter=filter, namespace=namespace)
            
            try:
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)
                if await write_file_to_folder(file_path, old_file_path):
                    await log_file_update(old_file_id, md5, file_size)
                    file_to_process.append(old_file_path)
            except Exception as e:
                logger.error(f"=== Error updating file {file_name}: {e} ===")
                continue
        else:
            UPLOAD_DIR = "uploaded_files"
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            new_file_path = os.path.join(UPLOAD_DIR, file_name)
            try:    
                if await write_file_to_folder(file_path, new_file_path):
                    await log_file_upload(user_id, file_name, new_file_path, extension, file_size, md5)
                    file_to_process.append(new_file_path)
            except Exception as e:
                logger.error(f"=== Error uploading file {file_name}: {e} ===")
                continue

    try:
        if file_to_process:
            logger.info(f"=== Starting embedding process for {len(file_to_process)} files ===")
            await store_embeddings(specific_files=file_to_process, user_id=user_id, processing_mode="pymupdf4llm")
            logger.info(f"=== Embedding process completed for {len(file_to_process)} files ===")
    except Exception as e:
        logger.error(f"=== Error during embedding process: {e} ===")
        raise HTTPException(status_code=500, detail=f"Error embedding files: {str(e)}")

    # Bulk Screening Logic
    try:
        output_filename = f"bulk_screening_{user_id[:8]}.xlsx"
        await process_resumes_to_excel(job_description, file_to_map, user_id, output_filename)
        
        if os.path.exists(output_filename):
            return FileResponse(
                path=output_filename,
                filename=output_filename,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            return JSONResponse(content={"message": "Processing completed but no candidates were found/mapped."})
    except Exception as e:
        logger.error(f"=== Error during bulk screening: {e} ===")
        raise HTTPException(status_code=500, detail=f"Error mapping resumes: {str(e)}")


    
            

    
    
    