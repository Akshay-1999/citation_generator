"""
FastAPI Router for Claude MCP (Model Context Protocol) Server.
Supports:
1. SSE Transport: GET /mcp/sse and POST /mcp/messages
2. Streamable HTTP / JSON-RPC: POST /mcp and POST /mcp/rpc
3. Direct REST Testing: GET /mcp/tools and POST /mcp/tools/{tool_name}
4. Claude Connector Manifest: GET /.well-known/mcp.json and GET /mcp/manifest.json
"""
import asyncio
import json
import uuid
from typing import Dict, Any, Optional

from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from mcp_server.oauth import validate_oauth_token
from mcp_server.tools import (
    execute_search_resumes,
    execute_start_screening,
    execute_get_screening_report
)
from utils.logging_utils import set_system_logger

logger = set_system_logger("mcp_server_logger")

mcp_router = APIRouter()

# ─── MCP Protocol Tool Definitions ─────────────────────────────────────────────
MCP_TOOLS = [
    {
        "name": "search_resumes",
        "description": "Semantic search across uploaded candidate resumes using Pinecone vector embeddings and Cohere reranking. Returns candidate snippets and relevance scores.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Candidate skills, technologies, job roles, or qualifications to search for (e.g. 'FastAPI and PostgreSQL backend developer')."
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of top matching resume chunks to retrieve (default: 5, max: 20).",
                    "default": 5
                },
                "file_filter": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of specific resume file names to restrict search to."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "start_screening",
        "description": "Screen candidate resumes against a Job Description. Evaluates fit, skills match, experience, and generates a structured candidate assessment.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_description": {
                    "type": "string",
                    "description": "The complete Job Description or role requirements to screen candidates against."
                },
                "file_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of resume file names to screen. If omitted, screens all uploaded resumes for the user."
                },
                "position": {
                    "type": "string",
                    "description": "Target job title or role name (e.g. 'Senior Python Engineer')."
                },
                "client_name": {
                    "type": "string",
                    "description": "Client or hiring company name (optional)."
                },
                "experience": {
                    "type": "string",
                    "description": "Required years of experience (e.g. '5+ years')."
                }
            },
            "required": ["job_description"]
        }
    },
    {
        "name": "get_screening_report",
        "description": "Retrieve candidate screening results and assessment cards for a specific batch, or list recent screening batches for the user.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "batch_id": {
                    "type": "string",
                    "description": "UUID of the screening batch to fetch detailed results for. If omitted, lists recent screening batches."
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of candidate records or batches to retrieve (default: 10, max: 50).",
                    "default": 10
                }
            }
        }
    }
]

# ─── In-memory SSE Sessions ───────────────────────────────────────────────────
# sessionId -> asyncio.Queue of event strings
_sse_sessions: Dict[str, asyncio.Queue] = {}


# ─── Core Tool Execution Dispatcher ───────────────────────────────────────────
async def dispatch_tool_call(tool_name: str, arguments: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
    user_id = user_context.get("user_id")
    username = user_context.get("username", "Claude User")
    role = user_context.get("role", "user")

    if tool_name == "search_resumes":
        query = arguments.get("query", "")
        top_k = arguments.get("top_k", 5)
        file_filter = arguments.get("file_filter")
        return await execute_search_resumes(query=query, user_id=user_id, top_k=top_k, file_filter=file_filter)

    elif tool_name == "start_screening":
        job_description = arguments.get("job_description", "")
        file_names = arguments.get("file_names")
        position = arguments.get("position")
        client_name = arguments.get("client_name")
        experience = arguments.get("experience")
        return await execute_start_screening(
            job_description=job_description,
            user_id=user_id,
            username=username,
            file_names=file_names,
            position=position,
            client_name=client_name,
            experience=experience
        )

    elif tool_name == "get_screening_report":
        batch_id = arguments.get("batch_id")
        limit = arguments.get("limit", 10)
        return await execute_get_screening_report(user_id=user_id, batch_id=batch_id, limit=limit, user_role=role)

    else:
        raise ValueError(f"Unknown MCP tool: {tool_name}")


# ─── JSON-RPC 2.0 Request Processor ───────────────────────────────────────────
async def process_jsonrpc_request(payload: Dict[str, Any], user_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    msg_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params", {}) or {}

    logger.info(f"--- [MCP] JSON-RPC method='{method}' id={msg_id} ---")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {
                        "listChanged": False
                    }
                },
                "serverInfo": {
                    "name": "recai-connector",
                    "version": "1.0.0"
                }
            }
        }

    elif method == "notifications/initialized":
        # Notification — client acknowledge initialization
        return None

    elif method == "ping":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {}
        }

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": MCP_TOOLS
            }
        }

    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {}) or {}

        try:
            result_data = await dispatch_tool_call(tool_name, arguments, user_context)
            text_response = json.dumps(result_data, indent=2, ensure_ascii=False)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": text_response
                        }
                    ],
                    "isError": not result_data.get("success", True)
                }
            }
        except Exception as err:
            logger.error(f"[MCP] Tool execution error for '{tool_name}': {err}", exc_info=True)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error executing tool {tool_name}: {str(err)}"
                        }
                    ],
                    "isError": True
                }
            }

    else:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }


