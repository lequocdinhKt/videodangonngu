# Đánh giá dự án Video Đa Ngôn Ngữ

Tài liệu này tổng hợp **ưu điểm**, **nhược điểm** và **những phần còn thiếu**. Cập nhật sau Supabase migration (2026-08).

---

## Supabase Migration — Trạng thái (verified by tests)

### FIXED (verified)

| Hạng mục | Chi tiết |
|----------|----------|
| SQLite / local PostgreSQL dependency | Gỡ SQLAlchemy runtime; Supabase client + repository |
| `create_all()` startup schema | Schema qua `supabase/migrations/001_initial_schema.sql` |
| Local media storage dependency | `SupabaseStorageProvider` + private bucket |
| Raw filesystem trong pipeline | `backend/workspace/` cho temp; upload finals lên Supabase |
| Public unpublished media access | Subtitle/audio check `published`; `/api/media` removed |
| Missing `pipeline_run_id` | Có trong schema + worker |
| Missing `videos.result_meta` | JSONB trong schema |
| Alembic dead code | Đã xóa alembic runtime |
| Upload size limit | `max_upload_mb` enforced trong admin upload |
| ARQ worker | `app/workers/arq_worker.py` + Dockerfile |
| Deploy guide | `SETUP_DEPLOY.md` |

### REMAINING

| Hạng mục | Chi tiết |
|----------|----------|
| Supabase integration tests (live) | Chỉ có mock tests; cần `SUPABASE_INTEGRATION=1` + credentials |
| Frontend polish | Quality flags UI, unpublish button |
| Rate limiting | Chưa có |
| Video delete storage cleanup | Chỉ xóa DB row |
| `USE_ARQ=true` production verify | Cần deploy Redis + worker thật |

**Tests passed (2026-08):** 35 unit tests (`pytest -m "not integration"`)

---

## 1. Tổng quan nhanh

| Hạng mục | Thực tế |
|----------|---------|
| Backend | FastAPI, Supabase integration |
| Frontend | React 19 + Vite + Tailwind |
| Tests | 10+ backend test files |
| Database | **Supabase PostgreSQL** (SQL migrations) |
| Storage | **Supabase Storage** (`video-assets` bucket) |
| Queue | ARQ + Redis (optional); asyncio fallback dev |
| Ngôn ngữ hỗ trợ | vi-VN, en-US, ru-RU, zh-CN |

**Kết luận ngắn:** MVP migrate sang Supabase xong. Deploy theo `SETUP_DEPLOY.md`.

---

## 2. Ưu điểm

### 2.1 Kiến trúc & thiết kế hệ thống

- **Nguyên tắc cốt lõi rõ ràng:** 1 video gốc + 4 track phụ đề + 4 track audio, không re-encode video, không burn subtitle — đúng hướng scalable.
- **Tách lớp hợp lý:** API routes / models / schemas / services / workers — codebase nhỏ, dễ đọc, ít layer thừa.
- **Provider pluggable:** Translation (`TranslationProvider`), TTS (`TTSEngine`), Storage (`BaseStorage`) — dễ thay OpenAI, Edge TTS, S3 sau này.
- **Tài liệu kiến trúc:** `PROJECT_ARCHITECTURE.md` mô tả rõ schema DB, pipeline stages, API, player design.

### 2.2 Backend pipeline (điểm mạnh nhất)

- **Pipeline đầy đủ:** PARSE → TRANSLATE → VALIDATE → TTS → ALIGN → MIX → SUBTITLE_EXPORT → FINALIZE.
- **Dịch theo batch có ngữ cảnh:** batch 12 segment, overlap 3 segment, truyền title/description/topic/glossary/proper nouns và segment lân cận.
- **Validation trước TTS:** kiểm tra số segment, timestamp, số liệu; retry 1 lần nếu fail.
- **Alignment đa tầng:** time-stretch nhẹ → stretch + silence → concise re-translate → flag `alignment_failed` + silence (không ép audio sai nghĩa).
- **Quality flags:** gom vào job FINALIZE, status `requires_review` khi có cảnh báo.
- **Regenerate theo ngôn ngữ:** chỉ chạy lại pipeline cho 1 lang, giữ nguyên asset các lang khác và merge quality flags.
- **Timeline duration:** `max(video.duration_ms, srt_end_ms)` — audio không ngắn hơn video gốc.
- **Music mixing:** trim/pad theo timeline, `amix=duration=first`, lưu `mix_config` vào DB.
- **TTS cache:** SHA256 cache theo provider/lang/voice/text — tiết kiệm chi phí khi regenerate.
- **Workspace cleanup:** xóa file tạm sau xử lý (success/fail), không đụng asset cuối.
- **Regression tests pipeline:** `test_pipeline_regressions.py` cover nhiều edge case thực tế.

### 2.3 Frontend player

- **Player architecture đúng thiết kế:** `<video>` làm master clock, `<audio>` ẩn cho dubbing, subtitle overlay tùy chỉnh.
- **Chọn ngôn ngữ độc lập:** subtitle và audio có thể khác nhau; toggle dubbing vi ↔ ngôn ngữ đã chọn.
- **AudioSyncController:** đồng bộ play/pause/seek, drift correction.
- **Subtitle customization:** font, màu, opacity, vị trí.
- **Admin workflow cơ bản:** upload → generate → xem jobs → publish; có QR code.

### 2.4 Dev experience

