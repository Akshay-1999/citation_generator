"""
Resume Format Converter — text extraction logic.
Previously contained ReportLab generation logic, which has been replaced by docxtpl.
"""

from pathlib import Path

# Supported resume input formats
SUPPORTED_RESUME_EXTENSIONS = {".pdf", ".docx", ".doc"}

async def extract_text(file_path: str) -> str:
    """
    Extract plain text from a resume file, reusing the existing
    battle-tested extractors in document_processing/data_extraction.py.

    - PDF  → extract_with_pymupdf  (pymupdf4llm → fitz fallback)
    - DOCX → extract_with_unstructured  (UnstructuredWordDocumentLoader
              → python-docx fallback)
    - DOC  → extract_with_unstructured  (HTML-disguised sniff → OLE binary
              stream → python-docx fallback — no LibreOffice required)
    """
    ext = Path(file_path).suffix.lower()
    if ext not in SUPPORTED_RESUME_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format '{ext}'. "
            f"Supported formats: {', '.join(sorted(SUPPORTED_RESUME_EXTENSIONS))}"
        )

    if ext == ".pdf":
        from document_processing.data_extraction import extract_with_pymupdf
        text, _ = await extract_with_pymupdf(file_path)
    else:  # .docx or .doc
        from document_processing.data_extraction import extract_with_unstructured
        text, _ = await extract_with_unstructured(file_path)

    if not text or not text.strip():
        raise ValueError(
            f"Could not extract any text from '{Path(file_path).name}'. "
            "The file may be corrupt, image-only, or password-protected."
        )

    return text
