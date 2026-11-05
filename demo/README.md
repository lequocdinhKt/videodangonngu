# Dữ liệu demo tự tạo

Bốn clip minh họa (Hội An, Hạ Long, cà phê Việt và chợ nổi) được sinh hoàn toàn bằng hình học/lập trình trong repository này. Không dùng ảnh, video hoặc nhạc của bên thứ ba.

```powershell
pip install -r demo/requirements.txt
python demo/generate_demo_assets.py

$env:DEMO_API_URL="http://localhost:8000"
$env:DEMO_ADMIN_EMAIL="admin@example.com"
$env:DEMO_ADMIN_PASSWORD="your-password"
python demo/seed_demo.py
```

Tệp sinh ra nằm trong `demo_assets/` và được sao chép sang `frontend/public/demo/`; cả hai đã được `.gitignore` loại khỏi Git. Để duyệt giao diện mà chưa cấu hình backend, copy `frontend/.env.demo.example` thành `frontend/.env` rồi chạy frontend. Script seed dùng đúng API upload/publish thật nên có thể chạy với local hoặc URL Render.