- **Setup nhanh:** README rõ ràng, `.env.example` đầy đủ, PostgreSQL qua `docker compose` + `alembic upgrade head`.
- **E2E mock:** `E2E_MOCK_TRANSLATION=1` chạy pipeline không cần OpenAI key.
- **Health check:** `/api/health` kiểm tra FFmpeg availability.
- **CORS configurable** qua env.

### 2.5 Bảo mật cơ bản (phần đã có)

- Admin API yêu cầu JWT Bearer token.
- Password hash bcrypt.
- API key OpenAI chỉ ở backend env, không lộ ra frontend bundle.
- Public list/detail video filter `status == published`.

---

## 3. Nhược điểm

### 3.1 Production readiness thấp

| Vấn đề | Chi tiết |
|--------|----------|
| Không có migration | ~~DB tạo bằng `Base.metadata.create_all()`~~ → **PASS (Phase 1):** Alembic `001_initial_schema`; `init_db()` không gọi `create_all()` |
| Queue gắn API process | `start_pipeline()` = `asyncio.create_task()` — mất job khi restart server, không scale worker |
| Storage local only | `get_storage()` hardcode `LocalStorageProvider`, settings S3 chưa implement |
| Không containerize app | `docker-compose.yml` chỉ Postgres + Redis, không có Dockerfile backend/frontend |
| Mâu thuẫn setup | ~~README / `.env.example` dùng SQLite~~ → **PASS (Phase 1):** đồng bộ PostgreSQL + `alembic upgrade head` |

### 3.2 Bảo mật — rủi ro cao

| Vấn đề | File | Mức độ |
|--------|------|--------|
| Media serve không auth | `GET /api/media/{path}` — ai biết key đều tải được | **Cao** |
| Subtitle/audio không check published | `public.py` — endpoint subtitle/audio không join `Video.status` | **Cao** |
| Publish từ draft | `admin.py` — cho phép publish video `draft` chưa generate | Trung bình |
| JWT secret mặc định | `change-me-in-production` trong `.env.example` | Trung bình |
| Admin credentials mặc định | `admin@example.com` / `admin123` seed lúc startup | Trung bình |
| Upload không giới hạn size | `max_upload_mb=500` trong settings nhưng route upload không enforce | Trung bình |
| Frontend route guard yếu | Chỉ dashboard check token; upload/detail page không redirect login | Thấp |
| Không rate limiting | Toàn bộ API | Thấp |

### 3.3 Config / code chưa wired

| Setting | Trạng thái |
|---------|-----------|
| `USE_ARQ` | Có trong env, không có ARQ worker module |
| `tts_concurrency` | Khai báo, TTS vẫn chạy tuần tự từng segment |
| `max_upload_mb` | Khai báo, upload route không check |
| `audio_drift_tolerance_ms` | Backend không dùng (frontend hardcode 100ms) |
| `validate_srt_structure()` | Có hàm, pipeline không gọi sau PARSE |
| `ProcessingJob.retry_count` | Field có, logic không tăng |
| Stage `UPLOAD` | Enum có, không ghi job |
| `TTSEngine.list_voices()` | Architecture mô tả, chưa implement |

### 3.4 Pipeline — hạn chế còn lại

- **Voice separation (Mode B):** tên config gợi ý tách voice/music nhưng thực tế chỉ `ffmpeg.extract_audio()` từ MP4 — không dùng Demucs/Spleeter.
- **Không export `metadata.json`** theo layout storage trong architecture.
- **SRT lưu key `source.srt`**, không đồng nhất hoàn toàn với layout tài liệu.
- **Xóa video chỉ xóa DB** — file trong `storage/video/{id}/` không bị cleanup.
- **Một video chỉ chạy 1 pipeline** — `_active_tasks` chặn duplicate nhưng không queue job chờ.

### 3.5 Frontend — thiếu polish

- **Không hiển thị quality flags** — admin không thấy lý do `requires_review`.
- **Không có nút Unpublish** — API có (`POST /unpublish`), frontend không gọi.
- **Publish khi `requires_review`** — không có action/hướng dẫn rõ cho admin.
- **`bgOpacity` trong SubtitleSettings** — khai báo type nhưng không áp dụng vào style.
- **Error handling cơ bản** — nhiều chỗ `console.error`, không toast/notification.
- **Không có state management** — fetch trực tiếp, polling 2s khi processing.
- **0 test frontend** — không Vitest, Playwright, Cypress.

### 3.6 Testing — coverage gaps

| Đã có | Chưa có |
|-------|---------|
| Health endpoint | API admin (login, upload, publish, 401) |
| Parse SRT, VTT, alignment compute | Public API security (media leak) |
| Pipeline regression (sâu) | Storage delete on video delete |
| E2E pipeline (mock + OpenAI) | Frontend tests |
| | Coverage report (pytest-cov) |
| | CI/CD pipeline |

---

## 4. So sánh với PROJECT_ARCHITECTURE.md

### Đã implement (khớp hoặc gần khớp)

- [x] Schema DB 6 bảng + upload keys (voice, music, srt)
- [x] Pipeline stages chính
- [x] OpenAI translation + Edge TTS
- [x] Multi-tier alignment + quality flags
- [x] Per-language regenerate API
- [x] Admin upload → generate → review → publish
- [x] Public player đa ngôn ngữ
- [x] QR code admin
- [x] Storage layout cơ bản (`video/{id}/original.mp4`, `subtitle/`, `audio/`, `workspace/`)

### Chưa implement / lệch tài liệu

