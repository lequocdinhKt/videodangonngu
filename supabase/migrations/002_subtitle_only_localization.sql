-- Subtitle-only multilingual metadata. Safe to apply after 001_initial_schema.sql.

ALTER TYPE language_status ADD VALUE IF NOT EXISTS 'ready_for_review';

CREATE TABLE IF NOT EXISTS video_translations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL REFERENCES videos (id) ON DELETE CASCADE,
    language_code VARCHAR(10) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_video_translations_video_language UNIQUE (video_id, language_code)
);

CREATE INDEX IF NOT EXISTS ix_video_translations_video_id
    ON video_translations (video_id);

-- Backfill Vietnamese metadata for projects created with the original schema.
INSERT INTO video_translations (video_id, language_code, title, description)
SELECT id, 'vi-VN', title, description
FROM videos
ON CONFLICT (video_id, language_code) DO NOTHING;
