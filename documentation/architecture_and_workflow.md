# Citation Generator Architecture & Workflows

This document outlines the architecture and core workflows of the Citation Generator application.

## 1. High-Level Architecture

The application is built using a modern Python tech stack, utilizing FastAPI for the backend, LangChain/OpenAI for LLM orchestration, PostgreSQL for relational data, and Pinecone for vector search.

```mermaid
graph LR
    %% Style definitions to mimic the dotted zones
    classDef topZone fill:transparent,stroke:#0277bd,stroke-width:2px,stroke-dasharray: 5 5;
    classDef leftZone fill:transparent,stroke:#2e7d32,stroke-width:2px,stroke-dasharray: 5 5;
    classDef centerZone fill:transparent,stroke:#c62828,stroke-width:2px,stroke-dasharray: 5 5;
    classDef nodeStyle fill:#f9f9f9,stroke:#333,stroke-width:1px,rx:5px,ry:5px;

    class User,API,Feedback,RawResumes,JDs,Templates,DocProc,Agents,Embed,LocalFS,OpenAI,Pinecone,Postgres nodeStyle;

    %% User Interaction / Workflow Layer (Top)
    subgraph TopZone [User Interaction & Workflow]
        direction LR
        User((User)) -->|Upload JD / Resumes| API(FastAPI App Plug-in)
        User -->|Chat Queries| API
        API -->|Results / Reports| Feedback((Feedback / User))
    end
    class TopZone topZone;

    %% Data Sources Layer (Left)
    subgraph LeftZone [Input Data Sources]
        direction TB
        RawResumes[Raw Resumes PDF/DOCX]
        JDs[Job Descriptions]
        Templates[Company Docx Templates]
    end
    class LeftZone leftZone;

    %% Core Application & Cloud Infrastructure (Center/Right)
    subgraph CenterZone [Core AI & Infrastructure]
        direction LR
        
        subgraph CoreLogic [Core Processing]
            direction TB
            Agents[LangChain Agents]
            DocProc[Document Processor]
            Embed[Embedding Engine]
        end
        
        subgraph CloudServices [Storage & Hosted Services]
            direction TB
            LocalFS[(Local File Storage)]
            OpenAI[OpenAI GPT Models]
            Pinecone[(Pinecone Vector DB)]
            Postgres[(PostgreSQL History)]
        end
        
        API --> CoreLogic
        DocProc --> LocalFS
        Agents --> OpenAI
        Agents --> Pinecone
        Embed --> Pinecone
        API --> Postgres
    end
    class CenterZone centerZone;
    
    %% Connecting the zones
    LeftZone --> CoreLogic
```

### Key Components

*   **FastAPI Framework**: Serves as the main entry point (`app.py`), routing requests and handling middleware (authentication via cookies, CORS, request logging).
*   **LangChain Agents (`agents/`)**: 
    *   `RAGAgent`: Handles conversational chat, utilizing tools to search uploaded documents in Pinecone.
    *   `ResumeMappingAgent`: Specialized for comparing Job Descriptions against candidate resumes.
*   **Document Processing (`document_processing/`)**: Handles file loading, text extraction, chunking, and template-based document generation (e.g., converting a raw resume into a standardized company DOCX/PDF template).
*   **Embedding Engine (`embedding/`)**: Manages the generation of embeddings (likely OpenAI) and interacts with the Pinecone Vector Database.
*   **Database (`db/`)**: PostgreSQL used for relational data storage, including user accounts, file metadata, chat history, and bulk screening reports.

---

## 2. Core Workflows

### A. RAG Chat Workflow (`/chat/query`)
This workflow describes how a user asks a question and the system retrieves relevant document chunks to answer it with citations.

```mermaid
sequenceDiagram
    participant User
    participant Router as Chat Route
    participant Agent as RAGAgent
    participant LLM as OpenAI
    participant VectorDB as Pinecone
    participant DB as PostgreSQL

    User->>Router: POST /chat/query (query, file_names)
    Router->>DB: Check/Create Chat Thread
    Router->>Agent: Initialize & Run Agent
    Agent->>LLM: Send Query + System Prompt
    LLM-->>Agent: Request Tool Call (search_uploaded_documents)
    Agent->>VectorDB: Query Pinecone for relevant chunks
    VectorDB-->>Agent: Return Document Matches
    Agent->>LLM: Send Document Chunks Context
    LLM-->>Agent: Synthesize Answer with Citations
    Agent-->>Router: Return Answer & Verified Chunks
    Router->>DB: Save Messages to Chat History
    Router-->>User: Return Response & Citations
```

### B. Bulk Folder Processing & Screening Workflow (`/folder/process_folder`)
This workflow handles the upload of a Job Description and multiple resumes, screening the candidates against the JD.

```mermaid
sequenceDiagram
    participant User
    participant Router as Folder Processor
    participant LLM as OpenAI (JD Analysis)
    participant DocProc as Document Processor
    participant Embedder as Embedding Engine
    participant Agent as ResumeMappingAgent
    participant DB as PostgreSQL

    User->>Router: Upload JD & Resume Files
    Router->>DocProc: Extract Text from JD
    Router->>LLM: Analyze JD (Extract Position, Exp, Client)
    LLM-->>Router: JD Metadata
    Router->>DB: Create Screening Batch Record
    
    loop For each Resume
        Router->>DocProc: Save file locally & Hash (MD5)
        Router->>DB: Log file upload
        Router->>Embedder: Extract text & Chunk
        Embedder->>Pinecone: Store Embeddings
    end
    
    Router->>Agent: Run Bulk Screening (JD vs Resumes)
    Agent-->>Router: Screening Results
    Router->>DocProc: Generate Excel Report
    Router-->>User: Return Screening Results & Report Download URL
```

### C. Resume Format Conversion Workflow (`/conversion/api/convert`)
This workflow standardizes candidate resumes into a specific company template format.

```mermaid
sequenceDiagram
    participant User
    participant Router as File Conversion
    participant Cache as PostgreSQL (Cache Check)
    participant DocxTpl as Template Converter
    participant LLM as OpenAI (Data Extraction)

    User->>Router: POST /convert (original_file)
    Router->>Cache: Check if already converted?
    alt Cache Hit
        Cache-->>Router: Return cached file URLs
        Router-->>User: Return Cached URLs
    else Cache Miss
        Router->>DocxTpl: Run DOCX Template Conversion
        DocxTpl->>LLM: Extract structured JSON data from Resume
        LLM-->>DocxTpl: Resume JSON Data
        DocxTpl->>DocxTpl: Populate Estuate Template (DOCX)
        DocxTpl->>DocxTpl: Generate PDF from DOCX
        DocxTpl-->>Router: Conversion Result & Files
        Router->>Cache: Save converted file paths & JSON
        Router-->>User: Return Download URLs & Preview
    end
```

## Directory Structure Highlights
*   `agents/`: Contains LLM orchestration logic (`agents_main.py`, `agents_tool.py`, `agent_utils.py`).
*   `db/`: Database configuration and query endpoints.
*   `document_processing/`: Parsers, loaders, and template converters.
*   `embedding/`: Pinecone index management and text embedder.
*   `routes/`: FastAPI endpoints separated by domain (`chat.py`, `fileconverstion.py`, `folderprocesser.py`, etc.).
*   `converted_resumes/` & `uploaded_files/`: Local file storage.