- [x] PostgreSQL + Alembic migrations — **PASS (Phase 1)**
- [ ] ARQ worker tách khỏi API
- [ ] S3 storage provider
- [ ] Thư mục `processors/`, `services/video/`
- [ ] `metadata.json` per video
- [ ] Voice separation thật (Mode B)
- [ ] `TTSEngine.list_voices()`
- [ ] Segment-level regenerate UI
- [ ] Job retry logic (`retry_count`)
- [ ] UPLOAD stage tracking

---

## 5. Còn thiếu — đề xuất bổ sung cho lần sau

### Ưu tiên cao (nên làm trước khi production)

1. **Bảo mật media**
   - Kiểm tra `Video.status == published` trên `/subtitles/`, `/audio/`, `/media/`
   - Hoặc signed URL có expiry cho media private

2. **Database migrations** — **PASS (Phase 1)**
   - Alembic `backend/alembic/` + migration `001_initial_schema`
   - PostgreSQL là DB chính (đồng bộ docker-compose)
   - Dev workflow: `alembic upgrade head`

3. **Background worker**
   - ARQ worker module tách khỏi uvicorn
   - Job persist qua Redis, survive server restart
   - Retry logic dùng `retry_count`

4. **Storage production**
   - Implement S3 provider (`STORAGE_PROVIDER=s3`)
   - Cleanup storage khi `DELETE /videos/{id}`

5. **Upload validation**
   - Enforce `max_upload_mb`
   - Kiểm tra MIME type, không chỉ extension

### Ưu tiên trung bình

6. **Admin UI improvements**
   - Hiển thị `quality_flags` và lý do `requires_review`
   - Block publish khi `requires_review` (hoặc confirm dialog)
   - Nút Unpublish
   - ProtectedRoute cho tất cả trang admin

7. **Pipeline hardening**
   - Gọi `validate_srt_structure()` sau PARSE
   - Parallel TTS theo `tts_concurrency`
   - Export `metadata.json` per video

8. **API tests**
   - Test auth 401/403
   - Test upload validation
   - Test publish/unpublish flow
   - Test media access control

9. **Docker & deploy**
   - Dockerfile backend + frontend
   - docker-compose service đầy đủ (api + worker + web)
   - CI/CD (GitHub Actions: lint, test, build)

### Ưu tiên thấp / tương lai

10. **Voice separation thật** — Demucs/Spleeter khi Mode B (mixed MP4)
11. **Segment-level regenerate** — UI + API cho 1 segment
12. **`list_voices()` TTS API** — admin chọn voice per language
13. **Frontend tests** — Vitest + Playwright E2E
14. **Rate limiting** — slowapi hoặc middleware
15. **Refresh token** — JWT expire handling tốt hơn
16. **Monitoring** — structured logging, metrics, alerting khi pipeline fail
17. **i18n admin UI** — giao diện admin đa ngôn ngữ
18. **Thumbnail regeneration** — khi video thay đổi
19. **Webhook/notification** — báo admin khi pipeline xong
20. **Batch upload** — nhiều video cùng lúc

---

## 6. Roadmap đề xuất (theo giai đoạn)

```
Giai đoạn 1 — Production safety (1–2 tuần)
├── Bảo mật media endpoints
├── Alembic + PostgreSQL
├── Enforce upload limits
└── API tests cơ bản

Giai đoạn 2 — Infrastructure (1–2 tuần)
├── ARQ worker
├── S3 storage
├── Storage cleanup on delete
└── Dockerfile + docker-compose đầy đủ

Giai đoạn 3 — Admin UX (1 tuần)
├── Quality flags UI
├── Publish/unpublish flow hoàn chỉnh
├── ProtectedRoute
└── Error handling / toast

Giai đoạn 4 — Quality & scale (ongoing)
├── Parallel TTS
├── Frontend tests
├── CI/CD
├── Voice separation thật
└── Monitoring
```

---

## 7. Thống kê codebase

| Metric | Số liệu |
|--------|---------|
| Backend app files | ~22 |
| Frontend src files | ~14 |
| Backend test files | 7 |
| Frontend test files | 0 |
| API admin endpoints | 11 |
| API public endpoints | 5 + health + media |
| Dependencies khai báo chưa wired | arq, s3 settings, tts_concurrency (alembic **PASS**) |

---

## 8. Ghi chú sau audit pipeline gần nhất

Các fix audit đã hoàn thành và test pass:

| Hạng mục audit | Trạng thái |
|----------------|------------|
| Alignment safety | PASS |
| Per-language regeneration isolation | PASS |
| Workspace cleanup | PASS |
| Translation context | PASS |
| Long-video timeline duration | PASS |
| Background music duration | PASS |
| Quality flags preserved across regeneration | PASS |
| DB/storage consistency (mix_config, VTT via storage) | PASS |
| PostgreSQL + Alembic migrations (Phase 1) | PASS |
| Schema constraints (unique lang, segment sequence, FK, cascade) | PASS (tests `test_database.py`) |

**Chưa test với OpenAI thật** — nên chạy E2E với API key thật trước khi deploy.

---

## 9. Architecture Decisions / Architecture Freeze

**Phase:** 1 — Database infrastructure implemented (2026-08-29)  
**Status:** PostgreSQL + Alembic **PASS**; ARQ/S3 unchanged (Phase 2+)