# ─── 1. SSE Transport Endpoints ───────────────────────────────────────────────
@mcp_router.get("/sse")
async def mcp_sse(request: Request):
    """
    Server-Sent Events endpoint for MCP stream transport.
    Clients connect here, receive an 'endpoint' event with the messages URI,
    and receive JSON-RPC responses.
    """
    session_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    _sse_sessions[session_id] = queue

    logger.info(f"--- [MCP] New SSE stream opened session_id={session_id} ---")

    async def event_generator():
        # First send endpoint URI where client should send messages
        endpoint_url = f"/mcp/messages?sessionId={session_id}"
        yield f"event: endpoint\ndata: {endpoint_url}\n\n"

        try:
            while True:
                # Disconnect check
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"event: message\ndata: {data}\n\n"
                except asyncio.TimeoutError:
                    # Keepalive ping
                    yield ": ping\n\n"
        finally:
            _sse_sessions.pop(session_id, None)
            logger.info(f"--- [MCP] SSE stream closed session_id={session_id} ---")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@mcp_router.post("/messages")
async def mcp_messages(
    request: Request,
    sessionId: Optional[str] = Query(None),
    user_context: dict = Depends(validate_oauth_token)
):
    """
    Message receiver for SSE transport.
    Processes JSON-RPC and sends response to SSE queue or returns it directly.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    response = await process_jsonrpc_request(body, user_context)

    # If an SSE session is active for this client, push response to the stream
    if sessionId and sessionId in _sse_sessions and response is not None:
        await _sse_sessions[sessionId].put(json.dumps(response))
        return JSONResponse(status_code=202, content={"status": "accepted"})

    # Otherwise return standard JSON-RPC HTTP response
    if response:
        return JSONResponse(content=response)
    return JSONResponse(status_code=204, content=None)


# ─── 2. Direct JSON-RPC Endpoints (POST /mcp and POST /mcp/rpc) ───────────────
@mcp_router.post("")
@mcp_router.post("/")
@mcp_router.post("/rpc")
async def mcp_rpc(
    request: Request,
    user_context: dict = Depends(validate_oauth_token)
):
    """
    Direct JSON-RPC 2.0 endpoint for Streamable HTTP clients (Claude Desktop, inspector, curl).
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # Handle batch or single JSON-RPC
    if isinstance(body, list):
        responses = []
        for req in body:
            res = await process_jsonrpc_request(req, user_context)
            if res is not None:
                responses.append(res)
        return JSONResponse(content=responses)
    else:
        res = await process_jsonrpc_request(body, user_context)
        if res is not None:
            return JSONResponse(content=res)
        return JSONResponse(status_code=204, content=None)


# ─── 3. Developer REST Testing Endpoints ──────────────────────────────────────
@mcp_router.get("/tools")
async def list_tools():
    """List available MCP tools and schemas."""
    return {"tools": MCP_TOOLS}


class ToolInvokeRequest(BaseModel):
    arguments: Dict[str, Any] = {}


@mcp_router.post("/tools/{tool_name}")
async def invoke_tool_rest(
    tool_name: str,
    payload: ToolInvokeRequest,
    user_context: dict = Depends(validate_oauth_token)
):
    """
    Direct REST endpoint to invoke a tool (for manual developer testing with curl / Postman).
    """
    try:
        result = await dispatch_tool_call(tool_name, payload.arguments, user_context)
        return JSONResponse(content=result)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error executing REST tool {tool_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ─── 4. Claude Connector Manifest & Discovery ──────────────────────────────────
@mcp_router.get("/manifest.json")
async def mcp_manifest(request: Request):
    """Claude Connector Manifest metadata."""
    base_url = str(request.base_url).rstrip("/")
    return {
        "schema_version": "v1",
        "name_for_model": "recai_connector",
        "name_for_human": "RecAI Resume Screening & Search",
        "description_for_model": "RecAI connects Claude to candidate resume libraries, semantic vector search, and AI-powered job screening.",
        "description_for_human": "Search candidate resumes and screen applicants against job descriptions directly inside Claude.",
        "logo_url": f"{base_url}/static/favicon.ico",
        "auth": {
            "type": "oauth",
            "authorization_url": f"{base_url}/oauth/authorize",
            "token_url": f"{base_url}/oauth/token",
            "scope": "read write"
        },
        "mcp": {
            "transport": "sse",
            "sse_url": f"{base_url}/mcp/sse",
            "messages_url": f"{base_url}/mcp/messages"
        },
        "tools_count": len(MCP_TOOLS)
    }
