from db.config import Database
from utils.logger_instances import job_logger as logger
import uuid
import datetime
from typing import Union

async def get_all_active_jobs_users():
    logger.info("--- Getting DB connection pool for active jobs ---")
    pool = await Database.get_pool()
    async with pool.acquire() as connection:
        rows = await connection.fetch(
            """
            SELECT id, user_id, report_name, "position", experience, jd_text, client_name, status, created_at
            FROM core.screening_batches 
            WHERE status = true AND is_deleted = false
            ORDER BY created_at DESC;
            """
        )
        if rows:
            logger.info(f"=== Retrieved {len(rows)} active jobs ===")
            return [{
                **dict(row),
                "id": str(row["id"]),
                "job_id": str(row["id"]),
                "job_code": str(row["id"])[:8].upper(),
                "title": row.get("position") or row.get("report_name") or "Untitled Position",
                "job_name": row.get("report_name"),
                "position": row.get("position") or row.get("report_name"),
                "client_name": row.get("client_name") or "Unknown Client",
                "min_experience": row.get("experience") or 0,
                "experience": row.get("experience") or 0,
                "jd_text": row.get("jd_text") or "",
                "status": "OPEN" if row.get("status") is True else "CLOSED",
                "user_id": str(row["user_id"]),
                "created_at": row["created_at"].isoformat() if row.get("created_at") else None
            } for row in rows]
        else:
            logger.info("=== No active jobs found ===")
            return []

async def get_all_jobs_admin():
    logger.info("--- Getting DB connection pool for admin jobs ---")
    pool = await Database.get_pool()
    async with pool.acquire() as connection:
        rows = await connection.fetch(
            """
            SELECT id, user_id, report_name, "position", experience, jd_text, client_name, status, created_at
            FROM core.screening_batches 
            WHERE is_deleted = false
            ORDER BY created_at DESC;
            """
        )
        if rows:
            logger.info(f"=== Retrieved {len(rows)} jobs for admin ===")
            return [{
                **dict(row),
                "id": str(row["id"]),
                "job_id": str(row["id"]),
                "job_code": str(row["id"])[:8].upper(),
                "title": row.get("position") or row.get("report_name") or "Untitled Position",
                "job_name": row.get("report_name"),
                "position": row.get("position") or row.get("report_name"),
                "client_name": row.get("client_name") or "Unknown Client",
                "min_experience": row.get("experience") or 0,
                "experience": row.get("experience") or 0,
                "jd_text": row.get("jd_text") or "",
                "status": "OPEN" if row.get("status") is True else "CLOSED",
                "user_id": str(row["user_id"]),
                "created_at": row["created_at"].isoformat() if row.get("created_at") else None
            } for row in rows]
        else:
            logger.info("=== No jobs found ===")
            return []


