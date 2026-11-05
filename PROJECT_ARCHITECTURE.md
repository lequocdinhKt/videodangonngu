# Kiến trúc Video Guide

## Luồng sử dụng

```text
QR chung → Cloudflare Pages → chọn ngôn ngữ → danh sách → video + phụ đề
                                │
Admin → FastAPI/Render → Supabase (metadata, cue, trạng thái)
                    └→ Cloudflare R2 (MP4, WebP/JPG/PNG, VTT)
                    └→ Groq (chỉ tạo bản dịch nháp)
```

Người xem không đăng nhập. Chỉ admin dùng JWT. Video giữ nguyên âm thanh tiếng Việt, không có audio track, TTS, Redis worker hoặc FFmpeg mixing trong luồng MVP.

## Dữ liệu

- `videos`: media key, thời lượng, trạng thái và thông tin gốc để tương thích dữ liệu cũ.
- `video_translations`: tiêu đề/mô tả theo ngôn ngữ; duy nhất theo `(video_id, language_code)`.
- `video_languages`: object key và trạng thái của từng phụ đề.
- `subtitle_segments`: timestamp và nội dung từng cue để admin biên tập.
- `processing_jobs`: tiến độ/lỗi dịch nháp.
- Bảng audio cũ được giữ để migration không phá dữ liệu nhưng API mới không đọc/ghi bảng này.

Trạng thái phụ đề: `pending → processing → ready_for_review → completed`. Chỉ `completed` được tính là đã duyệt.

## Object key R2

```text
video/{video_id}/original.mp4
video/{video_id}/thumbnail.webp
video/{video_id}/subtitle/vi.vtt
video/{video_id}/subtitle/en.vtt
video/{video_id}/subtitle/ru.vtt
video/{video_id}/subtitle/zh.vtt
```

SRT upload tạm nằm dưới `video/{video_id}/upload/`. Trình duyệt xin presigned PUT URL và tải thẳng lên R2. Public API cấp signed GET URL trong hai giờ; tải lại trang sẽ nhận URL mới.

## API

Public:

- `GET /api/videos?lang=vi-VN`
- `GET /api/videos/{id}?lang=en-US`
- `GET /api/videos/{id}/subtitles/ru-RU.vtt`

Admin:

- đăng nhập, CRUD video nháp và nội dung đa ngôn ngữ;
- xin upload URL, xác nhận asset, đọc/sửa/duyệt cue;
- tạo hoặc tạo lại bản dịch nháp;
- publish/unpublish và QR PNG/SVG.

Publish bị chặn nếu thiếu MP4, thumbnail, tiêu đề của bốn ngôn ngữ hoặc bất kỳ phụ đề nào chưa được duyệt.

## Giới hạn bảo vệ tải xuống

Frontend dùng `controlsList="nodownload"` và chặn menu chuột phải. Đây chỉ là hạn chế giao diện; trình duyệt phải nhận dữ liệu để phát nên không thể ngăn sao chép tuyệt đối.
