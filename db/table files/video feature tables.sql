-- =================================================================================================
-- VIDEO INTERVIEW & ANALYTICS SCHEMA
-- Schema: interview
-- =================================================================================================

-- 1. Ensure required extensions and schema exist
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA IF NOT EXISTS interview;

-- =================================================================================================
-- 1. CANDIDATES TABLE
-- =================================================================================================
CREATE TABLE IF NOT EXISTS interview.candidates (
    candidate_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recruiter_id UUID NOT NULL,                                       -- FK to core.users (user_id)
    candidate_name VARCHAR(255) NOT NULL,
    candidate_email VARCHAR(320) NOT NULL,
    candidate_phone_number VARCHAR(50),
    job_position VARCHAR(255),
    client VARCHAR(255),
    years_of_experience NUMERIC(4, 1),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ DEFAULT NULL,
    is_deleted BOOLEAN DEFAULT false,

    CONSTRAINT fk_candidate_recruiter FOREIGN KEY (recruiter_id)
        REFERENCES core.users (user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- =================================================================================================
-- 2. INTERVIEW SESSIONS TABLE
-- =================================================================================================
CREATE TABLE IF NOT EXISTS interview.interview_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID NOT NULL,                                       -- FK to interview.candidates
    job_id UUID,                                                      -- FK to core.screening_batches
    recruiter_id UUID NOT NULL,                                       -- FK to core.users (user_id)
    status VARCHAR(50) NOT NULL DEFAULT 'CREATED',
    interview_token VARCHAR(255) NOT NULL UNIQUE,                    -- Secure token for candidate portal
    interview_url TEXT,
    invite_sent_on TIMESTAMPTZ DEFAULT NULL,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '2 days'),
    started_at TIMESTAMPTZ DEFAULT NULL,
    completed_at TIMESTAMPTZ DEFAULT NULL,
    overall_score NUMERIC(5, 2) DEFAULT NULL,
    recommendation VARCHAR(100) DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_interview_status CHECK (
        status IN ('CREATED', 'EMAIL_SENT', 'STARTED', 'IN_PROGRESS', 'SUBMITTED', 'PROCESSING', 'COMPLETED', 'FAILED', 'EXPIRED')
    ),

    CONSTRAINT fk_session_candidate FOREIGN KEY (candidate_id)
        REFERENCES interview.candidates (candidate_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT fk_session_job FOREIGN KEY (job_id)
        REFERENCES core.screening_batches (id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,

    CONSTRAINT fk_session_recruiter FOREIGN KEY (recruiter_id)
        REFERENCES core.users (user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- =================================================================================================
-- 3. INTERVIEW TURNS TABLE (Per-Question Video/Audio & Turn Analytics)
-- =================================================================================================
CREATE TABLE IF NOT EXISTS interview.interview_turns (
    turn_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,                                         -- FK to interview.interview_sessions
    turn_number INTEGER NOT NULL,                                     -- E.g. 1, 2, 3, 4, 5
    question_id VARCHAR(100),
    question_text TEXT NOT NULL,
    question_generation_source VARCHAR(100) DEFAULT 'AI_GENERATED',
    question_type VARCHAR(100) DEFAULT 'TECHNICAL',                  -- E.g. BEHAVIORAL, TECHNICAL, SCENARIO
    video_path TEXT,                                                  -- Path to saved candidate video
    audio_path TEXT,                                                  -- Path to extracted audio for Whisper
    response_duration NUMERIC(6, 2),                                 -- Duration in seconds
    transcript TEXT,                                                  -- Whisper generated text
    language VARCHAR(50) DEFAULT 'en',
    confidence NUMERIC(5, 2),
    transcript_processing_time NUMERIC(6, 2),                        -- In seconds
    communication_score NUMERIC(5, 2),
    technical_score NUMERIC(5, 2),
    answer_summary TEXT,
    answer_feedback TEXT,
    processing_status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    submitted_at TIMESTAMPTZ DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_turn_processing_status CHECK (
        processing_status IN ('PENDING', 'TRANSCRIBING', 'ANALYZING', 'COMPLETED', 'FAILED')
    ),

    CONSTRAINT uq_session_turn UNIQUE (session_id, turn_number),

    CONSTRAINT fk_turn_session FOREIGN KEY (session_id)
        REFERENCES interview.interview_sessions (session_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- =================================================================================================
-- 4. INTERVIEW DOCUMENTS TABLE (Identity Verification / Govt ID & Selfie)
-- =================================================================================================
CREATE TABLE IF NOT EXISTS interview.interview_documents (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,                                         -- FK to interview.interview_sessions
    candidate_image TEXT,                                             -- Selfie capture path
    document_type VARCHAR(50) NOT NULL,
    file_path TEXT NOT NULL,
    verification_status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    confidence_score NUMERIC(5, 2) DEFAULT NULL,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_doc_type CHECK (
        document_type IN ('AADHAR', 'PASSPORT', 'PAN', 'DRIVING_LICENSE', 'VOTER_ID', 'OTHER')
    ),

    CONSTRAINT chk_doc_verification_status CHECK (
        verification_status IN ('PENDING', 'VERIFIED', 'FLAGGED', 'FAILED')
    ),

    CONSTRAINT fk_document_session FOREIGN KEY (session_id)
        REFERENCES interview.interview_sessions (session_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- =================================================================================================
-- 5. INTERVIEW REPORTS TABLE (Comprehensive AI Assessment)
-- =================================================================================================
CREATE TABLE IF NOT EXISTS interview.interview_reports (
    report_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL UNIQUE,                                  -- FK to interview.interview_sessions (1:1)
    communication_score NUMERIC(5, 2),
    technical_score NUMERIC(5, 2),
    resume_consistency_score NUMERIC(5, 2),
    overall_score NUMERIC(5, 2),
    recommendation VARCHAR(100),                                      -- E.g. Strong Hire, Hire, Hold, Reject
    summary TEXT,
    strengths JSONB,                                                  -- Key candidate strengths
    weaknesses JSONB,                                                 -- Identified gaps / weaknesses
    improvement_areas JSONB,
    confidence_indicators JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_report_session FOREIGN KEY (session_id)
        REFERENCES interview.interview_sessions (session_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- =================================================================================================
-- INDEXES FOR QUERY OPTIMIZATION
-- =================================================================================================
CREATE INDEX IF NOT EXISTS idx_candidates_recruiter_id ON interview.candidates(recruiter_id);
CREATE INDEX IF NOT EXISTS idx_candidates_email ON interview.candidates(candidate_email);

CREATE INDEX IF NOT EXISTS idx_sessions_candidate_id ON interview.interview_sessions(candidate_id);
CREATE INDEX IF NOT EXISTS idx_sessions_recruiter_id ON interview.interview_sessions(recruiter_id);
CREATE INDEX IF NOT EXISTS idx_sessions_job_id ON interview.interview_sessions(job_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON interview.interview_sessions(interview_token);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON interview.interview_sessions(status);

CREATE INDEX IF NOT EXISTS idx_turns_session_id ON interview.interview_turns(session_id);
CREATE INDEX IF NOT EXISTS idx_turns_status ON interview.interview_turns(processing_status);

CREATE INDEX IF NOT EXISTS idx_documents_session_id ON interview.interview_documents(session_id);
CREATE INDEX IF NOT EXISTS idx_reports_session_id ON interview.interview_reports(session_id);