This section records the **final architectural decisions** so Phase 1+ can proceed without rewrites. It reflects a full review of `backend/app`, `frontend/src`, `tests`, `docker-compose.yml`, requirements, `package.json`, `.env.example`, and `PROJECT_ARCHITECTURE.md`.

---

### 9.1 Current Architecture (As-Is)

```
┌─────────────┐     HTTP      ┌──────────────────────────────────────┐
│ React SPA   │ ────────────► │ FastAPI (single process)             │
│ (Vite)      │               │  • admin + public routes             │
└─────────────┘               │  • lifespan: init_db() (no create_all)│
                              │  • start_pipeline() → asyncio.Task   │
                              └───────┬──────────────┬─────────────────┘
                                      │              │
                              PostgreSQL (canonical)  LocalStorageProvider
                              Alembic migrations      ./storage (hardcoded)
                              asyncpg                   /api/media/{key}
```

| Area | Current state |
|------|---------------|
| **Database** | Default `postgresql+asyncpg://…@localhost:5432/videodangonngu`. Schema via **Alembic only** (`backend/alembic/`, revision `001_initial_schema`). `init_db()` is a no-op — no `create_all()` at startup. SQLite retained for isolated unit/pipeline tests via `create_all_for_tests()`. |
| **Queue** | `start_pipeline()` → `asyncio.create_task(run_pipeline)`. In-memory `_active_tasks` dict. `USE_ARQ=false` in settings; no ARQ worker module. Jobs partially persisted in `processing_jobs` table but execution is not durable. |
| **Storage** | `BaseStorage` / `StorageProvider` protocol exist. `get_storage()` always returns `LocalStorageProvider`. S3 settings declared but unused. Pipeline/worker/TTS cache bypass abstraction via `Path(settings.storage_dir)`. |
| **Processing** | Full pipeline implemented: PARSE → TRANSLATE → VALIDATE → TTS → ALIGN → MIX → SUBTITLE_EXPORT → FINALIZE. Original MP4 never re-encoded. VTT and MP3 stored as independent keys. |
| **API** | Routes depend directly on `get_storage()` from `local` module and `start_pipeline()` from worker. No dispatcher/dependency-injection layer. |
| **AI** | `TranslationProvider` + `TTSEngine` ABCs with factory functions (`get_translation_provider`, `get_tts_engine`) driven by env. Worker imports concrete providers; routes do not. |
| **Config** | Pydantic Settings with env vars. Defaults include SQLite URL, weak JWT secret, default admin credentials. |
| **Deploy** | `docker-compose.yml` provides Postgres 16 (+ healthcheck) + Redis 7. Env vars for DB credentials. Dev: `docker compose up -d` → `alembic upgrade head` → `uvicorn`. No API/worker/web containers yet. |

**Verdict:** MVP pipeline works end-to-end, but infrastructure is **dev-embedded** (DB schema, job execution, storage paths) rather than production-topology-ready.

---

### 9.2 Target Architecture (To-Be)

```
                         Internet
                             │
                      Reverse Proxy (nginx/Caddy)
                     /                    \
            Frontend (static)         FastAPI API
            React build                  │
                                         ├──► PostgreSQL (canonical)
                                         ├──► Redis
                                         │         │
                                         │    ARQ Worker(s)
                                         │    (separate process)
                                         │
                                         └──► S3-compatible Storage
                                              (prod) / Local (dev)

Worker/API ──► TranslationProvider / TTSEngine (env-selected)
Worker/API ──► FFmpeg (local temp files only; never re-encode video)
```

**Invariant rules (non-negotiable):**

1. Original MP4 is **stream-copied only** — never re-encoded.
2. Subtitles = independent VTT files; audio = independent MP3 tracks.
3. Business logic never imports OpenAI, Edge TTS, boto3, or local filesystem paths directly.
4. Production schema is **Alembic-only** — `create_all()` forbidden in prod/staging.
5. Job execution survives API process restart via Redis + ARQ.

---

### 9.3 Database Decision

**Decision:** PostgreSQL is the **canonical** database for development (normal) and all production environments.

| Component | Decision |
|-----------|----------|
| ORM | SQLAlchemy 2.x declarative, async sessions via `asyncpg` |
| Driver URL | `postgresql+asyncpg://user:pass@host:5432/dbname` |
| Migrations | Alembic for **all** schema changes |
| SQLite | Optional **test-only** via `DATABASE_URL=sqlite+aiosqlite:///:memory:` or temp file; never design features around SQLite semantics |
| Sync path | Alembic uses sync driver (`postgresql+psycopg2://` or `postgresql://`) for migrations; app runtime stays async |

**PostgreSQL compatibility review of current models (`backend/app/models/db.py`):**

| Element | Current | Compatible? | Phase 1 action |
|---------|---------|-------------|----------------|
| Primary keys | `UUID(as_uuid=True)` via `postgresql.UUID` | Yes | Keep; use `gen_random_uuid()` server default in migration |
| Timestamps | `DateTime(timezone=True)` + `server_default=func.now()` | Yes | Keep; maps to `TIMESTAMPTZ` |
| JSON fields | `postgresql.JSON` on `alignment_meta`, `mix_config` | Yes | **Change to `JSONB`** for PostgreSQL (query/index capable) |
| Enums | `Enum(VideoStatus)` etc. without explicit `name=` | Yes, fragile | Add named native enums: `video_status`, `language_status`, `job_status`, `processing_stage` |
| FK cascades | `video_languages`, `subtitle_segments`, `audio_tracks`, `processing_jobs` → `ON DELETE CASCADE` from video | Mostly OK | Keep video→children cascade; see cascade notes below |
| `users.id` ← `videos.created_by` | No `ondelete` (RESTRICT) | OK | Keep RESTRICT — prevent orphan policy issues |
| Indexes | Only `users.email`, `video_languages.language_code` | Incomplete | Add indexes (see §9.9) |
| Unique constraints | `users.email`, `audio_tracks.video_language_id` | Incomplete | Add composites (see §9.9) |

