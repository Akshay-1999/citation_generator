import asyncio
import os
import pandas as pd
from langchain_anthropic import ChatAnthropic
import json
import uuid
from db.config import Database
from dotenv import load_dotenv
from agents.agents_main import ResumeMappingAgent
from utils.logger_instances import folder_processer_logger as logger

load_dotenv()

from openpyxl import load_workbook, Workbook

REPORT_COLUMNS = [
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

def get_field_value(item: dict, col_name: str, current_username: str) -> str:
    clean = str(col_name).strip().lower()
    if clean in ["user name", "username", "screened by", "user"]:
        return str(item.get("user name") or item.get("username") or current_username or "")
    if clean in ["candidate name", "name", "candidate"]:
        return str(item.get("candidate name") or item.get("name") or "")
    if clean == "confidence_score":
        return str(item.get("confidence_score") or "")
    if clean == "certification":
        return str(item.get("certification") or "")
    if clean == "experience_comparison":
        return str(item.get("experience_comparison") or "")
    if clean == "skills":
        skills = item.get("skills", "")
        if isinstance(skills, list):
            return ", ".join(str(s) for s in skills)
        return str(skills or "")
    if clean == "matched_skills":
        matched = item.get("matched_skills", "")
        if isinstance(matched, list):
            return ", ".join(str(m) for m in matched)
        return str(matched or "")
    if clean in ["original_file", "file_name", "file"]:
        return str(item.get("original_file") or "")
    if clean == "phone":
        return str(item.get("phone") or "")
    if clean == "email":
        return str(item.get("email") or "")
    if clean == "experience_in_resume":
        return str(item.get("experience_in_resume") or "")
    if clean == "last_company":
        return str(item.get("last_company") or "")
    if clean == "gaps":
        return str(item.get("gaps") or "")
    if clean == "stability":
        return str(item.get("stability") or "")
    if clean in ["resume_gaps_against_jd", "jd_gaps"]:
        return str(item.get("resume_gaps_against_jd") or "")
    return str(item.get(col_name) or item.get(clean) or "")

async def save_results_to_db(results: list, user_id: str, batch_id: str = None, username: str = None):
    """Save screening results to the core.bulk_screening_results table."""
    logger.info(f"--- Saving {len(results)} results to database (Batch: {batch_id}, Username: {username}) ---")
    pool = await Database.get_pool()
    async with pool.acquire() as conn:
        try:
            # Prepare query including username and batch_id
            query = """
                INSERT INTO core.bulk_screening_results (
                    user_id, name, confidence_score, certification, experience_comparison, 
                    skills, matched_skills, original_file, phone, email, experience_in_resume, 
                    last_company, gaps, stability, resume_gaps_against_jd, error, batch_id, username
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
            """
            
            # Prepare data for insertion
            insert_data = []
            for res in results:
                # Handle skills (convert list to comma-separated)
                skills = res.get("skills", "")
                if isinstance(skills, list):
                    skills = ", ".join(str(s) for s in skills)
                
                # Handle matched_skills similarly
                matched_skills = res.get("matched_skills", "")
                if isinstance(matched_skills, list):
                    matched_skills = ", ".join(str(m) for m in matched_skills)
                
                candidate_name = res.get("candidate name") or res.get("name") or "Unknown"
                candidate_user = username or res.get("username") or res.get("user name") or "Unknown"

                # Extract values with defaults
                data = (
                    uuid.UUID(user_id),
                    candidate_name,
                    res.get("confidence_score"),
                    res.get("certification"),
                    res.get("experience_comparison"),
                    skills,
                    matched_skills,
                    res.get("original_file"),
                    res.get("phone"),
                    res.get("email"),
                    res.get("experience_in_resume"),
                    res.get("last_company"),
                    res.get("gaps"),
                    res.get("stability"),
                    res.get("resume_gaps_against_jd"),
                    res.get("error"),
                    uuid.UUID(batch_id) if batch_id else None,
                    candidate_user
                )
                insert_data.append(data)
            
            # Execute bulk insertion
            await conn.executemany(query, insert_data)
            logger.info("--- Database insertion completed successfully with username ---")
            
        except Exception as e:
            logger.error(f"--- Error inserting results to database: {e} ---", exc_info=True)

async def create_screening_batch(user_id, report_name, position, experience, client_name, jd_text):
    """Create a new batch record in the database."""
    batch_id = str(uuid.uuid4())
    pool = await Database.get_pool()
    async with pool.acquire() as conn:
        try:
            await conn.execute("""
                INSERT INTO core.screening_batches (id, user_id, report_name, position, experience, client_name, jd_text)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, uuid.UUID(batch_id), uuid.UUID(user_id), report_name, position, experience, client_name, jd_text)
            
            return batch_id, report_name
        except Exception as e:
            logger.error(f"Error creating batch: {e}")
            return None, report_name


async def process_resumes_to_excel(job_description: str, file_names: list, user_id: str, output_file: str, username: str, batch_id: str = None):
    """
    Iterate through resumes one by one and collect results.
    Opens existing report file to append new rows (preserving previous entries),
    or creates a new workbook with the standard columns.
    """
    client = ChatAnthropic(
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929"),
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        temperature=0.0,
        max_tokens=4096
    )
    agent = ResumeMappingAgent(client=client)
    
    all_results = []
    
    logger.info(f"--- Starting Bulk Processing for {len(file_names)} resumes (User: {username}) ---")

    if not file_names:
        logger.warning("--- WARNING: No file names provided for bulk processing ---")
        return []
    
    for file_name in file_names:
        logger.info(f"[Processing]: {file_name}...")
        try:
            # We pass a list with a single file name to process specifically
            response, matches, source = await agent.process_resume_mapping(
                job_description=job_description,
                file_names=[file_name],
                user_id=user_id
            )
            
            # response should be a dict if parsing was successful
            if isinstance(response, dict):
                response["original_file"] = file_name
                response["username"] = username
                response["user name"] = username
                response["candidate name"] = response.get("name") or "Unknown"
                response["name"] = response.get("name") or response.get("candidate name") or "Unknown"
                all_results.append(response)
                logger.info(f"Successfully screened {response.get('name', 'Unknown')} by {username}")
            elif isinstance(response, list):
                for item in response:
                    item["original_file"] = file_name
                    item["username"] = username
                    item["user name"] = username
                    item["candidate name"] = item.get("name") or "Unknown"
                    item["name"] = item.get("name") or item.get("candidate name") or "Unknown"
                    all_results.append(item)
                logger.info(f"Successfully screened {len(response)} candidates from {file_name} by {username}")
            else:
                logger.warning(f"Could not parse result for {file_name}. Raw output: {str(response)[:100]}...")
                all_results.append({
                    "original_file": file_name,
                    "username": username,
                    "user name": username,
                    "name": "Parsing failed",
                    "candidate name": "Parsing failed",
                    "error": "Parsing failed",
                    "raw_output": str(response)
                })
                
        except Exception as e:
            logger.error(f"Error processing {file_name}: {e}", exc_info=True)
            all_results.append({
                "original_file": file_name,
                "username": username,
                "user name": username,
                "name": "Error processing file",
                "candidate name": "Error processing file",
                "error": str(e)
            })

    # Append to existing Excel report without deleting prior rows, or create new if not present
    if all_results:
        # Check existing file paths (output_file or data/)
        existing_file = None
        if os.path.exists(output_file):
            existing_file = output_file
        else:
            filename_only = os.path.basename(output_file)
            for cand_dir in ["screening_reports", "data"]:
                cand_path = os.path.join(cand_dir, filename_only)
                if os.path.exists(cand_path):
                    existing_file = cand_path
                    break

        if existing_file:
            try:
                logger.info(f"Loading existing report to append rows: {existing_file}")
                workbook = load_workbook(existing_file)
                worksheet = workbook.active
            except Exception as load_err:
                logger.warning(f"Failed to load workbook {existing_file}: {load_err}, creating new")
                workbook = Workbook()
                worksheet = workbook.active
                worksheet.title = "Report"
        else:
            logger.info(f"Creating new report workbook: {output_file}")
            workbook = Workbook()
            worksheet = workbook.active
            worksheet.title = "Report"

        # Determine header columns
        header_cells = [cell.value for cell in worksheet[1]] if worksheet.max_row >= 1 else []
        existing_headers = [str(h).strip() for h in header_cells if h is not None]

        if not existing_headers:
            worksheet.append(REPORT_COLUMNS)
            active_columns = REPORT_COLUMNS
        else:
            has_user_col = any(h.lower() in ["user name", "username", "user"] for h in existing_headers)
            if not has_user_col:
                worksheet.insert_cols(1)
                worksheet.cell(row=1, column=1, value="user name")
                active_columns = ["user name"] + existing_headers
            else:
                active_columns = existing_headers

        # Append new candidate rows
        for item in all_results:
            row_data = [get_field_value(item, col, username) for col in active_columns]
            worksheet.append(row_data)

        # Save to output_file
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        workbook.save(output_file)
        logger.info(f"--- SUCCESS: Preserved previous entries and added {len(all_results)} new rows to {output_file} ---")

        # Sync across screening_reports and data directories
        filename_only = os.path.basename(output_file)
        for folder in ["screening_reports", "data"]:
            target_path = os.path.join(folder, filename_only)
            try:
                if os.path.abspath(target_path) != os.path.abspath(output_file):
                    os.makedirs(folder, exist_ok=True)
                    workbook.save(target_path)
                    logger.info(f"--- Synced report copy to: {target_path} ---")
            except Exception as sync_err:
                logger.warning(f"Could not sync report to {target_path}: {sync_err}")

        # Save to Database with batch_id and username
        await save_results_to_db(all_results, user_id, batch_id, username)
        return all_results
    else:
        logger.warning("--- No results to save ---")
        return []

async def delete_batch(batch_id, user_id):
    """Delete a batch and all its associated data."""
    try:
        from db.config import Database
        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute("UPDATE core.screening_batches SET is_deleted = true, deleted_at = NOW() WHERE id = $1", uuid.UUID(batch_id))    
            logger.info(f"--- Batch {batch_id} deleted successfully ---")
            return True
    except Exception as e:
        logger.error(f"Error deleting batch {batch_id}: {e}")
        return False