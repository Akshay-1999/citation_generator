"""
Example: Extract text from .docx files using unstructured (via LangChain)
Two approaches shown below — pick whichever fits your use case.
"""

# ─── Approach 1: Using LangChain's UnstructuredWordDocumentLoader ───
# This is what your codebase already imports in document_loader.py

from langchain_community.document_loaders import UnstructuredWordDocumentLoader
from unstructured.partition.docx import partition_docx
import time

file_path = r'C:\Users\akpatil\Downloads\MTIC 100  Oracle Developer – ERP Implementation Job Description (1) (1).docx'

print("=" * 60)
print("APPROACH 1: LangChain UnstructuredWordDocumentLoader")
print("=" * 60)

start = time.perf_counter()

# mode="elements" → splits into paragraphs, tables, headers etc.
# mode="single"   → returns entire doc as one Document (default)
loader = UnstructuredWordDocumentLoader(file_path, mode="elements")
documents = loader.load()

elapsed = time.perf_counter() - start

print(f"\n✅ Loaded {len(documents)} elements in {elapsed:.2f}s\n")

for i, doc in enumerate(documents[:5]):  # Show first 5 elements
    print(f"--- Element {i+1} ---")
    print(f"  Type    : {doc.metadata.get('category', 'unknown')}")
    print(f"  Content : {doc.page_content[:150]}...")
    print()

# Combine all elements into single text (this is what you'd feed to embeddings)
full_text = "\n\n".join([doc.page_content for doc in documents if doc.page_content.strip()])
print(f"📄 Total combined text length: {len(full_text)} characters")
print(f"📄 Total combined text preview:\n{full_text[:500]}...\n")


# ─── Approach 2: Using unstructured directly (without LangChain wrapper) ───
print("=" * 60)
print("APPROACH 2: Direct unstructured library")
print("=" * 60)

from unstructured.partition.docx import partition_docx

start = time.perf_counter()
elements = partition_docx(filename=file_path)
elapsed = time.perf_counter() - start

print(f"\n✅ Partitioned into {len(elements)} elements in {elapsed:.2f}s\n")

for i, element in enumerate(elements[:5]):  # Show first 5
    print(f"--- Element {i+1} ---")
    print(f"  Type    : {type(element).__name__}")
    print(f"  Content : {str(element)[:150]}...")
    print(f"total text = {len(str(element))}")


# ─── Example function matching YOUR codebase's pattern ───
# This is how extract_with_unstructured() would look in your data_extraction.py
print("=" * 60)
print("APPROACH 3: Function matching your pipeline's signature")
print("=" * 60)

import asyncio
import datetime
from pathlib import Path
from typing import Optional, Tuple

async def extract_with_unstructured(file_path: str) -> Tuple[str, dict]:
    """
    Extract text from .doc/.docx files using UnstructuredWordDocumentLoader.
    Returns (text, metadata) — same interface as extract_with_pymupdf().
    """
    start_time = time.perf_counter()
    start_timestamp = datetime.datetime.now()
    
    metadata = {
        "chunk_name": file_path,
        "processing_tool": "unstructured_docx",
        "start_timestamp": start_timestamp,
        "processing_time": 0,
        "task_id": "N/A",
        "fallback_reason": "N/A",
        "number_of_pages": None,  # DOCX doesn't have physical pages
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
        
        print(f"✅ extract_with_unstructured completed in {processing_time:.2f}s")
        print(f"   Text length: {len(result)} characters")
        
        return result, metadata
        
    except Exception as e:
        print(f"❌ Error: {e}")
        processing_time = time.perf_counter() - start_time
        metadata["processing_time"] = processing_time
        return "", metadata


# Run the async function
text, meta = asyncio.run(extract_with_unstructured(file_path))
print(f"\n📄 Extracted text preview:\n{text[:300]}...")
print(f"\n📋 Metadata: {meta}")
