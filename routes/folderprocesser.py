import shutil
import tempfile
from fastapi import APIRouter, Request, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.encoders import jsonable_encoder
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
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langsmith import traceable
from dotenv import load_dotenv

load_dotenv(override=True)  # loads .env from the current working directory

from utils.logger_instances import folder_processer_logger as logger

folder_processer_router = APIRouter()

@traceable(run_type="chain", name="Experiance_position_mapping_agent")
def process_query(query: str):
    llm = ChatAnthropic(
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929"),
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        temperature=0.0,
        max_tokens=4096
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", get_jd_analysis_system_prompt()),
        ("human", "{input}")
    ])
    chain = prompt | llm
    response = chain.invoke({
        "input": query
    })
    content = response.content
    if isinstance(content, list):
        content = "".join(item.get("text", str(item)) if isinstance(item, dict) else str(item) for item in content)
    return str(content).strip()

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

def serialize_screening_result(r: Any) -> dict:
    """Safely convert a DB row from core.bulk_screening_results into a JSON-serializable dict."""
    res = dict(r)
    record_id = res.get('processing_id') or res.get('id')
    res['id'] = str(record_id) if record_id else str(uuid.uuid4())
    res['processing_id'] = res['id']
    if res.get('user_id') is not None:
        res['user_id'] = str(res['user_id'])
    if res.get('batch_id') is not None:
        res['batch_id'] = str(res['batch_id'])
    if res.get('created_at') is not None:
        res['created_at'] = res['created_at'].isoformat() if hasattr(res['created_at'], 'isoformat') else str(res['created_at'])
    res['username'] = res.get('username') or 'Unknown'
    if isinstance(res.get('skills'), str):
        res['skills'] = [s.strip() for s in res['skills'].split(",") if s.strip()]
    elif not isinstance(res.get('skills'), list):
        res['skills'] = []
    if isinstance(res.get('matched_skills'), str):
        res['matched_skills'] = [s.strip() for s in res['matched_skills'].split(",") if s.strip()]
    elif not isinstance(res.get('matched_skills'), list):
        res['matched_skills'] = []
    return res

async def extract_text_from_attachment_jd(upload_file: Any, user_id: str = "default_user") -> str:
    """Save UploadFile to temp (or read from path) and extract text using the document loader."""
    if not upload_file:
        return ""

    # If already a string path or direct text
    if isinstance(upload_file, str):
        if os.path.exists(upload_file):
            try:
                loader = MemoryEfficientFileloader(user_id=user_id)
                extracted_text = ""
                async for doc in loader._process_file(upload_file, user_id=user_id, file_name=os.path.basename(upload_file)):
                    if doc.page_content:
                        extracted_text += doc.page_content + "\n\n"
                return extracted_text.strip()
            except Exception as e:
                logger.error(f"Error extracting text from path {upload_file}: {e}")
                return ""
        # If it's already plain text content
        return upload_file.strip()

    content = await upload_file.read()
    if not content:
        return ""
    
    # Reset file pointer for any subsequent reads
    await upload_file.seek(0)
    
    filename = getattr(upload_file, 'filename', 'document.txt')
    suffix = Path(filename).suffix.lower() if filename else ".txt"
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
        async for doc in loader._process_file(temp_path, user_id=user_id, file_name=filename):
            if doc.page_content:
                extracted_text += doc.page_content + "\n\n"
        
        if not extracted_text.strip():
             logger.warning(f"--- No text extracted from JD file: {filename} ---")
        return extracted_text.strip()
    except Exception as e:
        logger.error(f"=== Error extracting JD text from {filename}: {e} ===", exc_info=True)
        return ""
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as cleanup_err:
                logger.error(f"=== Error cleaning up temp JD file: {cleanup_err} ===")

# async def analyze_jd(jd_text: str) -> Dict[str, Any]:
#     """Use LLM to extract position, experience and client from JD."""
#     try:
#         client = ChatAnthropic(
#             model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929"),
#             api_key=os.getenv("ANTHROPIC_API_KEY"),
#             temperature=0.0,
#             max_tokens=4096
#         )
#         prompt = get_jd_analysis_system_prompt()
#         messages = [
#             {"role": "system", "content": prompt},
#             {"role": "user", "content": f"Analyze this Job Description:\n\n{jd_text}"}
#         ]
#         response = await client.ainvoke(messages)
#         # Handle potential markdown code blocks in LLM output
#         content = response.content
#         if isinstance(content, list):
#             content = "".join(item.get("text", str(item)) if isinstance(item, dict) else str(item) for item in content)
#         content = str(content)
#         if "```json" in content:
#             content = content.split("```json")[1].split("```")[0].strip()
#         elif "```" in content:
#             content = content.split("```")[1].strip()
#         return json.loads(content)
#     except Exception as e:
#         logger.error(f"Error analyzing JD: {e}")
#         return {"position": "Unknown Position", "experience": 0, "client_name": "Unknown"}