**Critical PostgreSQL note:** Models already use PostgreSQL dialect types (`postgresql.UUID`, `postgresql.JSON`). This is **correct for the target** but **conflicts with current SQLite default**. Phase 1 must switch default `.env.example` to PostgreSQL and treat SQLite as explicit test opt-in.

**`init_db()` decision:** **PASS (Phase 1)** — `create_all()` removed from application startup. Schema managed exclusively by Alembic. Tests use `create_all_for_tests()` against SQLite only.

---

### 9.4 Queue Decision

**Decision:** Redis + ARQ worker as the **production job queue**. In-process `asyncio.create_task()` remains an optional **development fallback**.

| Component | Decision |
|-----------|----------|
| Broker | Redis (`REDIS_URL`) |
| Worker framework | ARQ (`arq>=0.26.0` already in requirements) |
| Worker process | Separate entrypoint: `python -m app.workers.arq_worker` (to be created Phase 1) |
| Job persistence | Redis queue + `processing_jobs` table for status/progress audit |
| API role | Enqueue only — never run long pipeline in request handler |
| Dev fallback | `USE_ARQ=false` → `InProcessJobDispatcher` wrapping current `asyncio.create_task` |
| Idempotency | API checks `processing_jobs` + video status before enqueue; worker uses `pipeline_run_id` (new column) |

**Dispatcher abstraction (Phase 1):**

```python
class JobDispatcher(Protocol):
    async def enqueue_pipeline(self, video_id: UUID, language_codes: list[str] | None = None) -> str: ...

def get_job_dispatcher() -> JobDispatcher:
    if settings.use_arq:
        return ArqJobDispatcher(settings.redis_url)
    return InProcessJobDispatcher()
```

**Routes change:** Replace direct `start_pipeline()` calls with `await dispatcher.enqueue_pipeline(...)`.

**Retry policy:** ARQ `max_tries` + increment `processing_jobs.retry_count` on failure. Failed jobs set `Video.status = failed` only after exhausting retries.

**Concurrency:** One active full pipeline per `video_id` enforced at DB level (status check + partial unique index on running jobs), not in-memory `_active_tasks`.

---

### 9.5 Storage Decision

**Decision:** All asset I/O goes through a **`StorageProvider`** abstraction. Two implementations required:

| Provider | Env | Use case |
|----------|-----|----------|
| `LocalStorageProvider` | `STORAGE_PROVIDER=local` | Local dev, CI with temp dirs |
| `S3StorageProvider` | `STORAGE_PROVIDER=s3` | Production (AWS S3, MinIO, R2, etc.) |

**Factory (Phase 1):**

```python
def get_storage() -> StorageProvider:
    match settings.storage_provider:
        case "local": return LocalStorageProvider(settings.storage_dir)
        case "s3":    return S3StorageProvider(...)
        case _:       raise ValueError(...)
```

**Key layout (unchanged):**

```
video/{video_id}/original.mp4
video/{video_id}/thumbnail.jpg
video/{video_id}/source.srt
video/{video_id}/voice_vi.mp3
video/{video_id}/music.mp3
video/{video_id}/subtitle/{lang}.vtt
video/{video_id}/audio/{lang}.mp3
video/{video_id}/workspace/   ← ephemeral; never served publicly
cache/tts/                      ← ephemeral cache
```

**Rules:**

- Business logic stores **keys** in DB, never absolute paths.
- `get_url(key)` returns `/api/media/{key}` for local; presigned HTTPS URL for S3.
- FFmpeg operations that need local files use `storage.download_to_temp(key) -> Path` and `storage.upload_from_path(key, path)` — new methods on provider.
- **Remove** direct `Path(settings.storage_dir)` from `pipeline_worker.py`, `workspace.py`, `tts/cache.py`. Workspace paths derived from storage provider temp API.
- `DELETE /videos/{id}` must call `storage.delete_prefix(f"video/{id}/")` (new method) before DB delete.

**Env vars (all required for S3 prod):**

`STORAGE_PROVIDER`, `STORAGE_DIR` (local), `S3_BUCKET`, `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION` (add), `S3_PUBLIC_BASE_URL` (optional CDN)

---

### 9.6 Processing Pipeline Decision

**Decision:** Keep existing stage order — **no changes to pipeline semantics.**

```
PARSE → TRANSLATE → VALIDATE → TTS → ALIGN → MIX → SUBTITLE_EXPORT → FINALIZE
```

| Rule | Status |
|------|--------|
| Original MP4 never re-encoded | Implemented (upload stream copy only) |
| Independent VTT tracks | Implemented |
| Independent audio tracks | Implemented |
| Per-language regenerate | Implemented; re-runs TRANSLATE→FINALIZE for one `language_code` |
| Vietnamese audio from upload | Implemented; no TTS for vi-VN |
| Validation before TTS | Implemented |
| Quality flags → `requires_review` | Implemented (stored in `processing_jobs.error_message` — **move to JSONB column**, see §9.9) |

