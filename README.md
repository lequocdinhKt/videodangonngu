# Multilingual Video Localization Platform

A web platform for multilingual video localization with independent subtitle and audio tracks.

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- FFmpeg
- [Supabase](https://supabase.com) project (database + storage)

See **[SETUP_DEPLOY.md](SETUP_DEPLOY.md)** for full Supabase setup, deploy Railway/VPS, and production checklist.

### Setup

```bash
# 1. Configure Supabase (see SETUP_DEPLOY.md section 2)
#    - Run supabase/migrations/001_initial_schema.sql
#    - Create private bucket: video-assets

# 2. Backend
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy ..\.env.example .env     # Add SUPABASE_* keys
uvicorn app.main:app --reload --port 8000

# 3. Frontend (new terminal)
cd frontend
npm install
npm run dev

# 4. Optional: Redis for ARQ worker
docker compose up -d redis
```

### Default Admin
- Email: `admin@example.com` (or `ADMIN_EMAIL` in `.env`)
- Password: `admin123` (change in production!)

### URLs
- Public: http://localhost:5173
- Admin: http://localhost:5173/admin/login
- API: http://localhost:8000/api/health

### Tests

```bash
cd backend
pytest tests/ -m "not integration" -v
```

## Architecture

See [PROJECT_ARCHITECTURE.md](PROJECT_ARCHITECTURE.md) for system design.  
See [SETUP_DEPLOY.md](SETUP_DEPLOY.md) for deploy guide.

## Workflow

1. Admin uploads MP4 + Vietnamese SRT + voice MP3
2. Click **Generate** — system translates, generates TTS, aligns audio
3. Review in admin dashboard
4. **Publish** when ready
5. Users scan QR → select language → watch with independent subtitle/audio
