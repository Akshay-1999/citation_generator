-- Enable UUID generation (using pgcrypto)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Create schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS chathistory;

-- =========================
-- USERS TABLE
-- =========================
CREATE TABLE IF NOT EXISTS core.users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),      -- UUID PK
    username VARCHAR(255) NOT NULL,
    email VARCHAR(320) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE core.users
ADD COLUMN user_role VARCHAR(20) NOT NULL DEFAULT 'user'
    CHECK (user_role IN ('user', 'admin', 'system'));

ALTER TABLE core.users ADD COLUMN password TEXT NOT NULL DEFAULT crypt('default123', gen_salt('bf'));


-- =========================
-- FILES TABLE
-- =========================
CREATE TABLE IF NOT EXISTS core.files (
    file_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),       -- UUID PK
    user_id UUID NOT NULL,                                   -- FK to users
    filename VARCHAR(1024) NOT NULL,
    file_path TEXT NOT NULL,
    extension VARCHAR(32),
    size_mb NUMERIC(12,3) CHECK (size_mb >= 0),              -- File size in MB
    md5 CHAR(32) NOT NULL,                                   -- MD5 hash (32-char hex)
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    modified_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ DEFAULT NULL,
    is_deleted BOOLEAN DEFAULT false,

    CONSTRAINT fk_files_user FOREIGN KEY (user_id)
        REFERENCES core.users (user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- =========================
-- INDEXES
-- =========================
CREATE INDEX IF NOT EXISTS idx_files_user_id ON core.files(user_id);
CREATE INDEX IF NOT EXISTS idx_files_md5 ON core.files(md5);


-- =========================
-- CHAT HISTORY TABLES chat_threads
-- =========================
CREATE TABLE chathistory.chat_threads (
    thread_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    thread_title TEXT,
    thread_status TEXT NOT NULL DEFAULT 'not-shared',
    thread_created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    thread_updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT thread_status_check 
        CHECK (thread_status IN ('shared', 'not-shared', 'deleted')),

    CONSTRAINT fk_thread_user 
        FOREIGN KEY (user_id)
        REFERENCES core.users (user_id)
        ON DELETE CASCADE
);


-- =========================
-- messages Table
-- =========================
CREATE TABLE chathistory.messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL,
    user_id UUID NOT NULL,
    role TEXT NOT NULL,
    messages_content TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    citations JSONB,
    confidence_level NUMERIC,
    client_id TEXT,
    sequence_number INTEGER,
    file_context_name TEXT,

    CONSTRAINT fk_message_thread 
        FOREIGN KEY (thread_id)
        REFERENCES chathistory.chat_threads (thread_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_message_user 
        FOREIGN KEY (user_id)
        REFERENCES core.users (user_id)
        ON DELETE CASCADE
);

-- =========================
-- bulk_screening_results Table
-- =========================

ALTER TABLE core.bulk_screening_results
ADD COLUMN batch_id UUID;

ALTER TABLE core.bulk_screening_results
ADD COLUMN matched_skills TEXT;

ALTER TABLE core.bulk_screening_results
ADD CONSTRAINT fk_batch_id
FOREIGN KEY (batch_id)
REFERENCES core.screening_batches(id)
ON DELETE CASCADE;


-- =========================
-- screening_batches Table
-- =========================

CREATE TABLE IF NOT EXISTS core.screening_batches ( 
    id UUID PRIMARY KEY, 
    user_id UUID NOT NULL, 
    report_name TEXT NOT NULL, 
    position TEXT, 
    experience INTEGER, 
    client_name TEXT, 
    jd_text TEXT, 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
    CONSTRAINT fk_user FOREIGN KEY (user_id) 
    REFERENCES core.users(user_id) ON DELETE CASCADE 
);

alter table core.screening_batches add column client_name text;

-- =========================
-- converted_resumes Table
-- =========================
CREATE TABLE IF NOT EXISTS core.converted_resumes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    original_file VARCHAR(1024) NOT NULL,
    converted_file_path TEXT NOT NULL,
    template_name VARCHAR(255) DEFAULT 'Estuate Format',
    status VARCHAR(50) NOT NULL DEFAULT 'converted',
    rejection_reason TEXT DEFAULT NULL,
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMPTZ DEFAULT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT fk_converted_user FOREIGN KEY (user_id) 
        REFERENCES core.users (user_id) ON DELETE CASCADE,
    CONSTRAINT uq_user_original_file UNIQUE (user_id, original_file)
);

ALTER TABLE core.converted_resumes
RENAME COLUMN converted_file_path TO converted_pdf_file_path;

ALTER TABLE core.converted_resumes
ADD COLUMN converted_json_file_path text COLLATE pg_catalog."default";

ALTER TABLE core.converted_resumes
ADD COLUMN converted_docx_file_path text COLLATE pg_catalog."default";

ALTER TABLE core.converted_resumes
DROP CONSTRAINT uq_user_original_file;