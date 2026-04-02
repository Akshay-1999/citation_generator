import datetime
from pathlib import Path
from typing import AsyncIterator, List, Optional, Tuple
import asyncio
import aiofiles
import io
import re,os
import os
from bs4 import BeautifulSoup
import fitz
import pymupdf4llm
from langchain.schema import Document
import time
from utils.logging_utils import set_system_logger
logger = set_system_logger("system_logger")


async def extract_with_pymupdf(file_path: str, page_range: Optional[List[int]] = None) -> str:
    start_time = time.perf_counter()
    start_timestamp = datetime.datetime.now()
    logger.info(f"=== USING PYMUPDF TOOL FOR FILE: {Path(file_path).name} ===")
    metadata={
        "chunk_name": file_path,
        "processing_tool": 'pymupdf4llm',
        "start_timestamp": start_timestamp,
        "processing_time": 0,
        "task_id": "N/A",
        "fallback_reason": "N/A"
    }
    loop = asyncio.get_running_loop()
    try:
        if page_range:
            result = await loop.run_in_executor(
                None, 
                lambda: pymupdf4llm.to_markdown(file_path, pages=page_range)
            ) or ""
        else:
            result = await loop.run_in_executor(
                None, 
                lambda: pymupdf4llm.to_markdown(file_path)
            ) or ""
        processing_time = time.perf_counter() - start_time
        metadata["processing_time"] = processing_time
        logger.info(f"=== PYMUPDF EXTRACTION COMPLETED FOR FILE: {Path(file_path).name} - SUCCESS IN {processing_time:.2f} seconds ===")
        return result, metadata
    except Exception as e:
        logger.error(f"=== pymupdf4llm extraction failed: {e} ===")
        # Fallback: extract plain text using fitz
        logger.info(f"--- Falling back to fitz plain-text extraction for: {Path(file_path).name} ---")
        try:
            def _fitz_fallback():
                doc = None
                try:
                    doc = fitz.open(file_path)
                    pages = page_range if page_range else range(len(doc))
                    text_parts = []
                    for page_num in pages:
                        if page_num < len(doc):
                            text_parts.append(doc[page_num].get_text())
                    return "\n\n".join(text_parts)
                finally:
                    if doc:
                        doc.close()

            result = await loop.run_in_executor(None, _fitz_fallback)
            metadata["processing_tool"] = "fitz_fallback"
            metadata["fallback_reason"] = str(e)
            processing_time = time.perf_counter() - start_time
            metadata["processing_time"] = processing_time
            logger.info(f"=== FITZ FALLBACK COMPLETED FOR FILE: {Path(file_path).name} - {'SUCCESS' if result.strip() else 'NO TEXT'} IN {processing_time:.2f} seconds ===")
            return result, metadata
        except Exception as fallback_err:
            logger.error(f"=== Fitz fallback also failed for {Path(file_path).name}: {fallback_err} ===")
            processing_time = time.perf_counter() - start_time
            metadata["processing_time"] = processing_time
            return "", metadata

