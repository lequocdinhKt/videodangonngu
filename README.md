# Video Guide

Website xem video văn hóa/du lịch Việt Nam qua một mã QR chung. Người xem không cần tài khoản: chọn tiếng Việt, Anh, Nga hoặc Trung giản thể rồi xem video với tiêu đề, mô tả và phụ đề tương ứng. Âm thanh luôn là âm thanh gốc tiếng Việt; dự án không tạo hoặc chọn thuyết minh.

## Chức năng chính

- Giao diện sáng, mobile-first; lần đầu chọn ngôn ngữ và lưu bằng `localStorage`.
- Danh sách video dạng thẻ và trình phát 16:9 có bật/tắt, đổi phụ đề và toàn màn hình.
- Admin tạo nháp, nhập nội dung bốn ngôn ngữ, tải MP4/thumbnail/SRT, sửa từng cue, duyệt và xuất bản.
- Groq chỉ tạo bản dịch phụ đề nháp. Upload SRT thủ công luôn sử dụng được.
- QR chung chứa URL website, có bản PNG và SVG.
- Supabase lưu dữ liệu, Cloudflare R2 lưu media, Cloudflare Pages chạy frontend, Render chạy FastAPI.

## Chạy local

```powershell
Copy-Item .env.example backend/.env
# Điền Supabase và tài khoản admin trong backend/.env

cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# terminal khác
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

- Người xem: http://localhost:5173
- Admin: http://localhost:5173/admin/login
- API health: http://localhost:8000/api/health

Không có mật khẩu admin mặc định dùng được. Hãy đặt `ADMIN_EMAIL`, `ADMIN_PASSWORD` và `JWT_SECRET` trong `backend/.env`.

## Kiểm thử

```powershell
cd frontend
npm run build

cd ..\backend
pytest -q
```

Xem [SETUP_DEPLOY.md](SETUP_DEPLOY.md) để cấu hình Supabase, R2, Render, Pages và CORS.
