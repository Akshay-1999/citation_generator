-- Enable UUID generation (using pgcrypto)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Create schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS core;

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