async def create_job(user_id: str, job_name: str, position: str, experience: str, jd_text: str, client_name: str):
    logger.info("--- Getting DB connection pool for job creation ---")
    pool = await Database.get_pool()
    batch_id = uuid.uuid4()
    job_title = (job_name or position or "Job Position").strip()
    pos = (position or job_title).strip()
    client = (client_name or "Unknown Client").strip()
    report_name = job_title.replace(" ", "_") + "_" + client.replace(" ", "_") + "_" + str(datetime.datetime.now().strftime("%Y%m%d_%H%M%S")) 
    
    # Safe cast experience to int
    try:
        exp_int = int(str(experience).split('+')[0].strip())
    except Exception:
        exp_int = 0

    # Ensure user_id is a valid UUID that exists in core.users
    uuid_user = None
    try:
        uuid_user = uuid.UUID(str(user_id))
    except Exception:
        uuid_user = None

    async with pool.acquire() as connection:
        if uuid_user is None:
            # Look up user UUID from core.users by username or email
            user_row = await connection.fetchrow(
                "SELECT user_id FROM core.users WHERE username = $1 OR email = $1 LIMIT 1;",
                str(user_id)
            )
            if user_row:
                uuid_user = user_row["user_id"]
            else:
                # Fallback to any admin user in core.users
                admin_row = await connection.fetchrow(
                    "SELECT user_id FROM core.users WHERE user_role = 'admin' LIMIT 1;"
                )
                if admin_row:
                    uuid_user = admin_row["user_id"]
                else:
                    # Fallback to any user in core.users
                    any_user = await connection.fetchrow(
                        "SELECT user_id FROM core.users LIMIT 1;"
                    )
                    if any_user:
                        uuid_user = any_user["user_id"]
                    else:
                        uuid_user = uuid.uuid4()
        else:
            # Check if this uuid_user actually exists in core.users
            exists = await connection.fetchval(
                "SELECT EXISTS(SELECT 1 FROM core.users WHERE user_id = $1);",
                uuid_user
            )
            if not exists:
                admin_row = await connection.fetchrow(
                    "SELECT user_id FROM core.users WHERE user_role = 'admin' LIMIT 1;"
                )
                if admin_row:
                    uuid_user = admin_row["user_id"]

        await connection.execute(
            """
            INSERT INTO core.screening_batches (id, user_id, report_name, job_name, position, experience, jd_text, client_name, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            batch_id, uuid_user, report_name, job_title, pos, exp_int, jd_text, client, True
        )
        logger.info(f"=== Job {job_title} created successfully with ID {batch_id} ===")
        return {
            "message": f"Job created successfully. Report name: {job_title}",
            "job_id": str(batch_id),
            "id": str(batch_id),
            "user_id": str(uuid_user),
            "job_code": str(batch_id)[:8].upper(),
            "report_name": report_name,
            "job_name": job_title,
            "title": pos,
            "position": pos,
            "client_name": client,
            "min_experience": exp_int,
            "jd_text": jd_text,
            "status": "OPEN"
        }


async def update_job_status(job_id: str, status: Union[bool, str]):
    logger.info(f"--- Updating job status for {job_id} to {status} ---")
    pool = await Database.get_pool()
    bool_status = str(status).lower() in ["true", "open", "active", "1"]
    
    job_uuid = None
    try:
        job_uuid = uuid.UUID(str(job_id))
    except Exception:
        job_uuid = None

    async with pool.acquire() as connection:
        updated = False
        result = None
        if job_uuid:
            try:
                result = await connection.execute(
                    """
                    UPDATE core.screening_batches
                    SET status = $1, updated_at = now()        
                    WHERE id = $2;
                    """,
                    bool_status, job_uuid
                )
                updated = True
            except Exception:
                # In case updated_at column is absent
                result = await connection.execute(
                    """
                    UPDATE core.screening_batches
                    SET status = $1       
                    WHERE id = $2;
                    """,
                    bool_status, job_uuid
                )
                updated = True
        
        # If not updated by UUID or 0 rows affected, fallback to match by job_name or report_name
        if not updated or (result and result.endswith("0")):
            try:
                await connection.execute(
                    """
                    UPDATE core.screening_batches
                    SET status = $1, updated_at = now()
                    WHERE job_name = $2 OR report_name = $2;
                    """,
                    bool_status, str(job_id)
                )
            except Exception:
                await connection.execute(
                    """
                    UPDATE core.screening_batches
                    SET status = $1
                    WHERE job_name = $2 OR report_name = $2;
                    """,
                    bool_status, str(job_id)
                )

        logger.info(f"=== Job {job_id} status updated to {bool_status} ===")
        return {
            "message": f"Job status updated successfully. Job ID: {job_id}",
            "status": "OPEN" if bool_status else "CLOSED",
            "is_active": bool_status,
            "job_id": str(job_id)
        }


async def update_job_description(job_id: str, jd_text: str):
    logger.info(f"--- Updating JD text for job {job_id} ---")
    pool = await Database.get_pool()
    try:
        job_uuid = uuid.UUID(str(job_id))
    except Exception:
        job_uuid = job_id

    async with pool.acquire() as connection:
        await connection.execute(
            """
            UPDATE core.screening_batches
            SET jd_text = $1, updated_at = now()         
            WHERE id = $2;
            """,
            jd_text, job_uuid
        )
        logger.info(f"=== Job description for job {job_id} updated successfully ===")
        return {"message": f"Job description updated successfully. Job ID: {job_id}"}


async def soft_delete_job(job_id: str):
    logger.info(f"--- Soft deleting job {job_id} ---")
    pool = await Database.get_pool()
    try:
        job_uuid = uuid.UUID(str(job_id))
    except Exception:
        job_uuid = job_id

    async with pool.acquire() as connection:
        await connection.execute(
            """
            UPDATE core.screening_batches
            SET is_deleted = true, deleted_at = now() 
            WHERE id = $1;
            """,
            job_uuid
        )
        logger.info(f"=== Job {job_id} deleted successfully ===")
        return {"message": f"Job deleted successfully. Job ID: {job_id}"}