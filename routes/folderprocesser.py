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
import json
from datetime import datetime
import re

from routes.auth import login_required
from utils.logging_utils import set_system_logger
from routes.endpoint.filesendpoint import check_file_exists, log_file_upload, log_file_update, get_file_extension
from embedding.embedder import store_embeddings
from embedding.pinecone_index import delete_pinecone_index
from agents.agents_main import ResumeMappingAgent
from routes.endpoint.bulk_processing import process_resumes_to_excel
from document_processing.document_loader import MemoryEfficientFileloader
from db.config import Database
from agents.agent_utils import get_jd_analysis_system_prompt
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langsmith import traceable
from dotenv import load_dotenv

load_dotenv(override=True)  # loads .env from the current working directory

from utils.logger_instances import folder_processer_logger as logger

folder_processer_router = APIRouter()

@traceable(run_type="chain", name="Experiance_position_mapping_agent")
def process_query(query: str):
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"), temperature=0.0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", get_jd_analysis_system_prompt()),
        ("human", "{input}")
    ])
    chain = prompt | llm
    response = chain.invoke({
        "input": query
    })
    return response.content

# Resolve project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = "uploaded_files"
REPORTS_DIR = "screening_reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

def sanitize_filename(name: str) -> str:
    """Remove or replace characters that are unsafe for filenames."""
    # Replace spaces with underscores
    name = name.replace(" ", "_")
    # Remove any character that isn't alphanumeric, underscore, or hyphen
    return re.sub(r'[^\w\-]', '_', name)

def calculate_md5_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()

async def extract_text_from_attachment_jd(upload_file: UploadFile, user_id: str) -> str:
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
        
        logger.info(f"--- Extracting JD_content from temp file: {temp_path} ---")
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

async def analyze_jd(jd_text: str) -> Dict[str, Any]:
    """Use LLM to extract position, experience and client from JD."""
    try:
        client = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"), temperature=0.0)
        prompt = get_jd_analysis_system_prompt()
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Analyze this Job Description:\n\n{jd_text}"}
        ]
        response = await client.ainvoke(messages)
        # Handle potential markdown code blocks in LLM output
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()
        return json.loads(content)
    except Exception as e:
        logger.error(f"Error analyzing JD: {e}")
        return {"position": "Unknown Position", "experience": 0, "client_name": "Unknown"}


@folder_processer_router.get("/list_reports")
async def list_reports(session = Depends(login_required)):
    """List all past screening reports for the user."""
    if session is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id = session.get('user_id')
    pool = await Database.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, report_name, position, experience, client_name, created_at 
            FROM core.screening_batches 
            WHERE user_id = $1 
            and is_deleted = False
            ORDER BY created_at DESC
        """, uuid.UUID(user_id))
        
        return [{
            "id": str(r['id']),
            "report_name": r['report_name'],
            "position": r['position'],
            "experience": r['experience'],
            "client_name": r.get('client_name', 'Unknown'),
            "created_at": r['created_at'].isoformat()
        } for r in rows]

@folder_processer_router.put("/delete_report/{batch_id}")
async def delete_report(batch_id: str, session = Depends(login_required)):
    """Delete a screening report."""
    if session is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user_id = session.get('user_id')
    from routes.endpoint.bulk_processing import delete_batch
    result = await delete_batch(batch_id, user_id)
    if result:
        return {"message": "Report deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Report not found")

@folder_processer_router.get("/get_report_results/{batch_id}")
async def get_report_results(batch_id: str, session = Depends(login_required)):
    """Get screening results for a specific batch."""
    if session is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id = session.get('user_id')
    pool = await Database.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM core.bulk_screening_results 
            WHERE batch_id = $1 AND user_id = $2
        """, uuid.UUID(batch_id), uuid.UUID(user_id))
        
        results = []
        for r in rows:
            res = dict(r)
            res['id'] = str(res.get('id'))
            res['user_id'] = str(res.get('user_id'))
            res['batch_id'] = str(res.get('batch_id'))
            if isinstance(res.get('skills'), str):
                res['skills'] = [s.strip() for s in res['skills'].split(",") if s.strip()]
            if isinstance(res.get('matched_skills'), str):
                res['matched_skills'] = [s.strip() for s in res['matched_skills'].split(",") if s.strip()]
            results.append(res)
            
        return {"results": results, "batch_id": str(batch_id)}

@folder_processer_router.get("/download_report/{filename}")
async def download_report(filename: str, session = Depends(login_required)):
    """Serve a generated screening report."""
    if session is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    file_path = os.path.join(REPORTS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report not found")
        
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


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

    if jd_file:
        job_description = await extract_text_from_attachment_jd(jd_file, user_id)
    
    if not job_description: raise HTTPException(status_code=400, detail="No Job Description")

    # 🚀 STEP 1: Analyze JD to get Position, Experience and Client
    jd_analysis = await analyze_jd(job_description)
    position = jd_analysis.get("position", "Unknown Position")
    experience = jd_analysis.get("experience", 0)
    client_name = jd_analysis.get("client_name", "Unknown")

    # 🚀 STEP 2: Create Batch record
    from routes.endpoint.bulk_processing import create_screening_batch
    # Generate a descriptive report name
    date_str = datetime.now().strftime("%Y-%m-%d")
    clean_position = sanitize_filename(position)
    clean_client = sanitize_filename(client_name)
    report_name = f"{clean_client}_{clean_position}_{experience}_{date_str}"
    
    batch_id, report_name = await create_screening_batch(user_id, report_name, position, experience, client_name, job_description)

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_to_process = []
    file_to_map = []

    for uploaded_file in files:
        file_name = os.path.basename(uploaded_file.filename)

        # Skip Microsoft Word lock/temp files (e.g. ~$tuate_Kundanam.doc)
        if file_name.startswith('~$'):
            logger.info(f"--- Skipping Word lock file: {file_name} ---")
            continue

        extension = await get_file_extension(file_name)
        if extension is None: continue
        file_to_map.append(file_name)
        content = await uploaded_file.read()
        md5 = calculate_md5_bytes(content)
        file_exists = await check_file_exists(file_name, user_id)
        if file_exists:
            old_file_name, old_md5, old_file_path, old_file_id = file_exists
            if old_md5 == md5: continue
            filter_criteria = {"file_name": {"$in": [file_name]}, "user_id": {"$in": [user_id]}}
            await delete_pinecone_index(pinecone_filter=filter_criteria, namespace=f"estuate-data-{user_id}")
            with open(old_file_path, "wb") as f: f.write(content)
            await log_file_update(old_file_id, md5, len(content))
            file_to_process.append(old_file_path)
        else:
            new_file_path = os.path.join(UPLOAD_DIR, file_name)
            with open(new_file_path, "wb") as f: f.write(content)
            await log_file_upload(user_id, file_name, new_file_path, extension, len(content), md5)
            file_to_process.append(new_file_path)

    if file_to_process:
        await store_embeddings(specific_files=file_to_process, user_id=user_id, processing_mode="pymupdf4llm")

    try:
        output_filename = f"{report_name}.xlsx"
        output_path = os.path.join(REPORTS_DIR, output_filename)
        results = await process_resumes_to_excel(job_description, file_to_map, user_id, output_path, batch_id)
        
        return JSONResponse(content={
            "message": "Screening completed",
            "results": results,
            "report_name": report_name,
            "batch_id": str(batch_id),
            "download_url": f"/folder/download_report/{output_filename}"
        })
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))