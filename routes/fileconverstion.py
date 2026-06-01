from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Depends
from fastapi.responses import FileResponse
from routes.auth import login_required
from db.config import Database
from pydantic import BaseModel
import shutil
import uuid
from pathlib import Path
from typing import Optional

from utils.logger_instances import file_convert_logger as logger

fileconversionrouter = APIRouter()

# ── Directory setup ───────────────────────────────────────────────────────────

base_dir = Path(__file__).resolve().parent.parent
converted_pdf_dir = base_dir / "converted_resumes"/"converted_pdf"
converted_docx_dir = base_dir / "converted_resumes"/"converted_docx"
converted_json_dir = base_dir / "converted_resumes"/"converted_json"
uploaded_dir = base_dir / "uploaded_files"
templates_dir = base_dir / "templates"

for _d in (converted_pdf_dir,converted_docx_dir, converted_json_dir, uploaded_dir, templates_dir):
    _d.mkdir(parents=True, exist_ok=True)

# Fixed company template — place the DOCX at templates/Estuate_Template_main.docx
TEMPLATE_DOCX = templates_dir / "Estuate_Template_main.docx"


# ── Pydantic request models ───────────────────────────────────────────────────

class ConvertRequest(BaseModel):
    original_file: str
    candidate_name: Optional[str] = "Candidate"


class RejectRequest(BaseModel):
    original_file: str
    feedback: str


