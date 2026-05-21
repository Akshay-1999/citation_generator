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
converted_dir = base_dir / "converted_resumes"
uploaded_dir = base_dir / "uploaded_files"
templates_dir = base_dir / "templates"

for _d in (converted_dir, uploaded_dir, templates_dir):
    _d.mkdir(parents=True, exist_ok=True)

# Fixed company template — place the PDF at templates/estuate_template.pdf
TEMPLATE_PDF = templates_dir / "estuate_template.pdf"


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
        cached_filename = Path(cached).name
        logger.info(f"--- Cache hit: returning {cached_filename} ---")
        return {
            "message": "Resume already converted (cached).",
            "converted_file": cached_filename,
            "download_url": f"/conversion/api/download/{cached_filename}",
        }

    # ── Step 2: Resolve source resume ────────────────────────────────────────
    resume_path = uploaded_dir / original_file
    if not resume_path.exists():
        logger.error(f"=== Resume file not found on disk: {resume_path} ===")
        raise HTTPException(
            status_code=404,
            detail=f"Resume file '{original_file}' not found. "
                   "Please upload the file first via /file/upload.",
        )

    # ── Step 3: Validate template ─────────────────────────────────────────────
    if not TEMPLATE_PDF.exists():
        logger.error(f"=== Company template PDF missing: {TEMPLATE_PDF} ===")
        raise HTTPException(
            status_code=503,
            detail="Company template PDF not configured on the server. "
                   f"Please place the template at: templates/estuate_template.pdf",
        )

    # ── Step 4: Prepare output path ───────────────────────────────────────────
    # Replace spaces with underscores so the filename is URL-safe
    safe_name = Path(original_file).stem.replace(" ", "_")
    output_filename = f"Estuate_{safe_name}.pdf"
    output_path = converted_dir / output_filename

    # ── Step 5: Run conversion (async — awaited directly) ────────────────────
    try:
        from document_processing.resume_converter import run_conversion
        await run_conversion(
            str(resume_path),
            str(TEMPLATE_PDF),
            str(output_path),
        )
    except FileNotFoundError as exc:
        logger.error(f"=== Conversion failed — file not found: {exc} ===")
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        logger.error(f"=== Conversion failed — config error: {exc} ===")
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        logger.error(f"=== Conversion failed for {original_file}: {exc} ===", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(exc)}")

    # ── Step 6: Persist to DB ─────────────────────────────────────────────────
    from routes.endpoint.fileconverstionendpoint import write_converted_file_path
    await write_converted_file_path(user_id, original_file, str(output_path))

    logger.info(f"=== Conversion complete: {output_filename} ===")
    return {
        "message": "Resume converted successfully.",
        "converted_file": output_filename,
        "download_url": f"/conversion/api/download/{output_filename}",
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
    converted_file_path = await write_rejected_file_path(user_id, original_file, feedback)

    if converted_file_path:
        try:
            file_to_delete = Path(converted_file_path)
            if file_to_delete.exists():
                file_to_delete.unlink()
                logger.info(f"--- Deleted rejected file from disk: {converted_file_path} ---")
        except Exception as e:
            logger.error(f"=== Failed to delete rejected file {converted_file_path}: {e} ===")

    return {"message": "Rejection feedback recorded successfully."}


@fileconversionrouter.get("/download/{filename}")
def download_converted_resume(filename: str, session=Depends(login_required)):
    """
    Stream a converted resume PDF to the client.
    Only allows filenames that live inside converted_resumes/ (path traversal guard).
    """
    if session is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Security: strip any path components — only allow a bare filename
    safe_filename = Path(filename).name
    file_path = converted_dir / safe_filename

    if not file_path.exists() or not file_path.is_file():
        logger.warning(f"--- Download requested for missing file: {safe_filename} ---")
        raise HTTPException(status_code=404, detail="Converted file not found.")

    logger.info(f"--- Serving download: {safe_filename} ---")
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=safe_filename,
    )


@fileconversionrouter.get("/preview/{filename}")
def preview_converted_resume(filename: str, session=Depends(login_required)):
    """
    Serve a converted resume PDF inline for the preview modal iframe.
    Uses Content-Disposition: inline so the browser renders it in-place
    rather than prompting a file download.
    """
    if session is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Security: strip any path components — only allow a bare filename
    safe_filename = Path(filename).name
    file_path = converted_dir / safe_filename

    if not file_path.exists() or not file_path.is_file():
        logger.warning(f"--- Preview requested for missing file: {safe_filename} ---")
        raise HTTPException(status_code=404, detail="Converted file not found.")

    logger.info(f"--- Serving inline preview: {safe_filename} ---")
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=safe_filename,
        headers={"Content-Disposition": f'inline; filename="{safe_filename}"'},
    )