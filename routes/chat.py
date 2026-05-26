from fastapi import APIRouter, Request , Depends
from fastapi.responses import JSONResponse
from agents.agents_main import RAGAgent
from langchain_openai import ChatOpenAI
from langsmith import traceable
from dotenv import load_dotenv
import os   
load_dotenv()   
from routes.auth import login_required
from utils.logger_instances import chat_logger as logger
from pydantic import BaseModel
from typing import List , Dict , Any , Optional

import uuid
import datetime
chat_router = APIRouter()

class ChatRequest(BaseModel):
    query: str
    history: Optional[List[Dict[str, Any]]] = []
    thread_id: Optional[str] = None
    file_context: Optional[List[Dict[str, Any]]] = []
    file_names: Optional[List[str]] = []

@chat_router.post("/query")
async def process_query(request: Request , chat_request : ChatRequest , session= Depends(login_required)):
    user_id = session["user_id"]
    
    @traceable(run_type="chain", name="process_query")
    async def _run(chat_request : ChatRequest):
        query = chat_request.query
        history = chat_request.history
        thread_id = chat_request.thread_id
        file_context = chat_request.file_context or []
        file_names = chat_request.file_names or []
        
        try:
            if thread_id is None:
                thread_title = query[:50]
                logger.info("=== Thread ID is not provided, creating a new thread_id ===")
                from db.endpoints.chat_thread import create_chat_thread
                thread = await create_chat_thread(user_id , thread_title)
                if not thread:
                    logger.error("=== Thread creation failed ===")
                    return JSONResponse(status_code=500, content={'error': 'Failed to create chat thread.'})
                thread_id = str(thread["thread_id"])
                logger.info(f"=== Thread ID created successfully: {thread_id} ===")
            else:
                logger.info(f"=== Thread ID: {thread_id} ===")
        except Exception as e:
            logger.error(f"=== Error creating/checking chat thread for user {user_id}: {e} ===")
            return JSONResponse(status_code=500, content={'error': f'Thread error: {str(e)}'})
            
        try:
            llm = ChatOpenAI(model="gpt-5.4-mini", api_key=os.getenv("OPENAI_API_KEY"), temperature=0.0)
            logger.info(f"--- User ID: {user_id} ---")
            agent_instance = RAGAgent(client=llm , user_id=user_id)
            logger.info(f"--- Agent instance: {agent_instance} ---")
            logger.info(f"=== Starting agent process for query: {query} ===")
            
            response, verified_chunks, source = await agent_instance.run_agent(query=query, messages=history, user_id=user_id, pinecone_filter=file_names)
            
            # Source usually indicates 'Document derived' or 'LLM derived'
            confidence = 1.0 if source == 'Document derived' else 0.5
            
            now = datetime.datetime.now(datetime.timezone.utc)
            user_message = {
                "message_id": str(uuid.uuid4()), 
                "role": "user", 
                "content": query,
                "timestamp": now,
                "file_names": file_names
            }
            assistant_message = {
                "message_id": str(uuid.uuid4()), 
                "role": "assistant", 
                "content": response,
                "timestamp": now, 
                "citations": verified_chunks, 
                "confidence_level": confidence,
                "file_names": file_names
            }
            
            messages_to_store = [user_message, assistant_message] 
            from db.endpoints.chat_thread import append_message_to_thread
            await append_message_to_thread(user_id, messages_to_store, thread_id, file_context)
            
            logger.info(f"=== Agent response complete: {response[:100]}... ===")

            return {
                'response': response,
                'citations': verified_chunks,
                'confidence_level': confidence,
                'show_citations': True,
                'thread_id': str(thread_id) 
            }
        except Exception as e:
            logger.error(f"=== Error processing query for user {user_id}: {e} ===")
            return JSONResponse(status_code=500, content={'error': f'Processing error: {str(e)}'})

    response_data = await _run(chat_request)
    return response_data

@chat_router.get("/threads")
async def get_threads(session=Depends(login_required)):
    user_id = session["user_id"]
    from db.endpoints.chat_thread import get_user_threads
    threads = await get_user_threads(user_id)
    return threads

@chat_router.get("/history/{thread_id}")
async def get_history(thread_id: str, session=Depends(login_required)):
    user_id = session["user_id"]
    from db.endpoints.chat_thread import get_thread_messages
    messages = await get_thread_messages(thread_id)
    return messages
class RenameThreadRequest(BaseModel):
    thread_title: str

@chat_router.delete("/delete/{thread_id}")
async def delete_chat_thread(thread_id: str, session=Depends(login_required)):
    user_id = session["user_id"]
    from db.endpoints.chat_thread import delete_thread
    result = await delete_thread(thread_id, user_id)
    return result

@chat_router.put("/rename/{thread_id}")
async def rename_chat_thread(thread_id: str, request: RenameThreadRequest, session=Depends(login_required)):
    user_id = session["user_id"]
    from db.endpoints.chat_thread import rename_thread
    result = await rename_thread(thread_id, request.thread_title, user_id)
    return result
