import asyncio
import os
import pandas as pd
from langchain_openai import ChatOpenAI
import json
import uuid
from db.config import Database
from dotenv import load_dotenv
from agents.agents_main import ResumeMappingAgent

load_dotenv()

async def save_results_to_db(results: list, user_id: str):
    """Save screening results to the core.bulk_screening_results table."""
    print(f"--- Saving {len(results)} results to database ---")
    pool = await Database.get_pool()
    async with pool.acquire() as conn:
        try:
            # Prepare the query
            query = """
                INSERT INTO core.bulk_screening_results (
                    user_id, name, confidence_score, certification, experience_comparison, 
                    skills, original_file, phone, email, experience_in_resume, 
                    last_company, gaps, stability, resume_gaps_against_jd, error
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
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
                    res.get("error") # Add error column
                )
                insert_data.append(data)
            
            # Execute bulk insertion
            await conn.executemany(query, insert_data)
            print("--- Database insertion completed successfully ---")
            
        except Exception as e:
            print(f"--- Error inserting results to database: {e} ---")


async def process_resumes_to_excel(job_description: str, file_names: list, user_id: str, output_file: str):
    """
    Approach: Iterate through resumes one by one and collect results.
    This ensures that the LLM focuses on one candidate at a time, 
    reducing errors and ensuring clean JSON output for each.
    """
    client = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
    agent = ResumeMappingAgent(client=client)
    
    all_results = []
    
    print(f"--- Starting Bulk Processing for {len(file_names)} resumes ---")

    if not file_names:
        print("--- WARNING: No file names provided for bulk processing ---")
        return
    
    for file_name in file_names:
        print(f"\n[Processing]: {file_name}...")
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
                print(f"Successfully screened {response.get('name', 'Unknown')}")
            elif isinstance(response, list):
                # If it returned a list (unlikely since we gave 1 file, but possible)
                for item in response:
                    item["original_file"] = file_name
                    all_results.append(item)
                print(f"Successfully screened {len(response)} candidates from {file_name}")
            else:
                print(f"Warning: Could not parse result for {file_name}. Raw output: {str(response)[:100]}...")
                all_results.append({
                    "original_file": file_name,
                    "error": "Parsing failed",
                    "raw_output": str(response)
                })
                
        except Exception as e:
            print(f"Error processing {file_name}: {e}")
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
        print(f"\n--- SUCCESS: Results saved to {output_file} ---")
        print(df[["name", "confidence_score", "experience_comparison"]].to_string())
        
        # Save to Database
        await save_results_to_db(all_results, user_id)
    else:
        print("\n--- No results to save ---")