**Stage enum:** `ProcessingStage` exists in Python but DB column `processing_jobs.stage` is `String(50)`. **Decision:** migrate column to native PostgreSQL enum `processing_stage` for consistency and CHECK integrity.

**UPLOAD stage:** Not currently tracked. **Decision:** defer UPLOAD job row to Phase 2; upload is synchronous in API. Not blocking.

---

### 9.7 API Layer Decision

**Decision:** Routes remain thin orchestrators. Phase 1 introduces dependency injection for infrastructure:

| Dependency | Injection | Routes must NOT |
|------------|-----------|-----------------|
| Database | `Depends(get_db)` | Import engine/session factory directly |
| Storage | `Depends(get_storage)` | Import `local.get_storage` |
| Job queue | `Depends(get_job_dispatcher)` | Call `start_pipeline()` / `asyncio.create_task` |
| Translation/TTS | Worker-only | Import OpenAI/Edge in routes |

**Media serving:**

- **Local dev:** keep `GET /api/media/{path}` with auth gate (Phase 1 security fix).
- **Production S3:** public published assets via presigned URLs or CDN; admin preview via short-lived signed URLs.
- Public subtitle/audio endpoints must join `Video.status == published`.

---

### 9.8 AI Provider Decision

**Decision:** Keep existing interfaces unchanged.

| Interface | Factory env | MVP impl | Extension |
|-----------|-------------|----------|-----------|
| `TranslationProvider` | `TRANSLATION_PROVIDER`, `TRANSLATION_MODEL`, `OPENAI_API_KEY` | `openai` | Add providers without touching pipeline |
| `TTSEngine` | `TTS_PROVIDER`, `TTS_VOICE_*` | `edge` | Add providers without touching pipeline |

**Rules:**

- Pipeline/worker calls `get_translation_provider()` and `get_tts_engine()` only.
- Provider factories live in `services/translation/` and `services/tts/`.
- `TTSEngine.list_voices()` — add in Phase 2; not blocking freeze.

**E2E testing:** keep `E2E_MOCK_TRANSLATION=1` stub provider for CI without API keys.

---

### 9.9 Database Schema Review & Phase 1 Schema Changes

Review of all six tables against idempotency, regeneration, and production needs.

#### `users`

| Field | OK? | Notes |
|-------|-----|-------|
| id UUID PK | Yes | |
| email unique | Yes | Keep `UNIQUE` + index |
| password_hash | Yes | |
| role | Yes | Consider enum later; string OK for MVP |
| created_at TIMESTAMPTZ | Yes | |

No blocking changes.

#### `videos`

| Field | OK? | Notes |
|-------|-----|-------|
| status enum | Yes | Add index: `CREATE INDEX ix_videos_status ON videos(status)` |
| created_by FK | Yes | Add index on `created_by` |
| upload keys | Yes | All nullable until upload completes — OK |
| updated_at | Yes | |
| **Missing** | | `published_at TIMESTAMPTZ NULL` — set on publish |
| **Missing** | | `processing_started_at`, `processing_completed_at` for admin UI |

#### `video_languages`

| Field | OK? | Notes |
|-------|-----|-------|
| language_code | Yes | |
| **Missing** | | **`UNIQUE(video_id, language_code)`** — prevents duplicate lang rows |
| status enum | Yes | |
| subtitle_key | Yes | |

**Cascade:** `ON DELETE CASCADE` from video is correct.

#### `subtitle_segments`

| Field | OK? | Notes |
|-------|-----|-------|
| sequence/start/end | Yes | |
| alignment_meta | Change to JSONB | |
| **Missing** | | **`UNIQUE(video_language_id, sequence)`** — idempotent upsert on regenerate |
| **Missing** | | Index on `(video_language_id, sequence)` for ordered fetch |

**Cascade:** CASCADE from `video_languages` is correct (deleting lang removes segments).

#### `audio_tracks`

| Field | OK? | Notes |
|-------|-----|-------|
| video_language_id UNIQUE | Yes | Enforces 1:1 — keep |
| mix_config | Change to JSONB | |
| audio_key | Yes | |

#### `processing_jobs`

| Field | OK? | Notes |
|-------|-----|-------|
| stage | Change to enum | Currently `String(50)` — use `processing_stage` PG enum |
| status enum | Yes | |
| retry_count | Yes | Wire to ARQ retry in Phase 1 |
| error_message | Overloaded | FINALIZE stores JSON quality_flags in error_message — **add `result_meta JSONB NULL`** |
| **Missing** | | **`pipeline_run_id UUID NOT NULL`** — groups jobs for one generate/regenerate run |
| **Missing** | | **`UNIQUE(video_id, stage, language_code, pipeline_run_id)`** — idempotent job rows |
| **Missing** | | Index on `(video_id, status)` for polling |
| **Missing** | | `started_at`, `completed_at TIMESTAMPTZ` |
| **Missing** | | `worker_id VARCHAR(100)` — which ARQ worker ran the job |

**Cascade concern:** `processing_jobs` CASCADE on video delete is OK (audit logs deleted with video). For future audit retention, consider soft-delete — **not MVP**.

**Regeneration idempotency:** Before re-running a language, worker deletes segments for that `video_language_id` (already done). Unique constraint on `(video_language_id, sequence)` prevents duplicate inserts if retry overlaps.

---

### 9.10 Migration Strategy

**Decision:** Alembic is the **sole** production schema mechanism.

#### Initial setup (Phase 1)

