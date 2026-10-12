from fastapi import APIRouter, Request, Depends, HTTPException, UploadFile, File, Form, Query
from pydantic import BaseModel, Field
from typing import Optional, Literal
from utils.logger_instances import job_logger
from routes.auth import login_required
from db.endpoints.job import (
    get_all_jobs_admin,
    get_all_active_jobs_users,
    create_job,
    update_job_status,
    update_job_description,
    soft_delete_job
)
import uuid
import os
import datetime
from routes.folderprocesser import extract_text_from_attachment_jd

logger = job_logger

REPORTS_DIR = "screening_reports"

jobrouter = APIRouter()  

class Job(BaseModel):
    user_id: Optional[str] = Field(None, example="user_id")
    job_name: Optional[str] = Field(None, example="job_name")
    title: Optional[str] = Field(None, example="title")
    job_description: Optional[str] = Field(None, example="job_description")
    jd_text: Optional[str] = Field(None, example="jd_text")
    job_status: Optional[str] = Field("OPEN", example="job_status")
    status: Optional[str] = Field("OPEN", example="status")
    job_created_at: Optional[str] = Field(None, example="job_created_at")
    job_updated_at: Optional[str] = Field(None, example="job_updated_at")
    position: Optional[str] = Field(None, example="position")
    experience: Optional[str] = Field("0", example="experience")
    min_experience: Optional[str] = Field(None, example="min_experience")
    client_name: Optional[str] = Field(None, example="client_name")
    job_code: Optional[str] = Field(None, example="job_code")


