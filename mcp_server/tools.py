"""
MCP Tool Implementations for RecAI / ProfileIQ:
1. search_resumes: Semantic candidate search via Pinecone & Cohere reranking.
2. start_screening: Bulk resume vs. Job Description evaluation and batch creation.
3. get_screening_report: Fetching screening results by batch ID or listing reports.
"""
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from db.config import Database
from embedding.embedder import query_similar_documents
from routes.folderprocesser import serialize_screening_result
from routes.endpoint.bulk_processing import create_screening_batch, process_resumes_to_excel
from mcp_server.security import PromptInjectionGuard, mcp_rate_limiter
from utils.logging_utils import set_system_logger

logger = set_system_logger("mcp_tools_logger")

REPORTS_DIR = "screening_reports"
os.makedirs(REPORTS_DIR, exist_ok=True)


# ─── Tool 1: search_resumes ───────────────────────────────────────────────────
async def execute_search_resumes(
    query: str,
    user_id: str,
    top_k: int = 5,
    file_filter: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Search candidate resumes using semantic vector search and Cohere reranking.
    """
    mcp_rate_limiter.check_request(f"search:{user_id}")
    cleaned_query = PromptInjectionGuard.inspect_query(query)
    top_k = max(1, min(int(top_k or 5), 20))

    logger.info(f"--- [MCP] search_resumes query='{cleaned_query}' top_k={top_k} user_id={user_id} ---")

    pinecone_filter = {}
    if file_filter and isinstance(file_filter, list):
        pinecone_filter = {"file_name": {"$in": file_filter}}

    try:
        raw_result = await query_similar_documents(
            query=cleaned_query,
            user_id=user_id,
            top_k=top_k,
            pinecone_filter=pinecone_filter
        )
    except Exception as e:
        logger.error(f"[MCP] Error querying similar documents: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to search documents: {str(e)}",
            "matches": []
        }

    matches = raw_result.get("matches", [])
    if not matches:
        return {
            "success": True,
            "count": 0,
            "message": "No matching candidate resumes found for this query.",
            "matches": []
        }

    formatted_matches = []
    for m in matches:
        metadata = getattr(m, "metadata", {}) or {}
        score = getattr(m, "score", 0.0)
        reranked_score = metadata.get("reranked_score", score)
        file_name = metadata.get("file_name", "Unknown File")
        text_snippet = metadata.get("text", "")

        # Truncate text snippet to avoid flooding context
        if len(text_snippet) > 600:
            text_snippet = text_snippet[:600] + "..."

        formatted_matches.append({
            "file_name": file_name,
            "candidate_name": metadata.get("candidate_name") or metadata.get("name") or file_name,
            "relevance_score": round(float(reranked_score), 4),
            "pinecone_score": round(float(metadata.get("pinecone_score", score)), 4),
            "text_snippet": text_snippet
        })

    return {
        "success": True,
        "count": len(formatted_matches),
        "query": cleaned_query,
        "matches": formatted_matches
    }


# ─── Tool 2: start_screening ──────────────────────────────────────────────────
async def execute_start_screening(
    job_description: str,
    user_id: str,
    username: str = "Claude Recruiter",
    file_names: Optional[List[str]] = None,
    position: Optional[str] = None,
    client_name: Optional[str] = None,
    experience: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run bulk resume screening against a Job Description.
    """
    mcp_rate_limiter.check_request(f"screen:{user_id}")
    cleaned_jd = PromptInjectionGuard.inspect_job_description(job_description)

    # If no file names provided, look up all uploaded files belonging to the user
    target_files = file_names or []
    if not target_files:
        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT filename FROM core.files 
                WHERE user_id = $1 AND deleted_at IS NULL 
                ORDER BY created_at DESC
                LIMIT 50
            """, uuid.UUID(user_id) if isinstance(user_id, str) and len(user_id) == 36 else user_id)
            target_files = [r["filename"] for r in rows if r.get("filename")]

    if not target_files:
        return {
            "success": False,
            "error": "No resumes found to screen. Please upload candidate resumes in the RecAI portal first or provide specific 'file_names'."
        }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    resolved_position = position or "Screened Role"
    resolved_client = client_name or "Internal"
    resolved_exp = str(experience or "0")
    report_name = f"Claude_Screening_{timestamp}"

    logger.info(f"--- [MCP] start_screening files={len(target_files)} position='{resolved_position}' user={username} ---")

    # Create batch record in database
    batch_id, saved_report_name = await create_screening_batch(
        user_id=user_id,
        report_name=report_name,
        position=resolved_position,
        experience=resolved_exp,
        client_name=resolved_client,
        jd_text=cleaned_jd
    )

    if not batch_id:
        batch_id = str(uuid.uuid4())

    output_filename = f"{report_name}.xlsx"
    output_path = os.path.join(REPORTS_DIR, output_filename)

    try:
        results = await process_resumes_to_excel(
            job_description=cleaned_jd,
            file_names=target_files,
            user_id=user_id,
            output_file=output_path,
            username=username,
            batch_id=batch_id
        )

        candidates_summary = []
        for r in results:
            candidates_summary.append({
                "candidate_name": r.get("candidate name") or r.get("name") or "Unknown",
                "original_file": r.get("original_file", ""),
                "confidence_score": r.get("confidence_score", "N/A"),
                "matched_skills": r.get("matched_skills", []),
                "experience_comparison": r.get("experience_comparison", ""),
                "stability": r.get("stability", "")
            })

        return {
            "success": True,
            "batch_id": str(batch_id),
            "report_name": report_name,
            "total_screened": len(results),
            "download_url": f"/folder/download_report/{output_filename}",
            "candidates": candidates_summary
        }
    except Exception as e:
        logger.error(f"[MCP] Error during start_screening: {e}", exc_info=True)
        return {
            "success": False,
            "batch_id": str(batch_id),
            "error": f"Screening process encountered an error: {str(e)}"
        }


# ─── Tool 3: get_screening_report ─────────────────────────────────────────────
async def execute_get_screening_report(
    user_id: str,
    batch_id: Optional[str] = None,
    limit: int = 10,
    user_role: str = "user"
) -> Dict[str, Any]:
    """
    Fetch screening results for a specific batch ID, or list recent reports for the user.
    """
    mcp_rate_limiter.check_request(f"report:{user_id}")
    limit = max(1, min(int(limit or 10), 50))
    pool = await Database.get_pool()

    async with pool.acquire() as conn:
        # Case A: Specific batch ID requested
        if batch_id:
            try:
                batch_uuid = uuid.UUID(batch_id)
            except ValueError:
                return {"success": False, "error": f"Invalid batch_id format: {batch_id}"}

            # Enforce user_id scoping for non-admin
            if user_role != "admin":
                batch = await conn.fetchrow("""
                    SELECT id, report_name, position, experience, client_name, created_at 
                    FROM core.screening_batches 
                    WHERE id = $1 AND user_id = $2 AND is_deleted = False
                """, batch_uuid, uuid.UUID(user_id) if isinstance(user_id, str) and len(user_id) == 36 else user_id)
                if not batch:
                    return {"success": False, "error": "Screening batch not found or access denied."}
            else:
                batch = await conn.fetchrow("""
                    SELECT id, report_name, position, experience, client_name, created_at 
                    FROM core.screening_batches 
                    WHERE id = $1 AND is_deleted = False
                """, batch_uuid)
                if not batch:
                    return {"success": False, "error": "Screening batch not found."}

            rows = await conn.fetch("""
                SELECT * FROM core.bulk_screening_results 
                WHERE batch_id = $1 
                ORDER BY created_at DESC 
                LIMIT $2
            """, batch_uuid, limit)

            results = [serialize_screening_result(r) for r in rows]

            return {
                "success": True,
                "batch_id": str(batch_id),
                "report_name": batch.get("report_name"),
                "position": batch.get("position"),
                "client_name": batch.get("client_name"),
                "experience": batch.get("experience"),
                "created_at": batch.get("created_at").isoformat() if batch.get("created_at") else None,
                "candidate_count": len(results),
                "results": results
            }

        # Case B: List recent batches for the user
        else:
            if user_role == "admin":
                batches = await conn.fetch("""
                    SELECT id, report_name, position, experience, client_name, created_at 
                    FROM core.screening_batches 
                    WHERE is_deleted = False 
                    ORDER BY created_at DESC 
                    LIMIT $1
                """, limit)
            else:
                batches = await conn.fetch("""
                    SELECT id, report_name, position, experience, client_name, created_at 
                    FROM core.screening_batches 
                    WHERE is_deleted = False AND user_id = $1 
                    ORDER BY created_at DESC 
                    LIMIT $2
                """, uuid.UUID(user_id) if isinstance(user_id, str) and len(user_id) == 36 else user_id, limit)

            return {
                "success": True,
                "count": len(batches),
                "reports": [{
                    "batch_id": str(b["id"]),
                    "report_name": b.get("report_name"),
                    "position": b.get("position"),
                    "experience": b.get("experience"),
                    "client_name": b.get("client_name", "Unknown"),
                    "created_at": b["created_at"].isoformat() if b.get("created_at") else None
                } for b in batches]
            }
