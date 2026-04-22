import shutil
import tempfile
from fastapi import APIRouter, Request, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pathlib import Path
import uuid
import os
import hashlib

from routes.auth import login_required
from utils.logging_utils import set_system_logger
from routes.endpoint.filesendpoint import check_file_exists, log_file_upload, log_file_update, get_file_extension
from embedding.embedder import store_embeddings
from embedding.pinecone_index import delete_pinecone_index
from agents.agents_main import ResumeMappingAgent
from routes.endpoint.bulk_processing import process_resumes_to_excel
from document_processing.document_loader import MemoryEfficientFileloader

logger = set_system_logger("system_logger")
folder_processer_router = APIRouter()

# Resolve project root (two levels up from this file: routes/ -> project_root/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

UPLOAD_DIR = "uploaded_files"

def calculate_md5_bytes(data: bytes) -> str:
    """Calculate MD5 from raw bytes."""
    return hashlib.md5(data).hexdigest()

async def extract_text_from_upload(upload_file: UploadFile, user_id: str) -> str:
    """Save UploadFile to temp and extract text using the document loader."""
    content = await upload_file.read()
    if not content:
        return ""
    
    # Reset file pointer for any subsequent reads
    await upload_file.seek(0)
    
    suffix = Path(upload_file.filename).suffix.lower()
    temp_path = None
    try:
        # Use system temp directory for better reliability in production
        import tempfile
        temp_dir = os.path.join(tempfile.gettempdir(), "temp_jd_processing")
        os.makedirs(temp_dir, exist_ok=True)
        
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, dir=temp_dir, suffix=suffix) as tmp:
            temp_path = tmp.name
            tmp.write(content)
        
        logger.info(f"--- Extracting JD text from temp file: {temp_path} ---")
        loader = MemoryEfficientFileloader(user_id=user_id)
        extracted_text = ""
        async for doc in loader._process_file(temp_path, user_id=user_id, file_name=upload_file.filename):
            if doc.page_content:
                extracted_text += doc.page_content + "\n\n"
        
        if not extracted_text.strip():
             logger.warning(f"--- No text extracted from JD file: {upload_file.filename} ---")
             
        return extracted_text.strip()
    except Exception as e:
        logger.error(f"=== Error extracting JD text from {upload_file.filename}: {e} ===", exc_info=True)
        return ""
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as cleanup_err:
                logger.error(f"=== Error cleaning up temp JD file: {cleanup_err} ===")


@folder_processer_router.post("/process_folder")
async def process_folder(
    job_description: str = Form(...),
    files: List[UploadFile] = File(...),
    session = Depends(login_required),
    jd_file: Optional[UploadFile] = File(None)
):
    """
    Receive uploaded resume files + JD from the browser.
    - Saves new/updated files to uploaded_files/
    - Embeds any new or changed files
    - Runs bulk screening against the JD
    - Returns an Excel file with results
    """
    if session is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id = session.get('user_id')
    user_email = session.get('email')

    logger.info(f"=== Started folder processing for user: {user_email}, Files: {len(files)} ===")

    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    if not job_description and not jd_file:
        raise HTTPException(status_code=400, detail="No Job Description provided")

    if jd_file:
        job_description = await extract_text_from_upload(jd_file, user_id)
        logger.info(f"=== Extracted JD text: {job_description[:100]} ===")
        if not job_description:
             logger.warning(f"=== Failed to extract text from JD file: {jd_file.filename} ===")
        else:
            logger.info(f"=== Successfully extracted text from JD file: {jd_file.filename} ===")
    else:
        logger.info(f"=== Using JD from form data: {job_description} ===")
        job_description = job_description.strip()

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    file_to_process = []  # Files that need embedding (new or changed)
    file_to_map = []      # All file names for bulk screening

    for uploaded_file in files:
        # Strip folder prefix — browsers include it when using directory picker
        # e.g. "test/resume.pdf" → "resume.pdf"
        file_name = os.path.basename(uploaded_file.filename)
        
        # Check file extension
        extension = await get_file_extension(file_name)
        if extension is None:
            logger.warning(f"=== Skipping unsupported file: {file_name} ===")
            continue
        
        file_to_map.append(file_name)

        # Read file content
        content = await uploaded_file.read()
        file_size = len(content)
        md5 = calculate_md5_bytes(content)

        # Check if file already exists in DB
        file_exists = await check_file_exists(file_name, user_id)
        
        if file_exists:
            old_file_name, old_md5, old_file_path, old_file_id = file_exists
            if old_md5 == md5:
                logger.info(f"--- File unchanged, skipping: {file_name} ---")
                continue
            
            # File changed — delete old vectors and re-process
            filter_criteria = {"file_name": {"$in": [file_name]}, "user_id": {"$in": [user_id]}}
            namespace = f"estuate-data-{user_id}"
            await delete_pinecone_index(pinecone_filter=filter_criteria, namespace=namespace)
            
            try:
                file_path = old_file_path
                with open(file_path, "wb") as f:
                    f.write(content)
                await log_file_update(old_file_id, md5, file_size)
                file_to_process.append(file_path)
                logger.info(f"--- Updated existing file: {file_name} ---")
            except Exception as e:
                logger.error(f"=== Error updating file {file_name}: {e} ===")
                continue
        else:
            # New file — save to uploaded_files/
            new_file_path = os.path.join(UPLOAD_DIR, file_name)
            try:
                with open(new_file_path, "wb") as f:
                    f.write(content)
                await log_file_upload(user_id, file_name, new_file_path, extension, file_size, md5)
                file_to_process.append(new_file_path)
                logger.info(f"--- Saved new file: {file_name} ---")
            except Exception as e:
                logger.error(f"=== Error saving file {file_name}: {e} ===")
                continue

    # Embed new/changed files
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

        # Remove stale file from any previous run
        if os.path.exists(output_filename):
            os.remove(output_filename)
            logger.info(f"=== Removed stale output file: {output_filename} ===")

        if not file_to_map:
            logger.warning("=== No supported files found in the uploaded files ===")
            return JSONResponse(content={"message": "No supported files (PDF) found in the uploaded files."})

        logger.info(f"=== Starting bulk screening for {len(file_to_map)} files ===")
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