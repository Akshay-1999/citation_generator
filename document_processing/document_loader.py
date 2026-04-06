from langchain.schema import Document
from langchain_community.document_loaders import (
    PyMuPDFLoader,
    UnstructuredWordDocumentLoader,
    TextLoader,
    CSVLoader
)
import asyncio
from pathlib import Path
import fitz
import tempfile
import os
import datetime
from utils.logging_utils import set_system_logger
from document_processing.document_chunking import split_pdf_create_chunk
from typing import Optional , AsyncIterator ,List

from document_processing.data_extraction import extract_with_pymupdf
import uuid
from routes.endpoint.filesendpoint import get_document_id , add_chunks_data

logger = set_system_logger("system_logger")




class MemoryEfficientFileloader:
    def __init__(self , file_path : str = None , 
                chunk_size : int = 15000 , 
                user_id : str = None,
                progress_callback: Optional[callable] = None ):
        self.file_path = file_path
        self.chunk_size = chunk_size
        self.ext = Path(file_path).suffix.lower() if file_path else None
        self.user_id = user_id
        self.progress_callback = progress_callback

        self.loader_mapping = {
            '.pdf': PyMuPDFLoader,
            '.docx': UnstructuredWordDocumentLoader,
            '.txt': TextLoader,
            '.csv': CSVLoader,
            '.md': TextLoader,
            '.json': TextLoader
        }

    def _base_metadata(self , file_name , file_path , ext , page , created_at , modified_at , user_id):
        return {
            "user_id" : user_id,
            "file_name" : file_name,
            "file_path" : file_path,
            "ext" : ext,
            "content" : 'markdown' if ext in ['.pdf', '.docx'] else 'text',
            "page" : page,
            "created_at" : created_at,
            "modified_at" : modified_at
        }

    def _error_doc(self , message : str , file_name , ext, file_path, err):
        return Document(
            page_content=message,
            metadata={
                "user_id" : self.user_id,
                "file_name" : file_name,
                "file_path" : file_path,
                "ext" : ext,
                "content_format" : "Error",
                "page" : 0,
                "error" : str(err)
            }
    )

    async def _get_file_loader(self, file_path: str):
        ext = Path(file_path).suffix.lower()
        loader_class = self.loader_mapping.get(ext)
        return loader_class(file_path) if loader_class else None

    async def _process_file(self , file_path : str , user_id : str = None , file_name: Optional[str] = None)-> AsyncIterator[Document]:
        """
        Process a file by extracting its text content and yielding it as a stream of Document objects.
        This method is memory-efficient as it processes the file in chunks and yields results as they complete.
        """
        import time
        start_time = time.perf_counter()
        file = Path(file_path)
        logger.info(f"=== Started processing file for user {user_id}: {file_path} ===")
        file_name = file_name or file.name
        ext = file.suffix.lower()
        created_at = datetime.datetime.fromtimestamp(file.stat().st_ctime).isoformat()
        modified_at = datetime.datetime.fromtimestamp(file.stat().st_mtime).isoformat()
        loop = asyncio.get_running_loop()
        try:
            if ext == ".pdf":
                chunk_details = []
                try:
                    # Step 1: Split the large PDF into smaller, temporary files for parallel processing.
                    with fitz.open(file_path) as pdf_doc:
                        logger.info(f"--- Processing PDF file: {file_path} ---")
                        num_pages = len(pdf_doc)
                        logger.info(f"--- Number of pages in PDF: {num_pages} for file {file_path} ---")
                        # Use a threshold to decide if physical chunking is necessary.
                        if num_pages > 100:
                            chunk_details = await loop.run_in_executor(None, split_pdf_create_chunk, pdf_doc , 100)
                        # If the file is small, process it as a single chunk.
                        else:
                            chunk_details = [{"file_path": file_path, "start_page": 0}]
                except Exception as e:
                    logger.error(f"=== Error processing PDF file: {e} for file {file_path} ===")
                    yield self._error_doc(f"Error processing PDF chunking: {e}", file_name, ext, str(file_path), e)
                    return 
                # Step 2: Set up an asynchronous queue to handle results as they complete.
                result_queue = asyncio.Queue()

                # Step 3: Create a list of tasks, one for each chunk parallelly. 
                async def extract_text_from_chunk(chunk_index , chunk_file , start_page):
                    logger.info(f"--- Extracting text from chunk {chunk_index+1} for file {file_path} ---")
                    try:
                        text , metadata = await extract_with_pymupdf(chunk_file)
                        try:
                            with fitz.open(chunk_file) as pdf_doc:
                                metadata["number_of_pages"] = len(pdf_doc)
                        except Exception as e:
                            logger.error(f"=== Error extracting metadata from chunk {chunk_index+1} for file {file_path}: {e} ===")
                            metadata["number_of_pages"] = None
                            metadata.setdefault("chunk_name", chunk_file)   
                        
                        await result_queue.put((chunk_index, text or "", start_page , metadata))
                        logger.debug(f"Extracted text from chunk {chunk_index+1} for file {file_path}")
                    except Exception as e:
                        logger.error(f"=== Error extracting text from chunk {chunk_index+1} for file {file_path}: {e} ===")
                        fallback_metadata = {"chunk_name": chunk_file, "number_of_pages": None} 
                        await result_queue.put((chunk_index, None, start_page , fallback_metadata))
                    finally:
                        if chunk_file != str(file_path):
                            import gc
                            gc.collect()
                            for attempt in range(3):
                                try:
                                    await asyncio.sleep(0.5)
                                    os.remove(chunk_file)
                                    break
                                except Exception as e:
                                    if attempt == 2:
                                        logger.error(f"=== Error removing chunk file {chunk_file} after 3 attempts: {e} ===")
                                    else:
                                        logger.debug(f"Retry {attempt+1} removing {chunk_file}: {e}")
                
                logger.info(f"--- Created {len(chunk_details)} tasks for processing {len(chunk_details)} chunks of file {file_path} ---")
                extract_producer_tasks = [
                    asyncio.create_task(extract_text_from_chunk(i, details["file_path"], details["start_page"]))
                    for i, details in enumerate(chunk_details)
                ]

                # # Step 4: The "Consumer" loop. This is the critical optimization.
                # It processes results as they arrive, avoiding memory accumulation.
                completed_chunks = 0
                total_chunks = len(chunk_details)
                document_id = await get_document_id(file_name , user_id)
                logger.info(f"--- Document ID for file {file_name}: {document_id} ---")

                #bulk insert
                chunks_data = []

                while completed_chunks < total_chunks:
                    try:
                        chunk_index, text, start_page, metadata = await asyncio.wait_for(result_queue.get(), timeout=900.0)
                        #adding file name to metadata
                        metadata["file_name"] = file_name
                        # Report progress as each physical chunk is processed
                        if self.progress_callback:
                            await self.progress_callback(completed_chunks, total_chunks)
                            
                        completed_chunks += 1
                        logger.info(f"--- Processing chunk {chunk_index+1} for file {file_path} ---")
                        if text and text.strip():
                            chunks_data.append((
                                document_id,
                                chunk_index,
                                metadata,
                                "success"
                            ))
                            logger.debug(f"Chunk {chunk_index+1} processed successfully for file {file_path}")
                            metadata = self._base_metadata(file_name , str(file_path) , ext , start_page , created_at , modified_at , user_id)

                            # Add the new, specific metadata fields
                            metadata['chunk_index'] = chunk_index
                            metadata['start_page'] = start_page

                            yield Document(
                                page_content=text,
                                metadata=metadata
                            )
                        else:
                            logger.warning(f"=== Chunk {chunk_index + 1} for {file.name} resulted in no content and will be skipped ===")
                            # Add chunk data to list for bulk insert
                            chunks_data.append((document_id, chunk_index, metadata, "skipped-nodata"))
                    except asyncio.TimeoutError:
                        logger.error(f"=== Timeout waiting for a result from the queue. {completed_chunks}/{len(chunk_details)} chunks processed. Aborting ===")
                        break # Exit the loop if a chunk takes too long to process.
                    except Exception as e:
                        logger.error(f"=== Error processing chunk {chunk_index+1} for file {file_path}: {e} ===")
                        # Add chunk data to list for bulk insert
                        chunks_data.append((document_id, chunk_index, metadata, "error"))
                    finally:
                        if 'result_queue' in locals() and result_queue.qsize() > 0:
                            result_queue.task_done()

                # Final cleanup: Ensure all producer tasks are finished.
                await asyncio.gather(*extract_producer_tasks, return_exceptions=True)

                # Bulk insert all chunk data at once
                if chunks_data and document_id:
                    await add_chunks_data(chunks_data)
                    logger.info(f"--- Bulk inserted {len(chunks_data)} chunks for document {file.name} ---")
                elif not document_id:
                    logger.warning(f"=== Skipping bulk insert for {file.name} — document_id is None (file not registered in DB) ===")

                processing_time = time.perf_counter() - start_time
                logger.info(f"=== PROCESSING COMPLETED FOR FILE: {file.name} - {len(chunk_details)} chunks processed IN {processing_time:.2f} seconds ===")
                return 
        except Exception as e:
            logger.error(f"=== Error processing {file_path}: {e} ===", exc_info=True)
            yield self._error_doc("Failed to process file", file, ext, str(file_path), e)


    async def _load_process_single_file(self, file_path: str, user_id: Optional[str] = None , processing_mode='pymupdf4llm')-> List[Document]:
        docs = []
        temp_path = None
        logger.info("--- Copying file to temp directory ---")
        try:
            file_name = Path(file_path).name
            suffix = Path(file_name).suffix 
            with open(file_path, "rb") as f:
                data = f.read()
            with tempfile.NamedTemporaryFile(
                        mode='wb',
                        delete=False,
                        dir=r"D:\Akshay\Work and Document\Training\LLM AND AI\citation\citation_generator\temp_processing_files",
                        suffix=suffix) as tmp:
                        temp_path = tmp.name
                        tmp.write(data)  
                        logger.info(f"--- Created temp file {temp_path} for file {file_path} ---")
                        logger.info(f"--- Processing file {file_path} with mode {processing_mode} ---")
                        async for doc in self._process_file(temp_path , user_id , file_name=file_name):
                            doc.metadata.update({
                                "file_name" : file_name,
                                "file_path" : str(file_path),
                                "user_id" : user_id,
                                "processing_mode" : processing_mode
                            })
                            docs.append(doc)
        except Exception as e:
            logger.error(f"=== Error processing {file_path}: {e} ===", exc_info=True)
            docs.append(self._error_doc("Failed to process file", file_name, self.ext, str(file_path), e))                

        finally:
            #clean up temp files
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    logger.info(f"--- Removed temp file {temp_path} ---")
                except Exception as e:
                    logger.error(f"=== Error removing temp file {temp_path}: {e} ===", exc_info=True)
        return docs
    
    async def load(self, specific_files: Optional[List[str]] = None, user_id: Optional[str] = None, processing_mode='pymupdf4llm') -> AsyncIterator[Document]:
        files_to_process = specific_files or []
        tasks = [asyncio.create_task(self._load_process_single_file(path , user_id , processing_mode)) for path in files_to_process]
        for task in asyncio.as_completed(tasks):
            for doc in await task:
                yield doc