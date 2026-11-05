-- Multilingual Video Localization Platform — initial schema
-- Run in Supabase SQL Editor or via Supabase CLI

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TYPE video_status AS ENUM (
    'draft',
    'processing',
    'ready_for_review',
    'published',
    'failed',
    'requires_review'
);

CREATE TYPE language_status AS ENUM (
    'pending',
    'processing',
    'completed',
    'failed'
);

CREATE TYPE job_status AS ENUM (
    'pending',
    'running',
    'completed',
    'failed'
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'admin',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_users_email ON users (email);

CREATE TABLE videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    original_video_key VARCHAR(1000),
    thumbnail_key VARCHAR(1000),
    voice_key VARCHAR(1000),
    music_key VARCHAR(1000),
    srt_key VARCHAR(1000),
    duration_ms INTEGER,
    status video_status NOT NULL DEFAULT 'draft',
    result_meta JSONB,
    created_by UUID REFERENCES users (id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_videos_status ON videos (status);
CREATE INDEX ix_videos_created_by ON videos (created_by);

CREATE TABLE video_languages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL REFERENCES videos (id) ON DELETE CASCADE,
    language_code VARCHAR(10) NOT NULL,
    subtitle_key VARCHAR(1000),
    status language_status NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_video_languages_video_id_language_code UNIQUE (video_id, language_code)
);

CREATE INDEX ix_video_languages_video_id ON video_languages (video_id);
CREATE INDEX ix_video_languages_language_code ON video_languages (language_code);

CREATE TABLE subtitle_segments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_language_id UUID NOT NULL REFERENCES video_languages (id) ON DELETE CASCADE,
    sequence INTEGER NOT NULL,
    start_ms INTEGER NOT NULL,
    end_ms INTEGER NOT NULL,
    source_text TEXT NOT NULL DEFAULT '',
    translated_text TEXT NOT NULL DEFAULT '',
    alignment_meta JSONB,
    CONSTRAINT uq_subtitle_segments_video_language_id_sequence UNIQUE (video_language_id, sequence)
);

CREATE INDEX ix_subtitle_segments_video_language_id_sequence
    ON subtitle_segments (video_language_id, sequence);

CREATE TABLE audio_tracks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_language_id UUID NOT NULL UNIQUE REFERENCES video_languages (id) ON DELETE CASCADE,
    audio_key VARCHAR(1000) NOT NULL,
    duration_ms INTEGER,
    mix_config JSONB
);

CREATE TABLE processing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL REFERENCES videos (id) ON DELETE CASCADE,
    pipeline_run_id UUID NOT NULL,
    stage VARCHAR(50) NOT NULL,
    language_code VARCHAR(10),
    status job_status NOT NULL DEFAULT 'pending',
    progress INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_processing_jobs_run_stage_lang UNIQUE (video_id, stage, language_code, pipeline_run_id)
);

CREATE INDEX ix_processing_jobs_video_id ON processing_jobs (video_id);
CREATE INDEX ix_processing_jobs_video_id_status ON processing_jobs (video_id, status);