# ── Endpoints ─────────────────────────────────────────────────────────────────
@fileconversionrouter.post("/convert")
async def convert_resume(request: ConvertRequest, session=Depends(login_required)):
    """
    Convert a resume to the company template format using GPT-4o + ReportLab.

    1. Auth guard.
    2. Cache check — if already converted, return cached URL immediately.
    3. Resolve file paths and validate they exist.
    4. Run conversion in a thread (CPU-bound / blocking I/O).
    5. Persist result to DB.
    6. Return download URL.
    """
    if session is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user_id = session.get("user_id")
    original_file = request.original_file.strip()
    candidate_name = (request.candidate_name or "Candidate").strip()

    if not original_file:
        raise HTTPException(status_code=400, detail="original_file is required")

    logger.info(f"=== Convert request: user={user_id}, file={original_file} ===")

    # ── Step 1: Cache check ──────────────────────────────────────────────────
    from routes.endpoint.fileconverstionendpoint import check_converted_status
    cached = await check_converted_status(user_id, original_file)
    if cached:
        # cached holds the converted file path; extract just the filename for the URL
        cached_filename_pdf = Path(cached["pdf_file_path"]).name
        cached_filename_docx = Path(cached["docx_file_path"]).name
        filename_base = Path(cached["pdf_file_path"]).stem
        logger.info(f"--- Cache hit: returning {cached_filename_pdf} and {cached_filename_docx} ---")
        
        import json
        content_data = None
        json_path_str = cached.get("converted_json_file_path")
        if json_path_str:
            json_path = Path(json_path_str)
            if json_path.exists():
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        content_data = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading cached JSON from {json_path}: {e}")

        return {
            "message": "Resume already converted (cached).",
            "converted_pdf_file_path": cached_filename_pdf,
            "converted_docx_file_path": cached_filename_docx,
            "uuid": filename_base,
            "pdf_download_url": f"/conversion/api/download/{filename_base}?format=pdf",
            "docx_download_url": f"/conversion/api/download/{filename_base}?format=docx",
            "preview_url": f"/conversion/api/preview/{filename_base}",
            "content": content_data
        }

    # ── Step 2: Resolve source resume ────────────────────────────────────────
    resume_path = uploaded_dir / original_file
    if not resume_path.exists():
        logger.error(f"=== Resume file not found on disk: {resume_path} ===")
        raise HTTPException(
            status_code=404,
            detail=f"Resume file '{original_file}' not found. "
                   "Please upload the file first",
        )

    # ── Step 3: Validate template ─────────────────────────────────────────────
    if not TEMPLATE_DOCX.exists():
        logger.error(f"=== Company template DOCX missing: {TEMPLATE_DOCX} ===")
        raise HTTPException(
            status_code=503,
            detail="Company template DOCX not configured on the server. "
                   f"Please place the template at: templates/Estuate_Template_main.docx",
        )

    # ── Step 4: Prepare output path ───────────────────────────────────────────
    # Replace spaces with underscores so the filename is URL-safe
    safe_name = Path(original_file).stem.replace(" ", "_")
    filename_base = f"Estuate_{safe_name}"

    # ── Step 5: Run conversion (async — awaited directly) ────────────────────
    import asyncio
    max_retries = 2
    try:
        from document_processing.docxtpl_converter import run_docxtpl_conversion
        for attempt in range(max_retries + 1):
            try:
                conversion_result = await run_docxtpl_conversion(
                    str(resume_path),
                    str(TEMPLATE_DOCX),
                    str(converted_pdf_dir),
                    str(converted_docx_dir),
                    filename_base
                )
                break  # Success, exit the retry loop
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"=== Conversion attempt {attempt + 1} failed: {e}. Retrying in 2 seconds... ===")
                    await asyncio.sleep(2)
                else:
                    raise  # Re-raise to be caught by the outer try-except
    except FileNotFoundError as exc:
        logger.error(f"=== Conversion failed — file not found: {exc} ===")
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        logger.error(f"=== Conversion failed — config error: {exc} ===")
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        logger.error(f"=== Conversion failed for {original_file} after {max_retries} retries: {exc} ===", exc_info=True)
        raise HTTPException(status_code=500, detail="Conversion failed. Please wait for a few minutes and reprocess the file.")

    # ── Step 6: Persist to DB ─────────────────────────────────────────────────
    from routes.endpoint.fileconverstionendpoint import write_converted_file_path
    
    returned_filename_base = conversion_result["filename_base"]
    pdf_filename = conversion_result["files"].get("pdf_filename")
    docx_filename = conversion_result["files"]["docx_filename"]
    
    pdf_path_str = str(converted_pdf_dir / pdf_filename) if pdf_filename else ""
    docx_path_str = str(converted_docx_dir / docx_filename)
    
    # Save the JSON content to disk and get its path
    import json
    json_path = converted_json_dir / f"{returned_filename_base}.json"
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(conversion_result.get("content", {}), f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save JSON content for {returned_filename_base}: {e}")
        
    json_path_str = str(json_path)

    # Store the actual paths in the DB as expected by the new schema
    await write_converted_file_path(user_id, original_file, pdf_path_str, docx_path_str, json_path_str)

    logger.info(f"=== Conversion complete: {returned_filename_base} ===")
    return {
        "message": "Resume converted successfully.",
        "converted_file": pdf_filename,
        "uuid": returned_filename_base, # We keep 'uuid' key for frontend compatibility
        "pdf_download_url": f"/conversion/api/download/{returned_filename_base}?format=pdf",
        "docx_download_url": f"/conversion/api/download/{returned_filename_base}?format=docx",
        "preview_url": f"/conversion/api/preview/{returned_filename_base}",
        "content": conversion_result["content"]
    }


@fileconversionrouter.post("/reject")
async def reject_resume(request: RejectRequest, session=Depends(login_required)):
    """
    Record a rejection decision with feedback for a converted resume.
    Marks the DB record as rejected / soft-deleted.
    """
    if session is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user_id = session.get("user_id")
    original_file = request.original_file.strip()
    feedback = request.feedback.strip()

    if not original_file:
        raise HTTPException(status_code=400, detail="original_file is required")
    if not feedback:
        raise HTTPException(status_code=400, detail="feedback is required")

    logger.info(f"=== Reject request: user={user_id}, file={original_file} ===")

    from routes.endpoint.fileconverstionendpoint import write_rejected_file_path
    converted_paths = await write_rejected_file_path(user_id, original_file, feedback)

    if converted_paths:
        for key in ["converted_pdf_file_path", "converted_docx_file_path"]:
            try:
                path_str = converted_paths[key]
                if path_str:
                    file_to_delete = Path(path_str)
                    if file_to_delete.exists():
                        file_to_delete.unlink()
                        logger.info(f"--- Deleted rejected file from disk: {path_str} ---")
            except Exception as e:
                logger.error(f"=== Failed to delete rejected file {path_str}: {e} ===")
        
    #k once the file is deleted i want to reprocess the file converstion using the feed back 
    resume_path = uploaded_dir / original_file
    if not resume_path.exists():
        raise HTTPException(status_code=404, detail="Original resume not found to reprocess.")

    safe_name = Path(original_file).stem.replace(" ", "_")
    filename_base = f"Estuate_{safe_name}"

    from document_processing.docxtpl_converter import run_docxtpl_conversion
    
    try:
        conversion_result = await run_docxtpl_conversion(
            str(resume_path),
            str(TEMPLATE_DOCX),
            str(converted_pdf_dir),
            str(converted_docx_dir),
            filename_base,
            feedback
        )
    except Exception as exc:
        logger.error(f"=== Reprocessing failed: {exc} ===", exc_info=True)
        raise HTTPException(status_code=500, detail="Reprocessing failed.")

    from routes.endpoint.fileconverstionendpoint import write_converted_file_path
    
    returned_filename_base = conversion_result["filename_base"]
    pdf_filename = conversion_result["files"].get("pdf_filename")
    docx_filename = conversion_result["files"]["docx_filename"]
    
    pdf_path_str = str(converted_pdf_dir / pdf_filename) if pdf_filename else ""
    docx_path_str = str(converted_docx_dir / docx_filename)

    # Save the JSON content to disk and get its path
    import json
    json_path = converted_json_dir / f"{returned_filename_base}.json"
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(conversion_result.get("content", {}), f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save JSON content for {returned_filename_base}: {e}")
        
    json_path_str = str(json_path)

    # Store the actual paths in the DB as expected by the new schema (UPSERT handles it)
    await write_converted_file_path(user_id, original_file, pdf_path_str, docx_path_str, json_path_str)

    logger.info(f"=== Reprocessing complete: {returned_filename_base} ===")
    return {
        "message": "Resume rejected and reprocessed successfully.",
        "converted_file": pdf_filename,
        "uuid": returned_filename_base,
        "pdf_download_url": f"/conversion/api/download/{returned_filename_base}?format=pdf",
        "docx_download_url": f"/conversion/api/download/{returned_filename_base}?format=docx",
        "preview_url": f"/conversion/api/preview/{returned_filename_base}",
        "content": conversion_result["content"]
    }


class UpdateRequest(BaseModel):
    uuid: str
    content: dict

@fileconversionrouter.post("/update_and_regenerate")
async def update_and_regenerate(request: UpdateRequest, session=Depends(login_required)):
    """
    Accepts modified JSON data, directly regenerates the DOCX and PDF, 
    and overwrites the existing ones in the UUID folder.
    """
    if session is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    filename_base = request.uuid
    content = request.content
    
    if not filename_base:
        raise HTTPException(status_code=400, detail="UUID is required")

    logger.info(f"=== Regenerating files for UUID: {filename_base} ===")
    
    import asyncio
    from document_processing.docxtpl_converter import generate_docx_and_pdf_json_file
    
    try:
        result = await asyncio.to_thread(
            generate_docx_and_pdf_json_file, 
            content, 
            str(TEMPLATE_DOCX), 
            str(converted_pdf_dir), 
            str(converted_docx_dir),
            filename_base
        )
    except Exception as exc:
        logger.error(f"=== Regeneration failed for {filename_base}: {exc} ===", exc_info=True)
        raise HTTPException(status_code=500, detail="Regeneration failed.")
        
    return {
        "message": "Resume regenerated successfully.",
        "uuid": filename_base,
        "files": result
    }


@fileconversionrouter.get("/download/{file_uuid}")
def download_converted_resume(file_uuid: str, format: str = "pdf", session=Depends(login_required)):
    """
    Stream a converted resume (PDF or DOCX) to the client.
    """
    if session is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Security: strip any path components
    safe_uuid = Path(file_uuid).name

    if format.lower() == "docx":
        filename = f"{safe_uuid}.docx"
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        file_path = converted_docx_dir / filename
    else:
        filename = f"{safe_uuid}.pdf"
        media_type = "application/pdf"
        file_path = converted_pdf_dir / filename

    if not file_path.exists() or not file_path.is_file():
        logger.warning(f"--- Download requested for missing file: {filename} ---")
        raise HTTPException(status_code=404, detail="Converted file not found.")

    logger.info(f"--- Serving download: {filename} ---")
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename,
    )


@fileconversionrouter.get("/preview/{file_uuid}")
def preview_converted_resume(file_uuid: str, session=Depends(login_required)):
    """
    Serve a converted resume PDF inline for the preview modal iframe.
    """
    if session is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    safe_uuid = Path(file_uuid).name
    filename = f"{safe_uuid}.pdf"
    file_path = converted_pdf_dir / filename

    if not file_path.exists() or not file_path.is_file():
        logger.warning(f"--- Preview requested for missing file: {filename} ---")
        raise HTTPException(status_code=404, detail="Converted PDF file not found. It may not have generated successfully.")

    logger.info(f"--- Serving inline preview: {filename} ---")
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )