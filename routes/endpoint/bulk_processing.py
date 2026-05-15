import asyncio
import os
import pandas as pd
from langchain_openai import ChatOpenAI
import json
import uuid
from db.config import Database
from dotenv import load_dotenv
from agents.agents_main import ResumeMappingAgent
from utils.logger_instances import folder_processer_logger as logger

load_dotenv()

async def save_results_to_db(results: list, user_id: str, batch_id: str = None):
    """Save screening results to the core.bulk_screening_results table."""
    logger.info(f"--- Saving {len(results)} results to database (Batch: {batch_id}) ---")
    pool = await Database.get_pool()
    async with pool.acquire() as conn:
        try:
            # Prepare the query - added batch_id
            query = """
                INSERT INTO core.bulk_screening_results (
                    user_id, name, confidence_score, certification, experience_comparison, 
                    skills, original_file, phone, email, experience_in_resume, 
                    last_company, gaps, stability, resume_gaps_against_jd, error, batch_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
            """
            
            # Prepare data for insertion
            insert_data = []
            for res in results:
                # Handle skills (convert list to JSON string or comma-separated)
                skills = res.get("skills", "")
                if isinstance(skills, list):
                    skills = ", ".join(skills)
                
                # Extract values with defaults
                data = (
                    uuid.UUID(user_id),
                    res.get("name"),
                    res.get("confidence_score"),
                    res.get("certification"),
                    res.get("experience_comparison"),
                    skills,
                    res.get("original_file"),
                    res.get("phone"),
                    res.get("email"),
                    res.get("experience_in_resume"),
                    res.get("last_company"),
                    res.get("gaps"),
                    res.get("stability"),
                    res.get("resume_gaps_against_jd"),
                    res.get("error"), # Add error column
                    uuid.UUID(batch_id) if batch_id else None
                )
                insert_data.append(data)
            
            # Execute bulk insertion
            await conn.executemany(query, insert_data)
            logger.info("--- Database insertion completed successfully ---")
            
        except Exception as e:
            logger.error(f"--- Error inserting results to database: {e} ---")

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


async def process_resumes_to_excel(job_description: str, file_names: list, user_id: str, output_file: str, batch_id: str = None):
    """
    Approach: Iterate through resumes one by one and collect results.
    This ensures that the LLM focuses on one candidate at a time, 
    reducing errors and ensuring clean JSON output for each.
    """
    client = ChatOpenAI(model="gpt-5.4-mini", api_key=os.getenv("OPENAI_API_KEY"))
    agent = ResumeMappingAgent(client=client)
    
    all_results = []
    
    logger.info(f"--- Starting Bulk Processing for {len(file_names)} resumes ---")

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
                # Add the filename to the dict for reference in Excel
                response["original_file"] = file_name
                all_results.append(response)
                logger.info(f"Successfully screened {response.get('name', 'Unknown')}")
            elif isinstance(response, list):
                # If it returned a list (unlikely since we gave 1 file, but possible)
                for item in response:
                    item["original_file"] = file_name
                    all_results.append(item)
                logger.info(f"Successfully screened {len(response)} candidates from {file_name}")
            else:
                logger.warning(f"Could not parse result for {file_name}. Raw output: {str(response)[:100]}...")
                all_results.append({
                    "original_file": file_name,
                    "error": "Parsing failed",
                    "raw_output": str(response)
                })
                
        except Exception as e:
            logger.error(f"Error processing {file_name}: {e}", exc_info=True)
            all_results.append({
                "original_file": file_name,
                "error": str(e)
            })

    # Create DataFrame and Export to Excel
    if all_results:
        df = pd.DataFrame(all_results)
        
        # Reorder columns to put 'name' and 'match_score' first if they exist
        cols = df.columns.tolist()
        preferred_order = ["name", "confidence_score", "certification", "experience_comparison", "skills", "original_file"]
        existing_preferred = [c for c in preferred_order if c in cols]
        remaining = [c for c in cols if c not in existing_preferred]
        df = df[existing_preferred + remaining]
        
        df.to_excel(output_file, index=False)
        logger.info(f"--- SUCCESS: Results saved to {output_file} ---")
        
        # Save to Database with batch_id
        await save_results_to_db(all_results, user_id, batch_id)
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