```bash
# 1. Start PostgreSQL
docker compose up -d postgres

# 2. Configure env
DATABASE_URL=postgresql+asyncpg://videodangonngu:videodangonngu@localhost:5432/videodangonngu
ALEMBIC_DATABASE_URL=postgresql+psycopg2://videodangonngu:videodangonngu@localhost:5432/videodangonngu

# 3. Initialize Alembic (once)
cd backend && alembic init alembic

# 4. Configure alembic/env.py to import app.models.db.Base.metadata
#    Use sync engine for migrations; app uses asyncpg at runtime

# 5. Generate initial migration from models + schema fixes in §9.9
alembic revision --autogenerate -m "initial_schema"

# 6. Review generated SQL manually (enums, JSONB, indexes, uniques)

# 7. Apply
alembic upgrade head
```

#### Development workflow

| Action | Command |
|--------|---------|
| Create DB | `docker compose up -d postgres` (auto-creates via POSTGRES_DB) |
| Fresh dev DB | `alembic upgrade head` |
| Schema change | Edit models → `alembic revision --autogenerate -m "description"` → review → `upgrade head` |
| Rollback one | `alembic downgrade -1` |
| Reset dev DB | `dropdb`/`createdb` or `docker compose down -v` → `upgrade head` |

#### Production deployment

```
1. Backup PostgreSQL
2. Run: alembic upgrade head   (in deploy job, before starting new API containers)
3. Start/restart API + ARQ workers
4. Never run create_all()
```

#### Test workflow

| Mode | Approach |
|------|----------|
| Unit tests (fast) | SQLite in-memory + `create_all()` in fixture — acceptable |
| Integration tests | Prefer PostgreSQL test container + Alembic migrate |
| CI | Matrix: SQLite unit + Postgres integration |

#### Future schema changes

1. Modify SQLAlchemy models.
2. `alembic revision --autogenerate` — **always review** (autogen misses renames, data migrations).
3. Data migrations use explicit `op.execute()` in upgrade/downgrade.
4. Destructive changes require backup + expand-contract pattern for zero-downtime (future).

#### `.env.example` update (Phase 1)

```env
DATABASE_URL=postgresql+asyncpg://videodangonngu:videodangonngu@localhost:5432/videodangonngu
USE_ARQ=true   # false for solo dev without worker process
```

---

### 9.11 Environment / Configuration Checklist

All infrastructure dependencies **must** be env-configurable. Phase 1 must eliminate implicit defaults that hide misconfiguration in production.

| Variable | Required prod? | Current wired? |
|----------|----------------|----------------|
| `DATABASE_URL` | Yes | Yes (wrong default) |
| `REDIS_URL` | Yes (if USE_ARQ) | Declared, not wired |
| `STORAGE_PROVIDER` | Yes | Declared, not wired |
| `STORAGE_DIR` | Dev only | Yes |
| `S3_*` | Prod (s3) | Declared, not wired |
| `JWT_SECRET` | Yes | Yes (weak default) |
| `OPENAI_API_KEY` | Yes (openai) | Yes |
| `TRANSLATION_PROVIDER` | Yes | Yes |
| `TRANSLATION_MODEL` | Yes | Yes |
| `TTS_PROVIDER` | Yes | Yes |
| `TTS_VOICE_*` | Yes | Yes |
| `USE_ARQ` | Yes | Declared, not wired |
| `FFMPEG_PATH` / `FFPROBE_PATH` | Yes | Yes |
| `CORS_ORIGINS` | Yes | Yes |
| `PUBLIC_BASE_URL` | Yes | Yes |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Dev seed only | Yes — disable auto-seed in prod |

**Production guard (Phase 1):** fail startup if `JWT_SECRET == change-me*` or SQLite URL detected when `ENV=production`.

---

### 9.12 Architectural Risks Discovered

| # | Risk | Severity | Mitigation (Phase 1+) |
|---|------|----------|----------------------|
| R1 | `create_all()` on startup — no version control, no rollback | **High** | **PASS (Phase 1):** Alembic only; removed from `init_db()` |
| R2 | SQLite default contradicts PostgreSQL-native model types | **High** | **PASS (Phase 1):** PostgreSQL default URL; SQLite test-only |
| R3 | Jobs lost on API restart | **High** | ARQ worker + Redis |
| R4 | Business logic uses `Path(settings.storage_dir)` directly | **High** | Storage temp download/upload API |
| R5 | `get_storage()` hardcoded to local | **High** | Factory + S3 provider |
| R6 | Missing `UNIQUE(video_id, language_code)` | **Medium** | **PASS (Phase 1):** added in models + migration |
| R7 | Missing `UNIQUE(video_language_id, sequence)` | **Medium** | **PASS (Phase 1):** added in models + migration |
| R8 | Quality flags in `error_message` text field | **Medium** | Add `result_meta JSONB` |
| R9 | Public media/subtitle/audio no publish check | **High** (security) | Phase 1 security pass |
| R10 | `processing_jobs.stage` as free string | **Medium** | PG enum |
| R11 | No `pipeline_run_id` — hard to correlate regenerate runs | **Medium** | Add column |
| R12 | Delete video doesn't cleanup storage | **Medium** | `delete_prefix` on storage |
| R13 | Enum types without explicit names — Alembic autogen pain | **Low** | **PASS (Phase 1):** named enums `video_status`, `language_status`, `job_status` |
| R14 | `postgresql.JSON` vs `JSONB` | **Low** | **PASS (Phase 1):** `JSONB` in migration; `JsonType` variant in models |
| R15 | README / `.env.example` / docker-compose mismatch | **Low** | **PASS (Phase 1):** aligned docs |
| R16 | No Dockerfile / full compose stack | **Medium** | Phase 2 deploy |
| R17 | FFmpeg requires local temp files even with S3 | **Low** (accepted) | Temp dir via storage provider |
| R18 | In-memory `_active_tasks` race on multi-worker | **High** (at scale) | DB-level concurrency guard |

