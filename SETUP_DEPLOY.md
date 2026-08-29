# Deploy Setup Guide

Checklist để deploy **Multilingual Video Localization Platform** lên web.  
Các bước có dấu `[ ]` là việc **bạn phải tự làm** — agent không thể làm thay (tạo tài khoản, nhập secrets, deploy hosting).

---

## 1. Prerequisites

- [ ] Tài khoản [GitHub](https://github.com) (push code)
- [ ] Tài khoản [Supabase](https://supabase.com) (free tier đủ cho MVP)
- [ ] Tài khoản hosting backend (chọn một):
  - **Railway** — dễ, hỗ trợ Docker + Redis
  - **VPS** (DigitalOcean, Hetzner) — linh hoạt, cần SSH
- [ ] Tài khoản hosting frontend (chọn một):
  - Vercel / Netlify / Cloudflare Pages
- [ ] **FFmpeg** cài trên máy chạy worker (không cài trên Supabase)
- [ ] **OpenAI API key** (nếu generate thật, không dùng mock)
- [ ] Domain (optional lúc dev, bắt buộc khi public production)
- [ ] Python 3.11–3.12 khuyến nghị (tránh 3.14 nếu gặp lỗi package)

---

## 2. Supabase Setup (BẮT BUỘC — làm trước)

### 2.1 Tạo project

1. Đăng nhập [supabase.com](https://supabase.com) → **New project**
2. Chọn organization → đặt tên project (vd: `videodangonngu`)
3. Chọn **Region** gần user (Singapore cho VN)
4. Đặt database password → **Save password** (không mất)
5. Đợi project khởi tạo (~2 phút)

### 2.2 Lấy API keys

1. Vào **Project Settings** → **API**
2. Copy và lưu an toàn:
   - **Project URL** → `SUPABASE_URL`
   - **anon public** → `SUPABASE_ANON_KEY`
   - **service_role** → `SUPABASE_SERVICE_ROLE_KEY` ⚠️ **CHỈ backend, KHÔNG BAO GIỜ đưa vào frontend**

### 2.3 Chạy database migration

1. Vào **SQL Editor** → **New query**
2. Copy toàn bộ nội dung file [`supabase/migrations/001_initial_schema.sql`](../supabase/migrations/001_initial_schema.sql)
3. Click **Run**
4. Kiểm tra **Table Editor** — phải có: `users`, `videos`, `video_languages`, `subtitle_segments`, `audio_tracks`, `processing_jobs`

### 2.4 Tạo Storage bucket

1. Vào **Storage** → **New bucket**
2. Name: `video-assets`
3. **Public bucket: OFF** (private)
4. Create bucket

> Backend dùng service role + signed URLs — không cần public bucket.

### 2.5 Điền `.env` backend

Copy `.env.example` → `backend/.env`:

```env
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
SUPABASE_ANON_KEY=eyJ...
SUPABASE_STORAGE_BUCKET=video-assets
STORAGE_PROVIDER=supabase
SKIP_SUPABASE_VALIDATION=false

JWT_SECRET=<random-64-chars>
ADMIN_EMAIL=your@email.com
ADMIN_PASSWORD=<strong-password>
OPENAI_API_KEY=sk-...

PUBLIC_BASE_URL=https://your-domain.com
CORS_ORIGINS=https://your-domain.com
ENV=production
```

- [ ] Đã tạo Supabase project
- [ ] Đã chạy SQL migration
- [ ] Đã tạo bucket `video-assets` (private)
- [ ] Đã điền `backend/.env`

---

## 3. Local Development

```bash
# Không cần Docker PostgreSQL

cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy ..\.env.example .env       # rồi điền Supabase keys
uvicorn app.main:app --reload --port 8000

# Terminal mới — frontend
cd frontend
npm install
npm run dev
```

URLs:
- Frontend: http://localhost:5173
- API: http://localhost:8000/api/health
- Admin: http://localhost:5173/admin/login

### Chạy tests (không cần Supabase thật)

```bash
cd backend
pytest tests/ -m "not integration and not supabase_integration" -v
```

### E2E mock pipeline (cần FFmpeg)

```bash
set E2E_MOCK_TRANSLATION=1
python -m tests.run_e2e_pipeline
```

---

## 4. Deploy Option A — Railway

### 4.1 Chuẩn bị

- [ ] Push code lên GitHub
- [ ] Tài khoản [railway.app](https://railway.app)

### 4.2 Services

Tạo project Railway với 3 services:

| Service | Image/Build | Port |
|---------|-------------|------|
| `api` | Dockerfile `backend/Dockerfile`, CMD api | 8000 |
| `worker` | Same Dockerfile, CMD worker | — |
| `redis` | Railway Redis template | 6379 |

### 4.3 Environment variables (cả api + worker)

| Variable | Value |
|----------|-------|
| `SUPABASE_URL` | từ Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | từ Supabase |
| `SUPABASE_ANON_KEY` | từ Supabase |
| `SUPABASE_STORAGE_BUCKET` | `video-assets` |
| `STORAGE_PROVIDER` | `supabase` |
| `REDIS_URL` | Railway Redis URL |
| `USE_ARQ` | `true` |
| `JWT_SECRET` | random strong secret |
| `ADMIN_EMAIL` | email admin |
| `ADMIN_PASSWORD` | password mạnh |
| `OPENAI_API_KEY` | sk-... |
| `ENV` | `production` |
| `PUBLIC_BASE_URL` | https://your-frontend-domain.com |
| `CORS_ORIGINS` | https://your-frontend-domain.com |
| `FFMPEG_PATH` | `ffmpeg` |

- [ ] API service deployed
- [ ] Worker service deployed (có FFmpeg trong Docker image)
- [ ] Redis connected

### 4.4 Frontend trên Railway (optional)

Hoặc deploy frontend riêng trên Vercel (khuyến nghị section 6).

---

## 5. Deploy Option B — VPS (Ubuntu 22.04)

### 5.1 Server setup

```bash
# SSH vào VPS
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose-plugin nginx certbot python3-certbot-nginx
sudo usermod -aG docker $USER
```

### 5.2 Clone & configure

```bash
git clone <your-repo> /opt/videodangonngu
cd /opt/videodangonngu
cp .env.example backend/.env
# Edit backend/.env với Supabase keys + production settings
```

### 5.3 Start services

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Services: `api`, `worker`, `redis`

### 5.4 Nginx reverse proxy

```nginx
# /etc/nginx/sites-available/videodangonngu
server {
    listen 80;
    server_name your-domain.com;

    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 500M;
    }

    location / {
        root /var/www/videodangonngu/frontend/dist;
        try_files $uri $uri/ /index.html;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/videodangonngu /etc/nginx/sites-enabled/
sudo certbot --nginx -d your-domain.com
sudo nginx -t && sudo systemctl reload nginx
```

- [ ] VPS provisioned
- [ ] Docker compose running
- [ ] Nginx + HTTPS configured
- [ ] Frontend built: `cd frontend && npm run build`

---

## 6. Deploy Frontend (Vercel / Netlify)

1. Connect GitHub repo
2. Root directory: `frontend`
3. Build command: `npm run build`
4. Output: `dist`
5. **Environment variables:** KHÔNG thêm Supabase service role key
6. Rewrites/proxy `/api` → backend URL:

**Vercel** (`vercel.json`):
```json
{
  "rewrites": [
    { "source": "/api/(.*)", "destination": "https://your-api.railway.app/api/$1" }
  ]
}
```

- [ ] Frontend deployed
- [ ] `/api` proxy hoạt động
- [ ] `PUBLIC_BASE_URL` trỏ đúng domain frontend

---

## 7. Post-Deploy Verification

- [ ] `GET https://your-api/api/health` → `{"status":"ok","ffmpeg":true}`
- [ ] Admin login với email/password đã set
- [ ] **Đổi admin password** ngay sau lần login đầu (hoặc đổi `ADMIN_PASSWORD` trước deploy)
- [ ] Upload MP4 + SRT + voice → Generate → thành công
- [ ] Publish video
- [ ] Public URL: video playable, subtitle/audio switch hoạt động
- [ ] Unpublished video → 404
- [ ] QR code trỏ đúng `PUBLIC_BASE_URL`

---

## 8. Secrets Checklist

| Secret | Backend | Frontend | Ghi chú |
|--------|---------|----------|---------|
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | ❌ NEVER | Full DB + Storage access |
| `SUPABASE_ANON_KEY` | ✅ optional | ❌ | Không cần nếu frontend chỉ gọi FastAPI |
| `OPENAI_API_KEY` | ✅ | ❌ | |
| `JWT_SECRET` | ✅ | ❌ | |
| `ADMIN_PASSWORD` | ✅ env | ❌ | Seed lúc startup |

**Không bao giờ** prefix `VITE_` cho service role key.

---

## 9. Chi phí ước tính (MVP)

| Service | Free tier | Khi scale |
|---------|-----------|-----------|
| Supabase | 500MB DB, 1GB storage | Pro ~$25/tháng |
| Railway | $5 credit/tháng | ~$10–30/tháng |
| Vercel | Free static hosting | Pro nếu cần |
| OpenAI | Pay per use | ~$0.01–0.10/video tùy độ dài |
| Domain | ~$10/năm | |

---

## 10. Troubleshooting

| Lỗi | Nguyên nhân | Fix |
|-----|-------------|-----|
| `Missing required Supabase configuration` | Thiếu env | Điền `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` |
| `ffmpeg: false` trong health | FFmpeg chưa cài | Cài FFmpeg trên worker/host |
| Generate fail OpenAI | Thiếu key | Set `OPENAI_API_KEY` hoặc `E2E_MOCK_TRANSLATION=1` |
| Video 404 khi xem | Chưa publish | Admin → Publish |
| Signed URL expired | Xem quá lâu | Refresh page (API tạo URL mới) |
| CORS error | Sai origin | Set `CORS_ORIGINS` đúng domain frontend |

---

## 11. Schema changes sau này

1. Tạo file mới: `supabase/migrations/002_description.sql`
2. Chạy trong Supabase SQL Editor
3. Cập nhật `backend/app/models/db.py` và repository nếu cần
4. **Không** dùng Alembic — Supabase SQL migrations là source of truth

---

## 12. Architecture tóm tắt

```
User → Frontend (static) → FastAPI API
                              ├── Supabase Database
                              ├── Supabase Storage (private bucket)
                              └── Redis → ARQ Worker (FFmpeg + pipeline)
```

Pipeline stages: PARSE → TRANSLATE → VALIDATE → TTS → ALIGN → MIX → SUBTITLE_EXPORT → FINALIZE

Media layout trong bucket `video-assets`:
```
video/{id}/original.mp4
video/{id}/thumbnail.jpg
video/{id}/subtitle/{vi,en,ru,zh}.vtt
video/{id}/audio/{vi,en,ru,zh}.mp3
```
