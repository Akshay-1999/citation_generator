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
