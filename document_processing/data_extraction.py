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
from langchain_community.document_loaders import UnstructuredWordDocumentLoader
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
            
        # Detect silent failures where pymupdf4llm only extracts tables and misses the main text
        doc = fitz.open(file_path)
        try:
            fitz_len = sum(len(page.get_text()) for page in (doc[i] for i in (page_range if page_range else range(len(doc)))))
            if len(result.strip()) < 1000 and fitz_len > len(result.strip()) + 500:
                raise Exception(f"pymupdf4llm returned only {len(result.strip())} chars, but fitz found {fitz_len} chars. Forcing fallback.")
            
            # Prevent resume headers (Name, Contact) from being stripped
            if len(doc) > 0:
                first_page_text = doc[0].get_text().strip()
                if first_page_text:
                    header_text = first_page_text[:300]
                    # If the first 50 characters of the raw text are missing from the markdown, prepend the header
                    if header_text[:50].strip() and header_text[:50].strip() not in result:
                        logger.info(f"--- Prepended stripped header for {Path(file_path).name} ---")
                        result = header_text + "\n\n" + result
        finally:
            doc.close()

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

async def extract_with_unstructured(file_path: str, page_range: Optional[List[int]] = None) -> str:
    start_time = time.perf_counter()
    start_timestamp = datetime.datetime.now()
    logger.info(f"=== USING UNSTRUCTURED TOOL FOR FILE: {Path(file_path).name} ===")
    metadata={
        "chunk_name": file_path,
        "processing_tool": 'unstructured_docx',
        "start_timestamp": start_timestamp,
        "processing_time": 0,
        "task_id": "N/A",
        "fallback_reason": "N/A",
        "number_of_pages": None
    }
    loop = asyncio.get_running_loop()
    try:
        def _load_docx():
            loader = UnstructuredWordDocumentLoader(file_path, mode="elements")
            docs = loader.load()
            # Combine all elements into a single text string
            text = "\n\n".join([doc.page_content for doc in docs if doc.page_content.strip()])
            return text
        
        result = await loop.run_in_executor(None, _load_docx)
        
        processing_time = time.perf_counter() - start_time
        metadata["processing_time"] = processing_time
        
        logger.info(f"=== UNSTRUCTURED EXTRACTION COMPLETED FOR FILE: {Path(file_path).name} - SUCCESS IN {processing_time:.2f} seconds ===")
        
        return result, metadata
        
    except Exception as e:
        logger.error(f"=== unstructured extraction failed: {e} ===")
        processing_time = time.perf_counter() - start_time
        metadata["processing_time"] = processing_time
        return "", metadata