@folder_processer_router.get("/list_reports")
async def list_reports(session = Depends(login_required)):
    """List all past screening reports for the user."""
    if session is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    pool = await Database.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, report_name, position, experience, client_name, created_at 
            FROM core.screening_batches 
            WHERE is_deleted = False
            ORDER BY created_at DESC
        """)
        
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
    """Delete a screening report (admin only)."""
    if session is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user_role = session.get('role') if isinstance(session, dict) else None
    if user_role != 'admin':
        raise HTTPException(status_code=403, detail="Operation not permitted. Only administrators can delete screening reports.")
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
            WHERE batch_id = $1
            ORDER BY created_at DESC
        """, uuid.UUID(batch_id))
        
        results = [serialize_screening_result(r) for r in rows]
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
    client_name: Optional[str] = Form(None),
    experience: Optional[str] = Form(None),
    total_year_of_experience: Optional[str] = Form(None),
    report_name: Optional[str] = Form(None),
    position: Optional[str] = Form(None),
    job_id: Optional[str] = Form(None),
    batch_name: Optional[str] = Form(None),
    username: Optional[str] = Form(None),
    user_name: Optional[str] = Form(None),
    # jd_file: Optional[UploadFile] = File(None)
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
    user_email = session.get('email') if isinstance(session, dict) else None
    resolved_username = username or user_name or (session.get('username') if isinstance(session, dict) else None) or (user_email.split('@')[0] if user_email else 'Unknown')

    # if jd_file:
    #     job_description = await extract_text_from_attachment_jd(jd_file, user_id)
    
    if not job_description: raise HTTPException(status_code=400, detail="No Job Description")

    # Extract metadata from incoming Form or fallback to session/defaults
    batch_id = job_id or session.get('job_id')

    # Look up canonical batch info from core.screening_batches if batch_id is provided
    # so every user always opens and appends to the exact same report file
    if batch_id:
        try:
            pool = await Database.get_pool()
            async with pool.acquire() as conn:
                batch_row = await conn.fetchrow(
                    "SELECT report_name, position, client_name, experience FROM core.screening_batches WHERE id = $1 LIMIT 1",
                    uuid.UUID(batch_id)
                )
                if batch_row and batch_row.get("report_name"):
                    report_name = batch_row["report_name"]
                    if not position or position == "Unknown Position":
                        position = batch_row.get("position") or position
                    if not client_name or client_name == "Unknown Client":
                        client_name = batch_row.get("client_name") or client_name
                    if not experience:
                        experience = batch_row.get("experience") or experience
        except Exception as lookup_err:
            logger.warning(f"Could not lookup report_name for batch_id {batch_id}: {lookup_err}")

    raw_report_name = report_name or batch_name or (session.get('report_name') if isinstance(session, dict) else None) or f"Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    clean_report_name = str(raw_report_name)[:-5] if str(raw_report_name).endswith('.xlsx') else str(raw_report_name)
    report_name = clean_report_name
    position = position or session.get('position') or "Unknown Position"
    experience = total_year_of_experience or experience or session.get('total_year_of_experience') or 0
    client_name = client_name or session.get('client_name') or "Unknown Client"

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
        results = await process_resumes_to_excel(
            job_description=job_description,
            file_names=file_to_map,
            user_id=user_id,
            output_file=output_path,
            username=resolved_username,
            batch_id=batch_id
        )

        # Retrieve all cumulative results for this batch from DB so UI displays both existing and new candidates
        if batch_id:
            try:
                pool = await Database.get_pool()
                async with pool.acquire() as conn:
                    rows = await conn.fetch("""
                        SELECT * FROM core.bulk_screening_results 
                        WHERE batch_id = $1
                        ORDER BY created_at DESC
                    """, uuid.UUID(batch_id))
                    
                    if rows:
                        results = [serialize_screening_result(r) for r in rows]
            except Exception as fetch_err:
                logger.warning(f"Could not fetch cumulative results for batch {batch_id}: {fetch_err}")
        
        return JSONResponse(content=jsonable_encoder({
            "message": "Screening completed",
            "results": results,
            "report_name": report_name,
            "batch_id": str(batch_id) if batch_id else None,
            "download_url": f"/folder/download_report/{output_filename}"
        }))
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))