from utils.model_loader import get_embedding_model, rerank_documents
import asyncio
from typing import List , Dict , Any , Tuple
import httpx
from utils.logging_utils import set_system_logger
from document_processing.textsplitter import split_documents
from routes.endpoint.filesendpoint import get_documents_by_status
from embedding.pinecone_index import get_pinecone_index
from pathlib import Path
from langsmith import traceable
import uuid
import os


logger = set_system_logger("system_logger")

# this function will get the embeddings for the text of the user query not for the document chunks
async def get_embeddings(text : str) -> List[float]:
    try: 
        logger.info(f"--- processing embeddings for query: {text} ---")
        text = " ".join(text.split())
        embedding_client = await get_embedding_model()
        embedding = embedding_client.embed_query(text)
        logger.info(f"--- Embeddings generated for text: {text} ---")
        return embedding
    except Exception as e:
        logger.error(f"=== Error getting embeddings for text: {text} ===")
        logger.error(f"--- {e} ---")
        return None 

# this function will get the embeddings for the document chunks
async def process_embedding_batch(chunks,file_path,batch_idx):
    try:
        logger.info(f"--- Processing embedding batch for file: {file_path}, batch index: {batch_idx}, chunks: {len(chunks)} ---")
        embedding_client = await get_embedding_model()
        text = [chunk.page_content for chunk in chunks]
        retries = 2
        for attempt in range(retries+1):
            try:
                loop = asyncio.get_event_loop()
                embeddings = await loop.run_in_executor(None, lambda: embedding_client.embed_documents(text))
                logger.info(f"--- Embeddings generated for file: {file_path} ---")
                return batch_idx, embeddings, chunks
            except Exception as e:
                logger.warning(f"--- failed to generate embeddings for file: {file_path}, batch: {batch_idx}, attempt: {attempt+1} ---")
                logger.error(f"--- {e} ---")
                if attempt < retries:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise
    except Exception as e:
        logger.error(f"=== all attempts failed to generate embeddings for file: {file_path}, exception: {e} ===")
        return batch_idx, None, chunks


@traceable(run_type="retriever",  name = "query_similar_documents")
async def query_similar_documents(query : str , user_id : str = None , top_k : int = 3 , pinecone_filter : dict = None)-> Dict[str , Any]:
    if user_id is None:
        logger.error("User ID is required for query_similar_documents")
        raise ValueError("query_similar_documents: user_id must be provided")
    if not query:
        logger.error("Query is required for query_similar_documents")
        raise ValueError("query_similar_documents: query must be provided")

    loop = asyncio.get_running_loop()
    
    try:
        index = await get_pinecone_index()
        if index is None:
            logger.error(f"=== Pinecone index not found ===")
            return {"matches": [], "no_results": True}
        logger.info(f"--- Processing query for user: {user_id} ---")
        query_embedding = await get_embeddings(query)
        if query_embedding is None:
            logger.error(f"=== Failed to generate embeddings for query: {query} ===")
            raise ValueError(f"store_embeddings: query embeddings not generated for query: {query}")
        all_matches = []

        if user_id:
            namespace = "estuate-data-"+user_id
            logger.info(f"--- query using user id : {user_id} and namespace : {namespace} ---")
            user_result = await loop.run_in_executor(None, lambda: index.query(
                vector=query_embedding,
                top_k=top_k,
                namespace=namespace,
                filter=pinecone_filter or {},
                include_metadata=True
            ))
            if user_result and user_result.matches:
                logger.info(f"--- found {len(user_result.matches)} matches for user {user_id} ---")
                all_matches.extend(user_result.matches)
            else:
                logger.info(f"--- no matches found for user {user_id} ---")

            documents_for_reranking = [{"text": match.metadata.get("text" , "")} for match in all_matches]
            reranked_documents_result = await loop.run_in_executor(None, lambda: rerank_documents(query , documents_for_reranking))
            reranked_documents = []
            for item in reranked_documents_result.results:       
                idx = item.index 
                score = item.relevance_score
                if idx < len(all_matches):
                    match = all_matches[idx]
                    pinecone_score = getattr(match , "score" , 0.0)
                    match.metadata["reranked_score"] = score
                    match.metadata["pinecone_score"] = pinecone_score
                    match.score = score
                    reranked_documents.append(match)
                else:
                    logger.warning(f"--- Invalid index {idx} for match {match} ---")
            
            reranked_documents.sort(key = lambda m: m.metadata["reranked_score"] , reverse = True)

            final_matches = reranked_documents[:top_k]

            return {"matches" : final_matches,
                    "no_results" : False }
    except Exception as e:
        logger.error(f"=== Error querying similar documents and reranking for user: {user_id} ===")
        logger.error(f"--- {e} ---")
        return {"matches" : [],
                "no_results" : True }


