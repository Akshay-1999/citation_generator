from db.config import Database
from utils.logger_instances import file_convert_logger as logger
from pathlib import Path
import uuid
from typing import List, Dict, Any
# pyrefly: ignore [missing-import]
from fastapi import HTTPException

async def write_converted_file_path(user_id : str , original_file : str , converted_pdf_file_path : str , converted_docx_file_path : str):
    """
    Write the converted file path to the database.
    """
    logger.info(f"--- Writing converted file path for file: {original_file} ---")
    pool = await Database.get_pool()
    async with pool.acquire() as connection:
        try:
            logger.info(f"--- Writing converted file path: {converted_pdf_file_path} and {converted_docx_file_path} for file: {original_file} ---")
            await connection.execute(
                """
                INSERT INTO core.converted_resumes (user_id, original_file, converted_pdf_file_path, converted_docx_file_path, created_at, updated_at, status, is_deleted)
                VALUES ($1, $2, $3, $4, now(), now(), 'completed', false)
                """,
                user_id,
                original_file,
                converted_pdf_file_path,
                converted_docx_file_path
            )
            logger.info(f"=== Converted file path written successfully for file: {original_file} ===")
        except Exception as e:
            logger.error(f"=== Error writing converted file path for file {original_file}: {e} ===")

async def write_rejected_file_path(user_id : str , original_file : str , rejection_reason : str):
    """
    Write the rejected file path to the database.
    """
    logger.info(f"--- Writing rejected file path for file: {original_file} ---")
    pool = await Database.get_pool()
    async with pool.acquire() as connection:
        try:
            logger.info(f"--- Writing rejected file path: {original_file} ---")
            converted_paths = await connection.fetchrow(
                """
                UPDATE core.converted_resumes
                set rejection_reason = $1 , status = 'rejected' , is_deleted = true , deleted_at = now()
                WHERE user_id = $2 AND original_file = $3 AND is_deleted = false
                RETURNING converted_pdf_file_path, converted_docx_file_path
                """,
                rejection_reason,
                user_id,
                original_file
            )
            logger.info(f"=== Rejected file path written successfully for file: {original_file} ===")
            return converted_paths
        except Exception as e:
            logger.error(f"=== Error writing rejected file path for file {original_file}: {e} ===")
            return None

async def check_converted_status(user_id : str , file_path : str):
    """
    Check if the file has already been converted.
    """
    logger.info(f"--- Checking if file has already been converted: {file_path} ---")
    pool = await Database.get_pool()
    async with pool.acquire() as connection:
        try:
            logger.info(f"--- Checking converted status for file: {file_path} ---")
            row = await connection.fetchrow(
                """
                SELECT id, converted_pdf_file_path,converted_docx_file_path, status
                FROM core.converted_resumes
                WHERE user_id = $1 AND original_file = $2 AND is_deleted = false
                """,
                user_id,
                file_path
            )
            if row:
                logger.info(f"--- Converted file path found exist ---")
                message = {"pdf_file_path" : row["converted_pdf_file_path"] , "docx_file_path" : row["converted_docx_file_path"]}
                return message
            else:
                logger.info(f"--- Converted status not found for file: {file_path} ---")
                return None
        except Exception as e:
            logger.error(f"=== Error checking converted status for file {file_path}: {e} ===")
            return None