@jobrouter.api_route("/read_attached_file", methods=["GET", "POST"])
async def read_attached_file(request: Request, file: Optional[UploadFile] = File(None), session = Depends(login_required)):
    if session is None:
        logger.error("=== Unauthorized file read attempt: No active session ===")
        raise HTTPException(status_code=401, detail="Authentication required.")
    try:
        user_id = session.get('user_id', 'default_user') if isinstance(session, dict) else 'default_user'
        logger.info(f"=== Attempting to read attached file for user_id: {user_id} ===")
        
        # 1. If file uploaded directly via multipart/form-data
        if file is not None:
            file_content = await extract_text_from_attachment_jd(file, user_id)
            return {"message": "File read successfully", "file_content": file_content}
        
        # 2. If passed via query param ?job_description_url=...
        jd_file_url = request.query_params.get("job_description_url")
        if jd_file_url:
            file_content = await extract_text_from_attachment_jd(jd_file_url, user_id)
            return {"message": "File read successfully", "file_content": file_content}

        return {"message": "No file or URL provided", "file_content": ""}
    except Exception as e:
        logger.error(f"=== Error reading attached file: {e} ===", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def create_report_for_job(report_name : str , user_id : str , file_path : str):
    columns = [
        "user name",
        "candidate name",
        "confidence_score",
        "certification",
        "experience_comparison",
        "skills",
        "matched_skills",
        "original_file",
        "phone",
        "email",
        "experience_in_resume",
        "last_company",
        "gaps",
        "stability",
        "resume_gaps_against_jd"
    ]
    from openpyxl import Workbook

    os.makedirs(file_path, exist_ok=True)

    #create a new excel workbook 
    workbook = Workbook()
     # Get the active sheet
    worksheet = workbook.active
    worksheet.title = "Report"

    # Add column names in the first row
    worksheet.append(columns)

    clean_report_name = report_name[:-5] if report_name.endswith(".xlsx") else report_name
    save_path = os.path.join(file_path, f"{clean_report_name}.xlsx")
    workbook.save(save_path)

    # Also ensure a copy is in REPORTS_DIR (screening_reports) so download and preview work seamlessly
    if file_path != REPORTS_DIR:
        try:
            os.makedirs(REPORTS_DIR, exist_ok=True)
            reports_save_path = os.path.join(REPORTS_DIR, f"{clean_report_name}.xlsx")
            workbook.save(reports_save_path)
        except Exception as copy_err:
            logger.warning(f"Could not save copy to {REPORTS_DIR}: {copy_err}")
    return save_path
    

@jobrouter.post("/create_job")
async def create_job_endpoint(request: Request, job: Job, session = Depends(login_required)):
    if session is None:
        logger.error("=== Unauthorized job creation attempt: No active session ===")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    user_details_role = session.get('role') if isinstance(session, dict) else None
    if user_details_role != "admin":
        logger.error(f"=== Unauthorized job creation attempt by user_id: {session.get('user_id')} ===")
        raise HTTPException(status_code=403, detail="Operation not permitted. Admin role required.")
    
    try:
        user_id = session.get('user_id') or (job.user_id if job else None) or "admin"
        logger.info(f"=== Attempting to create job for user_id: {user_id} ===") 
        
        position = (job.position or job.title or job.job_name or "Position").strip()
        job_name = (job.job_name or job.title or job.position or "Job").strip()
        experience = str(job.experience if job.experience is not None else (job.min_experience or "0")).strip()
        client_name = (job.client_name or "Unknown Client").strip()
        
        # Robustly extract the job description text
        jd_text = (job.jd_text or job.job_description or "").strip()
        if not jd_text:
            logger.warning("=== Empty JD text received in create_job ===")

        job_details = await create_job(
            user_id=str(user_id),
            job_name=job_name,
            position=position,
            experience=experience,
            jd_text=jd_text,
            client_name=client_name
        )

        #Create the report path
        report_name = job_details.get("report_name") or (job_name.replace(" ", "_") + "_" + client_name.replace(" ", "_") + "_" + str(datetime.datetime.now().strftime("%Y%m%d_%H%M%S")))
        file_path =  os.path.join(REPORTS_DIR, report_name)
        # create_report_for_job
        user_id_val = job_details.get("user_id") or str(user_id)
        report_file_path = await create_report_for_job(report_name, user_id_val, "data")
        job_details["report_name"] = report_name
        job_details["report_file_path"] = report_file_path
        return job_details 
    except Exception as e:
        logger.error(f"=== Error creating job: {e} ===", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@jobrouter.get("/active_jobs")
async def get_active_jobs_endpoint(session = Depends(login_required)):
    if session is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    try:
        jobs = await get_all_active_jobs_users()
        return jobs
    except Exception as e:
        logger.error(f"Error fetching active jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@jobrouter.get("/active")
async def get_active_jobs_alias(session = Depends(login_required)):
    """Alias for /active_jobs to support both conventions."""
    if session is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    try:
        jobs = await get_all_active_jobs_users()
        return jobs
    except Exception as e:
        logger.error(f"Error fetching active jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@jobrouter.get("/admin_jobs")
async def get_admin_jobs(session = Depends(login_required)):
    if session is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    user_details_role = session.get('role') if isinstance(session, dict) else None
    if user_details_role != "admin":
        raise HTTPException(status_code=403, detail="Operation not permitted. Admin role required.")
    try:
        jobs = await get_all_jobs_admin()
        return jobs
    except Exception as e:
        logger.error(f"Error fetching all jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@jobrouter.get("/all_jobs")
async def get_all_jobs_endpoint(session = Depends(login_required)):
    """
    Active jobs endpoint for regular users / recruiters to populate
    the folder processing and screening dropdown.
    """
    if session is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    try:
        jobs = await get_all_active_jobs_users()
        return jobs
    except Exception as e:
        logger.error(f"Error fetching active jobs for users: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@jobrouter.put("/update_status/{job_id}")
@jobrouter.put("/{job_id}/status")
@jobrouter.put("/status/{job_id}")
@jobrouter.put("/update_job_status/{job_id}")
async def update_status_endpoint(
    job_id: str, 
    status: Optional[str] = Query("OPEN"), 
    session = Depends(login_required)
):
    if session is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    user_details_role = session.get('role') if isinstance(session, dict) else None
    if user_details_role != "admin":
        raise HTTPException(status_code=403, detail="Operation not permitted. Admin role required.")
    try:
        res = await update_job_status(job_id=job_id, status=status)
        return res
    except Exception as e:
        logger.error(f"Error updating job status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class JobStatusPayload(BaseModel):
    job_id: Optional[str] = None
    status: Optional[str] = "OPEN"


@jobrouter.api_route("/update_status", methods=["POST", "PUT"])
@jobrouter.api_route("/update_job_status", methods=["POST", "PUT"])
async def update_status_generic_endpoint(
    payload: Optional[JobStatusPayload] = None,
    job_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    session = Depends(login_required)
):
    if session is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    user_details_role = session.get('role') if isinstance(session, dict) else None
    if user_details_role != "admin":
        raise HTTPException(status_code=403, detail="Operation not permitted. Admin role required.")
    
    target_job_id = job_id or (payload.job_id if payload else None)
    target_status = status or (payload.status if payload else None) or "OPEN"

    if not target_job_id:
        raise HTTPException(status_code=400, detail="job_id is required.")

    try:
        res = await update_job_status(job_id=target_job_id, status=target_status)
        return res
    except Exception as e:
        logger.error(f"Error updating job status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@jobrouter.delete("/{job_id}")
@jobrouter.delete("/delete/{job_id}")
@jobrouter.delete("/delete_job/{job_id}")
async def delete_job_endpoint(job_id: str, session = Depends(login_required)):
    if session is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    user_details_role = session.get('role') if isinstance(session, dict) else None
    if user_details_role != "admin":
        raise HTTPException(status_code=403, detail="Operation not permitted. Admin role required.")
    try:
        res = await soft_delete_job(job_id=job_id)
        return res
    except Exception as e:
        logger.error(f"Error deleting job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))