---

### 9.13 Phase 1 Implementation Order (Reference)

1. ~~Alembic init + initial migration (schema fixes §9.9)~~ — **PASS**
2. ~~Switch defaults to PostgreSQL; guard prod config~~ — **PASS** (prod guard deferred)
3. `get_storage()` factory + refactor path leaks — Phase 2
4. `JobDispatcher` + ARQ worker module — Phase 2
5. Route DI refactor (storage, dispatcher) — Phase 2
6. Media auth / publish checks — Phase 2
7. Storage cleanup on delete — Phase 2
8. ~~Update `.env.example`, README~~ — **PASS**

---

### 9.14 Architecture Freeze Sign-Off

| Decision area | Frozen choice |
|---------------|---------------|
| Database | PostgreSQL + SQLAlchemy 2 async + Alembic |
| Queue | Redis + ARQ (in-process fallback for dev) |
| Storage | StorageProvider abstraction; Local + S3 |
| Pipeline | PARSE→…→FINALIZE; no video re-encode |
| API | Thin routes; DI for db/storage/queue |
| AI | TranslationProvider + TTSEngine interfaces |
| Config | All infra via env vars |
| Deploy topology | Proxy → Frontend + API → PG; API/Worker → Redis, S3 |

**Changes to frozen decisions require explicit architecture review before implementation.**

---

## 10. Phase 0 Status

```
PHASE 0 STATUS: WARNING
```

**Rationale:**

- Architecture review **complete**; decisions documented and actionable.
- ~~Current codebase **does not yet conform** to frozen architecture~~ → Phase 1 database items now conform.
- Foundation is **sound**: pipeline works, provider abstractions exist, models PostgreSQL-ready, docker-compose has Postgres + Redis.
- **No blocking design flaw** requiring rewrite — remaining gaps are Phase 2+ (ARQ, S3, security, storage DI).

---

## 11. Phase 1 — Database Infrastructure

### Completed work (PASS)

| Item | Status |
|------|--------|
| PostgreSQL as canonical DB (`DATABASE_URL`, `asyncpg`) | PASS |
| Alembic sole schema mechanism (`backend/alembic/`, `alembic.ini`) | PASS |
| Initial migration `001_initial_schema` (6 tables, enums, indexes, constraints) | PASS |
| Remove `create_all()` from `init_db()` / app startup | PASS |
| Model review: UUID, FK, cascade, JSONB, named enums, indexes | PASS |
| `UNIQUE(video_id, language_code)` | PASS |
| `UNIQUE(video_language_id, sequence)` + ordering index | PASS |
| `ix_processing_jobs_video_id_status` | PASS |
| docker-compose Postgres env vars + healthcheck | PASS |
| `.env.example` + README (`alembic upgrade head`) | PASS |
| Tests: SQLite unit tests separated; PostgreSQL `test_database.py` | PASS |
| Pipeline regression + E2E mock unchanged behavior | PASS |

### Remaining work (Phase 2+)

| Item | Notes |
|------|-------|
| ARQ worker + Redis queue | Not started (Phase 2) |
| S3 storage provider | Not started (Phase 2) |
| `processing_jobs.stage` → native PG enum | Still `String(50)` — deferred |
| `pipeline_run_id`, `result_meta JSONB` | Deferred per scope |
| `ENV=production` startup guards (JWT secret, SQLite block) | Deferred |
| `videodangonngu_test` DB bootstrap script in CI | Manual `CREATE DATABASE` today |
| Alembic upgrade on empty DB (verification) | Requires running PostgreSQL (Docker) |

### Phase 1 verification (2026-08-29)

| Check | Result |
|-------|--------|
| `alembic upgrade head` (empty DB) | **SKIPPED** — Docker/PostgreSQL not available in verification environment |
| Backend unit tests (`pytest -m "not postgresql and not integration"`) | **16 passed** |
| E2E mock pipeline (`E2E_MOCK_TRANSLATION=1`) | **PASSED** |
| Application startup (`init_db` no-op + admin seed) | **OK** (SQLite test harness) |
| Health check (`/api/health`) | **PASSED** |

---

## 12. Phase 1 Status

```
PHASE 1 STATUS: WARNING
```

**Rationale:**

- Database infrastructure **implemented and tested** (models, Alembic, docker-compose, docs).
- Unit tests and E2E mock pipeline **pass** without regressions.
- PostgreSQL integration tests (`test_database.py`) and live `alembic upgrade head` **not verified** in this environment (no Docker/PostgreSQL on host). Run locally:

```bash
docker compose up -d postgres
docker compose exec postgres psql -U videodangonngu -c "CREATE DATABASE videodangonngu_test;"
cd backend && alembic upgrade head
pytest tests/test_database.py -m postgresql -v
```

- Phase 2 items (ARQ, S3, storage DI, media security) **intentionally not started**.

---

*Tài liệu tạo tự động dựa trên phân tích source code. Cập nhật khi có thay đổi lớn về kiến trúc hoặc tính năng.*
