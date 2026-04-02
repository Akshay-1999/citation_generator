import fitz
import tempfile
import os
from contextlib import contextmanager


from utils.logging_utils import set_system_logger
logger = set_system_logger("system_logger")

def split_pdf_create_chunk(pdf_doc , chunk_size : int = 50):
    num_pages = len(pdf_doc)
    chunk_info = []
    if num_pages == 0:
        return []
    for start_page in range(0 , num_pages , chunk_size):
        end_page = min(start_page + chunk_size , num_pages)

        chunk_doc = fitz.open()
        chunk_doc.insert_pdf(pdf_doc , from_page = start_page , to_page = end_page)
        temp_fd , temp_path = tempfile.mkstemp(suffix=".pdf")
        try:
            os.close(temp_fd)
            chunk_doc.save(temp_path , garbage=4 , deflate=True)
            chunk_info.append({
                "file_path" : temp_path,
                "start_page" : start_page,
            })
            chunk_doc.close()
        except Exception as e:
            logger.error(f"=== Error creating chunk: {e} ===")
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            raise e
    logger.info(f"=== Successfully created {len(chunk_info)} processing chunks ===")
    return chunk_info

@contextmanager
def temp_pdf_file():
    """Context manager for temporary PDF files with guaranteed cleanup."""
    temp_fd, temp_path = tempfile.mkstemp(suffix=".pdf")
    os.close(temp_fd)
    try:
        yield temp_path
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)