async def store_embeddings(specific_files : List[str] = None, user_id : str = None, progeress_callback = None , processing_mode :str = "pymupdf4llm")->Dict[str,bool]:
    """
    Store embeddings for files into Pinecone under per-user namespace.
    user_id: REQUIRED for user uploads; set to None only for global/shared (e.g., shared_data).
    """
    if user_id is None:
        logger.error(f"User ID is required for file: {file_path}")
        raise ValueError(f"store_embeddings: user_id must be provided for user upload containers: {container_name}")

    index = await get_pinecone_index()

    if index is None:
        logger.error(f"Pinecone index not found for file: {file_path}")
        raise ValueError(f"store_embeddings: pinecone index not found for file: {file_path}")

    results = {}
    LOADING_SPLITTING_START, LOADING_SPLITTING_END = 20, 55
    EMBEDDING_START, EMBEDDING_END = 55, 90
    UPSERT_START, UPSERT_END = 90, 98

    if not specific_files:
        logger.info(f"--- No specific files provided. Querying database for documents in 'Processing' state ---")
        specific_files = await get_documents_by_status(status = "not_processed", user_id = user_id)
        if not specific_files:
            logger.info(f"--- No documents found in 'not_processed' state ---")
            return {}
    
    # Define progress ranges for each major phase within this function
    LOADING_SPLITTING_START, LOADING_SPLITTING_END = 15, 54
    EMBEDDING_START, EMBEDDING_END = 55, 90
    UPSERT_START, UPSERT_END = 91, 98

    import time
    start_time = time.perf_counter()
    namespace = "estuate-data-"+user_id
    
    for file_path in specific_files:
        try:
            logger.info(f"=== STARTING DOCUMENT CHUNKING FOR : {Path(file_path).name} ===")
            chunks = await split_documents(files_to_process=[file_path], user_id=user_id)
            
            if not chunks:
                results[file_path] = False
                continue
            
            #step 2 : organize chunks into batches
            batch_size = 150
            total_chunks = len(chunks)
            batches = [
                (chunks[i:i+batch_size], i // batch_size)
                for i in range(0, total_chunks, batch_size)
            ]
            chunking_time = time.perf_counter() - start_time
            logger.info(f"=== Document chunking completed for file: {file_path} in {chunking_time:.2f} seconds with total {total_chunks} chunks ===")
            
            start_time = time.perf_counter()
            logger.info(f"=== STARTING EMBEDDING FOR : {Path(file_path).name} ===")
            embedding_tasks = [
                asyncio.create_task(process_embedding_batch(batch_chunks, file_path, batch_idx))
                for batch_chunks , batch_idx in batches
            ]

            batch_result = {}
            for i in range(0,len(embedding_tasks), 4 ):
                batch_group = embedding_tasks[i:i+4]
                group_results = await asyncio.gather(*batch_group)
                for idx , embedding , batch_chunks in group_results:
                    batch_result[idx] = (embedding , batch_chunks)

                completed = i + len(batch_group)
 
                if progeress_callback:
                    await progress_callback(completed, len(embedding_tasks), EMBEDDING_START, EMBEDDING_END)
                
                if i + 4 < len(embedding_tasks):
                    await asyncio.sleep(0.1)

            embedding_time = time.perf_counter() - start_time
            logger.info(f"=== Embeddings generated for file: {Path(file_path).name} - {len(embedding_tasks)} batches in {embedding_time:.2f} seconds ===")
            

            # Phase 4 : vector upsert to pinecone(80 - 98%)
            start_time = time.perf_counter()
            logger.info(f"=== Starting vector upsert for file: {Path(file_path).name} ===")
            batch_count = len(batch_result)
            completed_upsert = 0 
            for batch_idx in sorted(batch_result.keys()):
                embedding , batch_chunks = batch_result[batch_idx]
                if embedding is None:
                    continue

                batch_start = batch_idx * batch_size

                vectors = []
                for i , (chunk , emb) in enumerate(zip(batch_chunks , embedding)):
                    vector_id = str(uuid.uuid5(uuid.NAMESPACE_DNS , f"{file_path}-chunk-{batch_start + i}"))
                    vectors.append({
                        "id": vector_id,
                        "values": emb,
                        "metadata": {
                            "user_id": user_id,
                            "text": chunk.page_content,
                            "file_path": file_path,
                            "file_name": os.path.basename(file_path),
                            "chunk_index": chunk.metadata.get("chunk_index", 0),
                            "chunk_total": chunk.metadata.get("chunk_total", 1),
                            "created_at": chunk.metadata.get("created_at", ""),
                            "last_modified": chunk.metadata.get("last_modified", ""),
                            "content_type" : chunk.metadata.get("content_type", ""),
                            "processing_mode" : chunk.metadata.get("processing_mode", ""),
                            "extension" : chunk.metadata.get("ext", ""),
                            "title": "",
                            "entities": []
                        }
                    })

                    #strict : Use correct Pinecone namespace!
                    max_retries = 3 
                    for attempt in range(max_retries):
                        try:
                            logger.info(f"--- uploading vectors for : {Path(file_path).name} to namespace : {namespace} ---")
                            await asyncio.get_event_loop().run_in_executor(
                                None,
                                lambda : index.upsert(
                                    vectors=vectors,
                                    namespace=namespace
                                )
                            )
                            logger.info(f"--- vector batches {batch_idx + 1} / {len(batch_result)} for file {Path(file_path).name} uploaded successfully ---")
                            break
                        except Exception as e:
                            logger.warning(f"--- failed to upload vectors for file: {file_path}, batch: {batch_idx}, attempt: {attempt+1} ---")
                            if attempt < max_retries:
                                await asyncio.sleep(2 ** attempt)
                            else:
                                logger.error(f"=== all attempts failed to upload vectors for file: {file_path}, batch: {batch_idx} ===")
                                raise

                    completed_upsert += 1
                    if progeress_callback:
                        await progress_callback(completed_upserts, batch_count, UPSERT_START, UPSERT_END)
                upsert_time = time.perf_counter() - start_time
                logger.info(f"=== vector upsert completed for file: {Path(file_path).name} - {completed_upsert} batches in {upsert_time:.2f} seconds ===")
                results[file_path] = True
                from routes.endpoint.filesendpoint import update_file_status
                await update_file_status(file_path = file_path , status = "processed" , user_id = user_id)
               

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}", exc_info=True)
            results[file_path] = False

    return results
                
                


                
            
                
            
            

    