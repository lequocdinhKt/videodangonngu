# Cài đặt và triển khai

## 1. Thu hồi khóa cũ

Nếu bất kỳ khóa Supabase, R2 hoặc Groq nào từng xuất hiện trong `.env.example` hay Git, hãy revoke/rotate trước khi deploy. File mẫu hiện chỉ chứa placeholder. Không đặt secret vào frontend hoặc biến bắt đầu bằng `VITE_`.

## 2. Supabase

1. Tạo project Free, ưu tiên region Singapore.
2. Mở SQL Editor, chạy lần lượt:
   - `supabase/migrations/001_initial_schema.sql`
   - `supabase/migrations/002_subtitle_only_localization.sql`
3. Lấy Project URL và `service_role` key cho backend.
4. Không cần tạo Supabase Storage bucket; media dùng R2.

## 3. Cloudflare R2

1. Tạo bucket, ví dụ `video-assets`.
2. Tạo S3 API token giới hạn vào bucket đó.
3. Ghi lại endpoint, Access Key ID và Secret Access Key.
4. Cấu hình CORS cho bucket, thay domain Pages thật:

```json
[
  {
    "AllowedOrigins": ["https://your-site.pages.dev", "http://localhost:5173"],
    "AllowedMethods": ["GET", "PUT", "HEAD"],
    "AllowedHeaders": ["Content-Type"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

Media không đưa vào Git. Upload admin ghi vào các object key cố định dưới `video/{id}/`.

## 4. Groq

Tạo API key và đặt `TRANSLATION_PROVIDER=groq`, `GROQ_API_KEY=...`. Đây là tùy chọn: không có key thì vẫn upload bốn SRT thủ công. Khi gặp 429, admin sẽ thấy thông báo thử lại hoặc dùng SRT thủ công.

## 5. Render Free cho FastAPI

Repository đã có `render.yaml` và Dockerfile. Trong Render:

1. New → Blueprint, chọn repository.
2. Điền các biến `sync: false` theo `.env.example`.
3. Đặt thêm:
   - `PUBLIC_BASE_URL=https://your-site.pages.dev`
   - `CORS_ORIGINS=https://your-site.pages.dev,http://localhost:5173`
   - `STORAGE_PROVIDER=r2`
4. Deploy và kiểm tra `https://your-api.onrender.com/api/health`.

Render Free có thể ngủ sau thời gian không hoạt động; frontend đã có trạng thái “Máy chủ đang khởi động” và nút thử lại.

## 6. Cloudflare Pages cho frontend

1. Workers & Pages → Create → Pages → kết nối repository.
2. Root directory: `frontend`.
3. Build command: `npm run build`.
4. Output directory: `dist`.
5. Environment variable: `VITE_API_URL=https://your-api.onrender.com`.
6. Deploy. File `public/_redirects` đã cấu hình fallback cho React Router.

Sau khi có URL Pages cuối cùng, cập nhật `PUBLIC_BASE_URL` và `CORS_ORIGINS` trên Render rồi redeploy. QR sinh từ `PUBLIC_BASE_URL`; URL gốc Pages vẫn dùng được nếu sau này thêm domain riêng.

## 7. Cấu hình bắt buộc của backend

```env
ENV=production
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
STORAGE_PROVIDER=r2
S3_BUCKET=video-assets
S3_ENDPOINT=https://ACCOUNT_ID.r2.cloudflarestorage.com
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
SIGNED_URL_EXPIRES_SECONDS=7200
JWT_SECRET=<chuỗi ngẫu nhiên dài>
ADMIN_EMAIL=<email thật>
ADMIN_PASSWORD=<mật khẩu mạnh>
GROQ_API_KEY=<tùy chọn>
PUBLIC_BASE_URL=https://your-site.pages.dev
CORS_ORIGINS=https://your-site.pages.dev,http://localhost:5173
```

Production sẽ từ chối khởi động nếu còn JWT hoặc mật khẩu placeholder.

## 8. Kiểm tra nghiệm thu

1. Admin đăng nhập và tạo video mới.
2. Upload MP4, thumbnail và SRT Việt.
3. Tạo bản dịch nháp hoặc upload SRT EN/RU/ZH.
4. Sửa ít nhất một cue, lưu và duyệt đủ bốn ngôn ngữ.
5. Publish, tải QR PNG/SVG và quét bằng Android/iPhone.
6. Kiểm tra đổi ngôn ngữ, bật/tắt/đổi phụ đề, toàn màn hình và tải lại sau khi signed URL hết hạn.
7. Thử file sai định dạng, video quá dung lượng và trạng thái Groq rate-limit.

Lưu ý: Render/R2/Supabase/Groq cần tài khoản và secret của chủ dự án nên không thể triển khai công khai chỉ bằng source code local.
