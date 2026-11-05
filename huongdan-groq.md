# Hướng dẫn Generate video với Groq

Tài liệu này liệt kê **việc bạn cần làm thủ công** và **việc hệ thống đã làm sẵn**.

---

## Luồng tổng quan

```
Upload (MP4 + SRT)     →  Generate (bấm nút)     →  Publish
     draft                    processing              published
                         Groq dịch + Edge TTS
                         4 ngôn ngữ + audio
```

**Upload không tự dịch.** Sau upload, vào trang chi tiết video → bấm **Generate**.

---

## PHẦN BẠN CẦN LÀM THỦ CÔNG

### 1. Tạo API key Groq (miễn phí)

1. Vào [https://console.groq.com](https://console.groq.com)
2. Đăng ký / đăng nhập
3. **API Keys** → **Create API Key**
4. Copy key (dạng `gsk_...`) — **chỉ hiện 1 lần**

> Groq free tier có rate limit. Video dài = nhiều batch dịch → có thể chậm hoặc bị 429 nếu gọi quá nhanh.

### 2. Cài FFmpeg (bắt buộc)

Pipeline cần FFmpeg để: trích thumbnail, trộn audio, căn thời gian, xuất MP3.

**Windows:**

1. Tải từ [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html) (hoặc `winget install FFmpeg`)
2. Thêm `ffmpeg` vào PATH
3. Kiểm tra:

```powershell
ffmpeg -version
ffprobe -version
```

**Kiểm tra qua API:**

```text
GET http://localhost:8000/api/health
→ "ffmpeg": true
```

### 3. Cấu hình `backend/.env`

Copy từ `.env.example` nếu chưa có, rồi điền:

```env
# Dịch phụ đề — dùng Groq (không cần OpenAI)
TRANSLATION_PROVIDER=groq
GROQ_API_KEY=gsk_your_key_here
GROQ_MODEL=openai/gpt-oss-120b

# TTS vẫn dùng Edge TTS (miễn phí, không cần key)
TTS_PROVIDER=edge
```

**Model Groq gợi ý:**

| Model | Ghi chú |
|---|---|
| `openai/gpt-oss-120b` | **Mặc định** — thay thế `llama-3.3-70b-versatile` (đã ngừng 08/2026) |
| `qwen/qwen3.6-27b` | Nhanh, hỗ trợ tool/vision |
| `openai/gpt-oss-20b` | Nhẹ hơn 120B |

> **Lưu ý:** Sau khi đổi `GROQ_MODEL` trong `.env`, phải **restart uvicorn** (Ctrl+C rồi chạy lại). `--reload` không tự đọc lại `.env`.

Xem model mới nhất tại [Groq docs](https://console.groq.com/docs/models).

### 4. Restart backend

```powershell
cd backend
.venv\Scripts\activate
# Ctrl+C server cũ
uvicorn app.main:app --reload --port 8000
```

`.env` không tự reload khi dùng `--reload`.

### 5. Upload file đúng format

| File | Bắt buộc | Ghi chú |
|---|---|---|
| MP4 | ✅ | Video gốc |
| SRT | ✅ | Phụ đề tiếng Việt, timeline chuẩn |
| Voice MP3 | Khuyến nghị | Giọng thuyết minh vi-VN (không TTS lại) |
| Music MP3 | Tuỳ chọn | Nhạc nền mix với giọng |

### 6. Chạy Generate

1. Mở `http://localhost:5173/admin/videos/new` → upload
2. Chuyển sang trang chi tiết video
3. Bấm **Generate**
4. Theo dõi thanh tiến trình + danh sách jobs
5. Khi `ready_for_review` → nghe thử từng ngôn ngữ → **Publish**

### 7. (Tuỳ chọn) Cloudflare R2

Nếu dùng storage R2, làm theo `huongdanchuyen.md` trước. Generate không liên quan R2 key — chỉ cần file đã upload lên R2.

---

## PHẦN HỆ THỐNG ĐÃ LÀM SẴN

| Tính năng | Mô tả |
|---|---|
| Groq provider | `backend/app/services/translation/groq_provider.py` |
| Factory | `TRANSLATION_PROVIDER=groq` → dùng Groq API |
| Generate API | `POST /api/admin/videos/{id}/generate` |
| Validate trước Generate | Kiểm tra `GROQ_API_KEY`, FFmpeg, file SRT |
| Pipeline | PARSE → TRANSLATE (Groq) → TTS (Edge) → MIX → VTT |
| Frontend progress | Thanh % + jobs trên trang chi tiết video |
| Lỗi rõ ràng | Hiện lỗi Groq/FFmpeg/thiếu key trên UI |

---

## Pipeline chi tiết

```
vi-VN:  SRT → segments DB → voice MP3 upload (hoặc trích từ video)
en/ru/zh: SRT → Groq dịch → Edge TTS → căn thời gian → mix → .vtt + .mp3
```

Ngôn ngữ xử lý khi Generate: `en-US`, `ru-RU`, `zh-CN` (+ finalize `vi-VN`).

---

## Troubleshooting

| Triệu chứng | Nguyên nhân | Cách fix |
|---|---|---|
| Generate báo thiếu GROQ_API_KEY | Chưa điền `.env` | Thêm key + restart uvicorn |
| FFmpeg chưa cài | Không có trong PATH | Cài FFmpeg, restart terminal |
| Status `failed` | Groq rate limit / lỗi JSON | Xem jobs + log server; thử model nhỏ hơn |
| Ngôn ngữ `pending` | Chưa Generate | Bấm Generate |
| Upload xong không có audio | Bình thường | Generate mới tạo audio |
| Groq 429 Too Many Requests | Free tier limit | Đợi vài phút hoặc nâng plan |

---

## Test nhanh không tốn Groq

```powershell
cd backend
set E2E_MOCK_TRANSLATION=1
python -m tests.run_e2e_pipeline
```

Cần FFmpeg. Không gọi Groq thật.

---

## Checklist

- [ ] Tạo Groq API key
- [ ] Cài FFmpeg (`ffmpeg -version` OK)
- [ ] `GROQ_API_KEY` trong `backend/.env`
- [ ] `TRANSLATION_PROVIDER=groq`
- [ ] Restart uvicorn
- [ ] Upload MP4 + SRT (+ voice MP3)
- [ ] Bấm Generate → đợi 100%
- [ ] Publish

---

## Không commit

- `GROQ_API_KEY`
- `S3_SECRET_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`

Giữ trong `backend/.env` (đã gitignore).
