# Multilingual Video Localization Platform — Architecture

## 1. System Overview

A web platform where Admin uploads one Vietnamese-narrated video with SRT subtitles and optional separate voice/music tracks. The system pre-generates independent subtitle and audio tracks for Vietnamese, English, Russian, and Chinese Simplified. End users access via QR code on mobile and watch with instant playback — no on-demand AI processing.

### Core Principle

```
1 ORIGINAL VIDEO + 4 SUBTITLE TRACKS + 4 AUDIO TRACKS
```

The video stream is never re-encoded. Subtitles are never burned in. Language switching happens client-side.

## 2. Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, TypeScript, Vite, Tailwind v4, React Router |
| Backend | Python 3.11+, FastAPI, Pydantic v2 |
| Database | **Supabase (PostgreSQL)** via Python client |
| Storage | **Supabase Storage** (private bucket `video-assets`) |
| Job Queue | ARQ (Redis); asyncio in-process fallback for dev |
| Translation | Pluggable `TranslationProvider`; MVP: OpenAI |
| TTS | Pluggable `TTSEngine`; MVP: Edge TTS |
| Audio | FFmpeg/ffprobe |
| Auth | JWT + bcrypt (admin only) |

## 3. Directory Structure

```
videodangonngu/
├── supabase/migrations/     # SQL schema (source of truth)
├── backend/app/
│   ├── integrations/supabase/  # client, database repo, storage helpers
│   ├── api/routes/             # admin + public
│   ├── models/                 # domain dataclasses + enums
│   ├── services/               # translation, tts, audio, storage
│   └── workers/                # pipeline + ARQ worker
├── frontend/src/
├── SETUP_DEPLOY.md             # deploy checklist
└── docker-compose.yml          # Redis only (dev)
```

## 4. Database Schema

Managed via `supabase/migrations/001_initial_schema.sql`.

### users
- id (UUID PK), email, password_hash, role, created_at

### videos
- id, title, description, original_video_key, thumbnail_key, duration_ms
- status: draft | processing | ready_for_review | published | failed | requires_review
- result_meta (JSONB), created_by (FK), created_at, updated_at

### video_languages
- id, video_id (FK), language_code — **UNIQUE(video_id, language_code)**
- subtitle_key, status, timestamps

### subtitle_segments
- id, video_language_id (FK), sequence — **UNIQUE(video_language_id, sequence)**
- start_ms, end_ms, source_text, translated_text, alignment_meta (JSONB)

### audio_tracks
- id, video_language_id (FK), audio_key, duration_ms, mix_config (JSONB)

### processing_jobs
- id, video_id (FK), pipeline_run_id, stage, language_code, status, progress
- error_message, retry_count, started_at, completed_at, timestamps
- **UNIQUE(video_id, stage, language_code, pipeline_run_id)**

## 5. Processing Pipeline

Stages: `PARSE → TRANSLATE → VALIDATE → TTS → ALIGN → MIX → SUBTITLE_EXPORT → FINALIZE`

- Each generate/regenerate run has a unique `pipeline_run_id`
- Temporary files in `backend/workspace/`; finals uploaded to Supabase Storage
- Vietnamese audio uses uploaded voice (no TTS regeneration)

## 6. Storage Layout (Supabase bucket: video-assets)

```
video/{video_id}/
  original.mp4
  thumbnail.jpg
  source.srt          # upload input
  voice_vi.mp3        # upload input
  music.mp3           # optional
  subtitle/vi.vtt en.vtt ru.vtt zh.vtt
  audio/vi.mp3 en.mp3 ru.mp3 zh.mp3
```

## 7. API Reference

### Admin (JWT)
- POST `/api/admin/auth/login`
- GET/POST `/api/admin/videos`
- POST `/api/admin/videos/{id}/generate`
- POST `/api/admin/videos/{id}/regenerate/{lang}`
- GET `/api/admin/videos/{id}/jobs`
- POST publish/unpublish, DELETE, preview, QR

### Public
- GET `/api/videos` — published only
- GET `/api/videos/{id}` — published only
- GET `/api/videos/{id}/subtitles/{lang}.vtt` — redirect to signed URL
- GET `/api/videos/{id}/audio/{lang}.mp3` — redirect to signed URL

Media access requires `video.status == published`. Bucket is private; backend issues signed URLs.

## 8. Security

- `SUPABASE_SERVICE_ROLE_KEY` — backend only, never in frontend
- Admin endpoints require JWT
- Public API: read-only GET for published videos only
- Signed URLs with expiration for all media

## 9. Configuration

Required environment variables:
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_STORAGE_BUCKET`
- `JWT_SECRET`, `OPENAI_API_KEY`, `PUBLIC_BASE_URL`, `CORS_ORIGINS`

See `.env.example` and `SETUP_DEPLOY.md`.

## 10. Success Criteria

Admin uploads MP4 + SRT + voice → Generate → Publish → User scans QR → plays with English subtitle + audio → can switch audio to Vietnamese independently.
