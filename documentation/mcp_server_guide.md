# RecAI / ProfileIQ — Model Context Protocol (MCP) Server Guide

This document provides a comprehensive technical guide to the **Model Context Protocol (MCP)** server implemented in this repository. It covers architectural design, supported tools, protocol internals, security, how to launch the server, and how end-users or AI clients (like Anthropic Claude) interact with it.

---

## Table of Contents
1. [Overview & Architecture](#1-overview--architecture)
2. [Implemented Components & File Structure](#2-implemented-components--file-structure)
3. [Implemented MCP Tools](#3-implemented-mcp-tools)
   - [`search_resumes`](#tool-1-search_resumes)
   - [`start_screening`](#tool-2-start_screening)
   - [`get_screening_report`](#tool-3-get_screening_report)
4. [Protocol & Transport Layer](#4-protocol--transport-layer)
   - [SSE Transport (`/mcp/sse` & `/mcp/messages`)](#a-sse-transport)
   - [Streamable HTTP JSON-RPC (`/mcp` & `/mcp/rpc`)](#b-streamable-http-json-rpc)
   - [Direct Developer REST Endpoints (`/mcp/tools`)](#c-direct-developer-rest-endpoints)
   - [Claude Connector Manifest (`/.well-known/mcp.json`)](#d-claude-connector-manifest)
5. [Authentication & Security](#5-authentication--security)
   - [OAuth 2.1 with PKCE](#oauth-21-with-pkce)
   - [Prompt Injection Guard](#prompt-injection-guard)
   - [Sliding-Window Rate Limiting](#sliding-window-rate-limiting)
   - [Multi-Tenant Data Isolation](#multi-tenant-data-isolation)
6. [How to Start & Verify the MCP Server](#6-how-to-start--verify-the-mcp-server)
   - [Prerequisites & Environment Variables](#prerequisites--environment-variables)
   - [Starting the Server](#starting-the-server)
   - [Running the Automated Test Suite](#running-the-automated-test-suite)
7. [How to Connect AI Clients (Claude Desktop, Web, Inspector)](#7-how-to-connect-ai-clients)
   - [Claude Desktop Configuration](#claude-desktop-configuration)
   - [Official MCP Inspector Testing](#official-mcp-inspector-testing)
   - [Claude.ai Web Connector Integration](#claudeai-web-connector-integration)
8. [End-User Workflows & Example Prompts](#8-end-user-workflows--example-prompts)
9. [Testing MCP APIs via Swagger UI, cURL, & Backend](#9-testing-mcp-apis-via-swagger-ui-curl--backend)
   - [9.1 Interactive Testing in Swagger UI (`/docs`)](#91-interactive-testing-in-swagger-ui-docs)
   - [9.2 Authentication Methods for Backend Testing](#92-authentication-methods-for-backend-testing)
   - [9.3 Testing Developer REST Endpoints (`/mcp/tools/{tool_name}`)](#93-testing-developer-rest-endpoints-mcptoolstool_name)
   - [9.4 Testing JSON-RPC 2.0 Directly (`POST /mcp`)](#94-testing-json-rpc-20-directly-post-mcp)
   - [9.5 Testing SSE Transport (`/mcp/sse` & `/mcp/messages`)](#95-testing-sse-transport-mcpsse--mcpmessages)
   - [9.6 Programmatic Testing with Python (`httpx` / `requests`)](#96-programmatic-testing-with-python-httpx--requests)

---

## 1. Overview & Architecture

### What is MCP?
The **Model Context Protocol (MCP)** is an open standard created by Anthropic that allows Large Language Models (LLMs) such as Claude to securely connect to external tools, databases, and business services.

### What Does the RecAI MCP Server Do?
The RecAI MCP server exposes the core capabilities of the recruiting platform directly into Claude's conversational context:
1. **Semantic Resume Search:** Searching vector embeddings across uploaded candidate resumes via Pinecone and Cohere reranking.
2. **Batch Job Screening:** Evaluating uploaded candidate resumes against raw Job Descriptions (JDs), calculating skills match, experience fit, and candidate stability.
3. **Screening Reports & Cards:** Retrieving candidate cards, confidence scores, and downloading formatted Excel audit reports.

### Architecture Diagram

```mermaid
graph TD
    subgraph ClientLayer [AI Clients]
        ClaudeDesktop[Claude Desktop App]
        ClaudeWeb[Claude.ai Web Connector]
        MCPInspector[MCP Inspector / Developer Tools]
    end

    subgraph AuthLayer [Authentication & Security]
        OAuth[OAuth 2.1 Server + PKCE]
        RateLimit[Sliding Window Rate Limiter]
        Guard[Prompt Injection Guard]
    end

    subgraph TransportLayer [FastAPI MCP Router]
        SSE["SSE Transport (/mcp/sse, /mcp/messages)"]
        RPC["JSON-RPC 2.0 (/mcp, /mcp/rpc)"]
        REST["REST API (/mcp/tools)"]
        Manifest["Manifest Discovery (/.well-known/mcp.json)"]
    end

    subgraph ExecutionLayer [Tool Execution Dispatcher]
        T1["search_resumes()"]
        T2["start_screening()"]
        T3["get_screening_report()"]
    end

    subgraph BackendServices [Core AI & Data Services]
        Pinecone[(Pinecone Vector DB)]
        Cohere[Cohere Rerank API]
        PostgreSQL[(PostgreSQL core tables)]
        ExcelService[Excel Report Engine]
    end

    ClientLayer --> TransportLayer
    TransportLayer --> AuthLayer
    AuthLayer --> ExecutionLayer
    ExecutionLayer --> BackendServices
```

---

## 2. Implemented Components & File Structure

All MCP-specific logic is located in the [`mcp_server/`](file:///d:/Akshay/Work%20and%20Document/Training/LLM%20AND%20AI/citation/citation_generator/mcp_server) package:

| File | Purpose |
| :--- | :--- |
| [`mcp_server/__init__.py`](file:///d:/Akshay/Work%20and%20Document/Training/LLM%20AND%20AI/citation/citation_generator/mcp_server/__init__.py) | Package initialization, exports `oauth_router` and `mcp_router`. |
| [`mcp_server/server.py`](file:///d:/Akshay/Work%20and%20Document/Training/LLM%20AND%20AI/citation/citation_generator/mcp_server/server.py) | FastAPI router handling SSE streams, JSON-RPC 2.0 processing, tool dispatch, and connector manifests. |
| [`mcp_server/tools.py`](file:///d:/Akshay/Work%20and%20Document/Training/LLM%20AND%20AI/citation/citation_generator/mcp_server/tools.py) | Core logic for the 3 tools (`search_resumes`, `start_screening`, `get_screening_report`). |
| [`mcp_server/oauth.py`](file:///d:/Akshay/Work%20and%20Document/Training/LLM%20AND%20AI/citation/citation_generator/mcp_server/oauth.py) | Full OAuth 2.1 server implementation with PKCE (RFC 8414, RFC 9728), login UI, code exchange, and token validation. |
| [`mcp_server/security.py`](file:///d:/Akshay/Work%20and%20Document/Training/LLM%20AND%20AI/citation/citation_generator/mcp_server/security.py) | Security layer providing regex-based prompt injection detection, input sanitization, and sliding-window rate limiting. |
| [`app.py`](file:///d:/Akshay/Work%20and%20Document/Training/LLM%20AND%20AI/citation/citation_generator/app.py) | FastAPI application root mounting `/oauth`, `/mcp`, and `/.well-known/mcp.json`. |
| [`test_mcp_connector.py`](file:///d:/Akshay/Work%20and%20Document/Training/LLM%20AND%20AI/citation/citation_generator/test_mcp_connector.py) | Automated test suite validating OAuth, manifests, JSON-RPC protocol, tool calls, and security filters. |

---

## 3. Implemented MCP Tools

### Tool 1: `search_resumes`
Performs semantic vector search across candidate resumes uploaded by the authenticated recruiter.

* **Schema:**
  ```json
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
          "items": { "type": "string" },
          "description": "Optional list of specific resume file names to restrict search to."
        }
      },
      "required": ["query"]
    }
  }
  ```
* **Internal Workflow:**
  1. Calls `mcp_rate_limiter.check_request("search:<user_id>")`.
  2. Runs query through `PromptInjectionGuard.inspect_query(query)`.
  3. Invokes `query_similar_documents()` in `embedding/embedder.py` with recruiter's `user_id` isolation.
  4. Pinecone matches are reranked via Cohere.
  5. Snippets are truncated to safe lengths (<=600 chars) to prevent context window explosion.
  6. Returns structured candidate matches containing `candidate_name`, `file_name`, `relevance_score`, `pinecone_score`, and `text_snippet`.

---

### Tool 2: `start_screening`
Evaluates uploaded resumes against a full Job Description, generating structured assessments, fit scores, and an Excel report.

* **Schema:**
  ```json
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
          "items": { "type": "string" },
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
  }
  ```
* **Internal Workflow:**
  1. Calls `mcp_rate_limiter.check_request("screen:<user_id>")`.
  2. Sanitizes JD via `PromptInjectionGuard.inspect_job_description(job_description)`.
  3. If `file_names` is omitted, automatically queries `core.files` in PostgreSQL for the latest 50 resumes owned by `user_id`.
  4. Creates a new batch record in `core.screening_batches` in PostgreSQL.
  5. Executes `process_resumes_to_excel()`:
     - Extracts candidate profile.
     - Performs LLM evaluation against JD requirements.
     - Generates `.xlsx` report saved to `screening_reports/`.
  6. Returns `batch_id`, candidate summary list (`confidence_score`, `matched_skills`, `experience_comparison`, `stability`), and a direct `download_url`.

---

### Tool 3: `get_screening_report`
Retrieves past screening batch results or candidate assessment cards.

* **Schema:**
  ```json
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
  ```
* **Internal Workflow:**
  - **With `batch_id`:** Verifies access permissions (`user_id` ownership unless user is `admin`). Queries `core.bulk_screening_results` and returns individual candidate assessment cards.
  - **Without `batch_id`:** Queries `core.screening_batches` and lists recent batches with batch IDs, role titles, client names, and timestamps.

---

## 4. Protocol & Transport Layer

The server supports three distinct access modes:

### a. SSE Transport
- `GET /mcp/sse`: Establishes a persistent Server-Sent Events stream. The server generates a unique `sessionId` and sends an initial `endpoint` event informing the client where to send requests (e.g. `data: /mcp/messages?sessionId=<uuid>`). Keeps connection alive with heartbeat pings every 15 seconds.
- `POST /mcp/messages?sessionId=<uuid>`: Client posts JSON-RPC payloads to this endpoint. The server processes the command and queues the JSON-RPC response back to the client's SSE stream.

### b. Streamable HTTP JSON-RPC
- `POST /mcp` and `POST /mcp/rpc`: Direct HTTP endpoints adhering to the **JSON-RPC 2.0** specification.
- Supported methods:
  - `initialize`: Returns protocol version (`2024-11-05`), capabilities, and server info (`recai-connector 1.0.0`).
  - `notifications/initialized`: Notification sent by client confirming readiness.
  - `ping`: Health check returning `{}`.
  - `tools/list`: Returns full tool definitions and JSON schemas.
  - `tools/call`: Executes a tool with `name` and `arguments`.

### c. Direct Developer REST Endpoints
For debugging without MCP clients:
- `GET /mcp/tools`: Returns the list of registered tools.
- `POST /mcp/tools/{tool_name}`: Directly invokes a tool with JSON arguments:
  ```bash
  curl -X POST "http://localhost:8000/mcp/tools/search_resumes" \
    -H "Authorization: Bearer <your-token>" \
    -H "Content-Type: application/json" \
    -d '{"arguments": {"query": "AWS and Kubernetes engineer", "top_k": 3}}'
  ```

### d. Claude Connector Manifest
- `GET /.well-known/mcp.json` and `GET /mcp/manifest.json`:
  Provides the official Claude Connector Manifest so Claude.ai or marketplaces can automatically discover server auth and transport endpoints.

---

## 5. Authentication & Security

### OAuth 2.1 with PKCE
The MCP server implements standard OAuth 2.1 with **Proof Key for Code Exchange (PKCE)** using SHA-256 (`S256`):
- `GET /.well-known/oauth-authorization-server`: Authorization Server Metadata (RFC 8414).
- `GET /.well-known/oauth-protected-resource`: Protected Resource Metadata (RFC 9728).
- `GET /oauth/authorize`: Serves a secure, glassmorphic login screen for Claude users.
- `POST /oauth/login`: Authenticates recruiter credentials against the database and returns an authorization code.
- `POST /oauth/token`: Exchanges the code (with `code_verifier`) for an access token and refresh token.

### Prompt Injection Guard
Located in [`mcp_server/security.py`](file:///d:/Akshay/Work%20and%20Document/Training/LLM%20AND%20AI/citation/citation_generator/mcp_server/security.py):
- Strips null bytes and non-printable control characters.
- Detects and rejects malicious prompts containing phrases like:
  - `ignore previous instructions`
  - `you are now in developer mode / DAN`
  - `reveal system prompt / secret key`
  - System prompt tags (`<system>`, `[system:]`)
- For Job Descriptions, sanitizes and neutralizes injection attempts without dropping recruiter text.

### Sliding-Window Rate Limiting
- Enforces an in-memory sliding window of **60 requests per minute** per client/user.
- Returns standard HTTP 429 with `Retry-After` header when limits are reached.

### Multi-Tenant Data Isolation
Every tool call verifies the Bearer token and extracts `user_id`. Queries to Pinecone and PostgreSQL are explicitly scoped to the authenticated user's ID, preventing users from seeing other recruiters' candidates or batches.

---

## 6. How to Start & Verify the MCP Server

### Prerequisites & Environment Variables
Ensure the following variables are present in your `.env` file:
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/recai
secret_key=your-jwt-secret-key

# Vector & AI Services
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_INDEX=your-index-name
COHERE_API_KEY=your-cohere-api-key
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# MCP OAuth Configuration
MCP_OAUTH_CLIENT_ID=recai-mcp-connector
MCP_ALLOWED_REDIRECT_URIS=https://claude.ai/api/mcp/auth_callback,http://localhost:3000/callback
```

### Starting the Server
Run the FastAPI application using Uvicorn:

**On Windows (PowerShell):**
```powershell
# Using the workspace virtual environment
.\venv\Scripts\uvicorn.exe app:app --host 0.0.0.0 --port 8000 --reload
```

**On Linux / macOS:**
```bash
source venv/bin/activate
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### Verifying the Server Endpoints
Once running, verify endpoints in another terminal:

```bash
# 1. Health check
curl http://localhost:8000/

# 2. Check MCP Manifest
curl http://localhost:8000/.well-known/mcp.json

# 3. Check Tools List
curl http://localhost:8000/mcp/tools

# 4. Check OAuth Discovery
curl http://localhost:8000/.well-known/oauth-authorization-server
```

### Running the Automated Test Suite
To run the automated test suite testing OAuth, JSON-RPC, prompt injection guards, and tools:

```powershell
.\venv\Scripts\python.exe test_mcp_connector.py
```

---

## 7. How to Connect AI Clients

### Claude Desktop Configuration
To connect Claude Desktop to your local RecAI MCP server, edit your `claude_desktop_config.json`:
- **Windows Path:** `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS Path:** `~/Library/Application Support/Claude/claude_desktop_config.json`

Add the server using the SSE transport or an mcp-proxy:

```json
{
  "mcpServers": {
    "recai": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://localhost:8000/mcp/sse"
      ]
    }
  }
}
```

Restart Claude Desktop. You will see a hammer icon 🔨 indicating that `search_resumes`, `start_screening`, and `get_screening_report` are available.

---

### Official MCP Inspector Testing
Anthropic provides an interactive developer tool called the **MCP Inspector**:

```bash
npx @modelcontextprotocol/inspector http://localhost:8000/mcp/sse
```

1. Open the inspector URL shown in the terminal (usually `http://localhost:5173`).
2. The Inspector connects via SSE.
3. You can click **List Tools**, view tool schemas, and invoke `search_resumes` or `get_screening_report` interactively.

---

### Claude.ai Web Connector Integration
When deployed with a public domain (e.g. `https://recai.estuate.com`):
1. In Claude.ai workspace settings, navigate to **Integrations / Custom Connectors**.
2. Enter your server base URL: `https://recai.estuate.com`.
3. Claude fetches `https://recai.estuate.com/.well-known/mcp.json`.
4. Claude initiates the OAuth 2.1 flow by opening the login page (`/oauth/authorize`).
5. After recruiter login, Claude securely retains the Bearer token and automatically calls tools during chat.

---

## 8. End-User Workflows & Example Prompts

Once connected, recruiters interact with Claude naturally without needing to remember API endpoints or syntax:

### Workflow 1: Searching Candidates by Skill or Role
* **Recruiter Prompt:**
  > "Find candidates in my uploaded resume pool who have experience with Python, FastAPI, and PostgreSQL."
* **What Happens:**
  - Claude calls `search_resumes(query="Python, FastAPI, PostgreSQL", top_k=5)`.
  - RecAI runs vector retrieval in Pinecone and Cohere reranking.
  - Claude presents the top candidates with their match scores, relevant career snippets, and file names.

---

### Workflow 2: Screening Resumes Against a Job Description
* **Recruiter Prompt:**
  > "Here is our new Job Description for a Senior Cloud Architect:
  > [Pasted Job Description text]
  > Please screen all my uploaded candidates against this role."
* **What Happens:**
  - Claude calls `start_screening(job_description="...", position="Senior Cloud Architect")`.
  - RecAI creates a batch, executes LLM screening across the candidate resumes, and compiles an Excel sheet.
  - Claude displays a structured summary:
    - Candidate match scores
    - Matched skills & missing skills
    - Stability assessment
    - Download link for the full Excel report

---

### Workflow 3: Reviewing Past Reports
* **Recruiter Prompt:**
  > "Show me the results and candidate cards from my latest screening batch."
* **What Happens:**
  - Claude calls `get_screening_report()`.
  - If a batch ID is known or selected, Claude calls `get_screening_report(batch_id="<uuid>")`.
  - Claude summarizes each candidate's evaluation cards and recommendations (Shortlist / Review / Reject).

---

## 9. Testing MCP APIs via Swagger UI, cURL, & Backend

FastAPI automatically generates interactive OpenAPI documentation. You can test every MCP endpoint directly in your browser via Swagger UI or using backend tools like cURL and Python.

### 9.1 Interactive Testing in Swagger UI (`/docs`)

1. Start your backend server:
   ```powershell
   .\venv\Scripts\uvicorn.exe app:app --host 0.0.0.0 --port 8000 --reload
   ```
2. Open your browser and navigate to:
   ```
   http://localhost:8000/docs
   ```
3. Locate the two MCP-related tag sections in Swagger UI:
   - **`mcp`**: Contains the protocol endpoints (`/mcp`, `/mcp/rpc`, `/mcp/sse`, `/mcp/messages`, `/mcp/tools`, `/mcp/tools/{tool_name}`, `/.well-known/mcp.json`).
   - **`mcp_oauth` & `oauth_well_known`**: Contains OAuth 2.1 discovery and token exchange endpoints.

---

### 9.2 Authentication Methods for Backend Testing

MCP tool endpoints require authentication to enforce tenant data isolation. You have three flexible options when testing via Swagger UI or backend scripts:

#### Option A: Quick Developer Key (Recommended for Local Dev)
You can define an instant developer key in your `.env` file without going through full user login:
```env
MCP_DEV_API_KEY=dev-secret-key-12345
```
When this key is passed in the headers (`Authorization: Bearer dev-secret-key-12345` or `X-API-Key: dev-secret-key-12345`), the server grants access using a built-in admin developer context.

#### Option B: Standard JWT Token (`/auth/login`)
1. In Swagger UI, expand `POST /auth/login`.
2. Submit your test user credentials:
   ```json
   {
     "email": "recruiter@example.com",
     "password": "yourpassword"
   }
   ```
3. Copy the returned `auth_token` or use browser cookie authentication.
4. Pass the token as a header: `Authorization: Bearer <auth_token>`.

#### Option C: OAuth 2.1 Token Exchange
Use the `/oauth/token` endpoint or follow the browser flow at `http://localhost:8000/oauth/authorize`.

---

### 9.3 Testing Developer REST Endpoints (`/mcp/tools/{tool_name}`)

FastAPI exposes `POST /mcp/tools/{tool_name}` for testing individual tools without needing an MCP client.

#### 1. Test `search_resumes`
* **Swagger UI:** Expand `POST /mcp/tools/{tool_name}`, click **Try it out**.
* **Path parameter `tool_name`:** `search_resumes`
* **Request Body:**
  ```json
  {
    "arguments": {
      "query": "FastAPI and PostgreSQL backend developer",
      "top_k": 3
    }
  }
  ```
* **cURL Command:**
  ```bash
  curl -X POST "http://localhost:8000/mcp/tools/search_resumes" \
    -H "Content-Type: application/json" 
    -H "Authorization: Bearer dev-secret-key-12345" \
    -d '{
      "arguments": {
        "query": "FastAPI and PostgreSQL backend developer",
        "top_k": 3
      }
    }'
  ```
* **Expected Response (`200 OK`):**
  ```json
  {
    "success": true,
    "count": 3,
    "query": "FastAPI and PostgreSQL backend developer",
    "matches": [
      {
        "file_name": "john_doe_resume.pdf",
        "candidate_name": "John Doe",
        "relevance_score": 0.8942,
        "pinecone_score": 0.8123,
        "text_snippet": "Senior Backend Developer with 6 years experience in Python, FastAPI microservices, and PostgreSQL query tuning..."
      }
    ]
  }
  ```

---

#### 2. Test `start_screening`
* **Swagger UI:** Expand `POST /mcp/tools/{tool_name}`, click **Try it out**.
* **Path parameter `tool_name`:** `start_screening`
* **Request Body:**
  ```json
  {
    "arguments": {
      "job_description": "We are seeking a Senior Python Engineer with 5+ years of experience in FastAPI, Docker, and PostgreSQL. Must have hands-on experience designing REST APIs and working in Agile teams.",
      "position": "Senior Python Engineer",
      "client_name": "Estuate Inc",
      "experience": "5+ years"
    }
  }
  ```
* **cURL Command:**
  ```bash
  curl -X POST "http://localhost:8000/mcp/tools/start_screening" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer dev-secret-key-12345" \
    -d '{
      "arguments": {
        "job_description": "We are seeking a Senior Python Engineer with 5+ years of experience in FastAPI, Docker, and PostgreSQL.",
        "position": "Senior Python Engineer",
        "client_name": "Estuate Inc",
        "experience": "5+ years"
      }
    }'
  ```
* **Expected Response (`200 OK`):**
  ```json
  {
    "success": true,
    "batch_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "report_name": "Claude_Screening_20261013_120000",
    "total_screened": 2,
    "download_url": "/folder/download_report/Claude_Screening_20261013_120000.xlsx",
    "candidates": [
      {
        "candidate_name": "Alice Smith",
        "original_file": "alice_smith.pdf",
        "confidence_score": 88,
        "matched_skills": ["Python", "FastAPI", "Docker", "PostgreSQL"],
        "experience_comparison": "Candidate has 6 years (exceeds 5 years required)",
        "stability": "High (average 3 years per company)"
      }
    ]
  }
  ```

---

#### 3. Test `get_screening_report`
* **Swagger UI:** Expand `POST /mcp/tools/{tool_name}`, click **Try it out**.
* **Path parameter `tool_name`:** `get_screening_report`
* **Request Body (List Recent Batches):**
  ```json
  {
    "arguments": {
      "limit": 5
    }
  }
  ```
* **Request Body (Specific Batch ID):**
  ```json
  {
    "arguments": {
      "batch_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "limit": 10
    }
  }
  ```
* **cURL Command:**
  ```bash
  curl -X POST "http://localhost:8000/mcp/tools/get_screening_report" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer dev-secret-key-12345" \
    -d '{
      "arguments": {
        "limit": 5
      }
    }'
  ```

---

### 9.4 Testing JSON-RPC 2.0 Directly (`POST /mcp`)

AI clients like Claude Desktop connect via JSON-RPC 2.0. You can test the exact JSON-RPC lifecycle in Swagger UI or with cURL by sending requests to `POST /mcp` (or `POST /mcp/rpc`).

#### 1. `initialize` Handshake
```bash
curl -X POST "http://localhost:8000/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": { "name": "backend-tester", "version": "1.0.0" }
    }
  }'
```
* **Response (`200 OK`):**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": { "listChanged": false }
    },
    "serverInfo": {
      "name": "recai-connector",
      "version": "1.0.0"
    }
  }
}
```

---

#### 2. `tools/list`
```bash
curl -X POST "http://localhost:8000/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
  }'
```
* **Response:** Returns JSON schemas for `search_resumes`, `start_screening`, and `get_screening_report`.

---

#### 3. `tools/call`
```bash
curl -X POST "http://localhost:8000/mcp" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-secret-key-12345" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "search_resumes",
      "arguments": {
        "query": "React frontend developer",
        "top_k": 2
      }
    }
  }'
```
* **Response (`200 OK`):**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\n  \"success\": true,\n  \"count\": 2,\n  ...\n}"
      }
    ],
    "isError": false
  }
}
```

---

### 9.5 Testing SSE Transport (`/mcp/sse` & `/mcp/messages`)

If testing SSE streaming via terminal:

1. Open the SSE listener in one terminal:
   ```bash
   curl -N "http://localhost:8000/mcp/sse"
   ```
   *You will see:*
   ```
   event: endpoint
   data: /mcp/messages?sessionId=b4a9...-....-....
   ```
2. Copy the `sessionId` from the output. In a second terminal, send a JSON-RPC message:
   ```bash
   curl -X POST "http://localhost:8000/mcp/messages?sessionId=<YOUR_SESSION_ID>" \
     -H "Content-Type: application/json" \
     -d '{
       "jsonrpc": "2.0",
       "id": 1,
       "method": "ping"
     }'
   ```
3. Watch the first terminal: the SSE stream will output the JSON-RPC response with `event: message`.

---

### 9.6 Programmatic Testing with Python (`httpx` / `requests`)

You can run automated scripts against the MCP endpoints using Python:

```python
import requests

BASE_URL = "http://localhost:8000"
DEV_KEY = "dev-secret-key-12345"  # Matches MCP_DEV_API_KEY in .env

headers = {
    "Authorization": f"Bearer {DEV_KEY}",
    "Content-Type": "application/json"
}

# 1. Test Tools Schema List
res = requests.get(f"{BASE_URL}/mcp/tools")
print("Available tools:", [t["name"] for t in res.json()["tools"]])

# 2. Test Resume Search Tool
search_payload = {
    "arguments": {
        "query": "DevOps Engineer with Kubernetes and Terraform",
        "top_k": 3
    }
}
search_res = requests.post(
    f"{BASE_URL}/mcp/tools/search_resumes",
    headers=headers,
    json=search_payload
)
print("Search Status:", search_res.status_code)
print("Search Result:", search_res.json())

# 3. Test JSON-RPC Protocol Endpoint
rpc_payload = {
    "jsonrpc": "2.0",
    "id": 101,
    "method": "tools/call",
    "params": {
        "name": "get_screening_report",
        "arguments": {"limit": 3}
    }
}
rpc_res = requests.post(f"{BASE_URL}/mcp", headers=headers, json=rpc_payload)
print("JSON-RPC Result:", rpc_res.json())
```

