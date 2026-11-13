# Hướng dẫn vận hành dự án Video Đa Ngôn Ngữ

File này là quy ước làm việc mặc định cho mọi agent và kỹ sư trong toàn bộ repository. Nếu một thư mục con có `AGENTS.md` riêng, file gần mã nguồn đang sửa hơn được ưu tiên trong phạm vi thư mục đó. Yêu cầu trực tiếp của người dùng luôn có độ ưu tiên cao hơn tài liệu này.

## 1. Mục tiêu sản phẩm

Đây là website giới thiệu hai nội dung video về di sản Ma nhai Ngũ Hành Sơn. Luồng công khai chuẩn là:

```text
QR chung → chọn ngôn ngữ → thư viện đúng hai chương → xem video → bật/tắt/đổi phụ đề
```

- Người xem không cần đăng nhập; chỉ khu vực admin yêu cầu xác thực.
- Bốn ngôn ngữ được hỗ trợ là `vi-VN`, `en-US`, `ru-RU`, `zh-CN`.
- Video luôn giữ âm thanh tiếng Việt gốc. Người xem đổi phụ đề trong lúc phát theo mô hình quen thuộc như YouTube; việc đổi phụ đề không được tải lại video hoặc làm mất vị trí phát.
- QR chung trỏ về route `/`. Nếu trình duyệt đã lưu một ngôn ngữ hợp lệ, ứng dụng có thể chuyển tiếp tới `/videos`; người dùng luôn phải có cách quay lại đổi ngôn ngữ.
- MVP không tạo audio lồng tiếng, không trộn audio, không dùng TTS và không yêu cầu tài khoản cho người xem.

### Hai slot nội dung cố định

Sản phẩm có đúng hai slot/chương công khai. Phần trình bày, thứ tự và nội dung biên tập của hai chương có thể được cấu hình riêng, nhưng media production phải do admin quản lý.

- Dùng một lớp ánh xạ rõ ràng và ổn định từ slot/slug công khai sang ID video trong production.
- Không giả định slug demo `hoi-an` và `ha-long` cũng là UUID của bản ghi production.
- Không rải ID hoặc slug của video ở nhiều component. Nguồn ánh xạ phải có một nơi sở hữu duy nhất và có fallback/error state rõ ràng khi chưa gắn media.
- Không tự động biến thư viện thành danh sách động nhiều video nếu chưa có yêu cầu thay đổi phạm vi sản phẩm.

## 2. Kiến trúc và hợp đồng hiện tại

### Thành phần

- `frontend/`: React, TypeScript và Vite; chứa public flow, trình phát và khu vực admin.
- `backend/`: FastAPI; cung cấp API public/admin, xác thực, kiểm tra media, xử lý SRT/VTT và điều phối dịch.
- Supabase: lưu metadata, bản dịch tiêu đề/mô tả, cue phụ đề và trạng thái xử lý.
- Cloudflare R2 hoặc storage adapter tương đương: lưu MP4, thumbnail và VTT; video lớn được tải trực tiếp bằng signed URL khi cấu hình cho phép.
- Groq: chỉ tạo bản dịch phụ đề nháp. Kết quả máy không được coi là nội dung đã duyệt.
- `supabase/migrations/`: lịch sử schema; không sửa migration đã chạy để thay thế cho migration mới.

Đọc `PROJECT_ARCHITECTURE.md` trước khi thay đổi data flow, storage, publish rule hoặc deployment.

### Route và mã ngôn ngữ là hợp đồng sản phẩm

Giữ tương thích với các route công khai sau, trừ khi người dùng yêu cầu migration rõ ràng:

- `/`: chọn ngôn ngữ.
- `/videos`: thư viện hai chương.
- `/videos/:id`: trang xem video và đổi phụ đề.

Các mã ngôn ngữ chuẩn là `vi-VN`, `en-US`, `ru-RU`, `zh-CN`. Không tạo alias không kiểm soát như `vn`, `cn` hoặc chỉ lưu `en` trong database. Tên file VTT rút gọn (`vi.vtt`, `en.vtt`, `ru.vtt`, `zh.vtt`) chỉ là chi tiết storage, không thay thế mã locale ở API hoặc model.

Khi sửa API, kiểm tra đồng thời type frontend, schema Pydantic, repository, migration và test. Không thay đổi wire shape hoặc publish rule âm thầm.

## 3. Quy tắc bắt buộc cho UI/UX

Mọi công việc làm thay đổi giao diện, bố cục, màu sắc, typography, interaction, responsive behavior hoặc accessibility phải đọc và áp dụng cả hai skill sau trước khi thiết kế hay sửa code:

1. `.agents/skills/apple-design/SKILL.md`
2. `.agents/skills/ui-ux-pro-max/SKILL.md`

Với `apple-design`, chỉ nạp các reference liên quan theo hướng dẫn của skill; với web, áp dụng các nguyên tắc nền tảng và accessibility, không sao chép máy móc convention chỉ dành cho native iOS/macOS. Với `ui-ux-pro-max`, dùng truy vấn nhỏ, đúng domain/stack và kiểm tra kết quả trước khi áp dụng.

### Tiêu chuẩn giao diện

- Thiết kế mobile-first và phải dùng tốt ở tối thiểu 375, 768, 1024 và 1440 CSS px; không có cuộn ngang ngoài ý muốn.
- Nội dung video là trọng tâm. Mỗi màn hình chỉ có một hành động chính nổi bật; trang trí không được cạnh tranh với video, tiêu đề hoặc lựa chọn ngôn ngữ.
- Giữ trải nghiệm trình phát quen thuộc: play/pause, seek, mute/unmute, fullscreen và menu phụ đề. Không tự động phát video có âm thanh.
- Mọi chức năng chính phải dùng được bằng bàn phím. Tab order theo thứ tự nhìn thấy; focus indicator luôn rõ; menu mở phải đóng được bằng `Escape` và trả focus hợp lý.
- Nút icon-only phải có accessible name. Trạng thái mở, chọn, bật/tắt phải được công bố bằng thuộc tính semantic phù hợp như `aria-expanded`, `aria-checked` hoặc `aria-pressed`.
- Mục tiêu chạm chính tối thiểu 44 × 44 CSS px và có khoảng cách đủ để tránh chạm nhầm. Không dựa vào hover cho thao tác thiết yếu.
- Văn bản thường đạt tương phản tối thiểu 4.5:1; chữ lớn và UI component đạt tối thiểu 3:1. Không dùng màu làm tín hiệu duy nhất.
- Body text trên mobile mặc định không nhỏ hơn 16 px. Layout phải chịu được zoom/text scaling 200% mà không mất chức năng hoặc che nội dung.
- Tôn trọng `prefers-reduced-motion`; animation chỉ dùng để giải thích quan hệ trạng thái, có thể ngắt và không chặn thao tác.
- Dùng semantic color/design token thay vì rải raw hex trong component. Mọi state hover, pressed, focus, disabled, loading và error phải rõ ở cả nền sáng và nền tối nếu theme đó được hỗ trợ.
- Không dùng emoji làm icon cấu trúc hoặc điều hướng. Dùng một bộ SVG/icon nhất quán; cờ ngôn ngữ chỉ là tín hiệu bổ trợ và luôn đi kèm tên ngôn ngữ bằng chữ.
- Ảnh có ý nghĩa cần alt text; ảnh trang trí dùng alt rỗng hoặc ẩn khỏi accessibility tree. Lỗi và trạng thái tải phải được screen reader nhận biết.
- Không chặn pinch-to-zoom. Không dùng `user-scalable=no` hoặc thủ thuật tương đương.

## 4. Media và phụ đề

### Đầu vào chuẩn

- Video: MP4 với video H.264 và audio AAC là baseline tương thích. Xác minh codec, độ phân giải, frame rate, thời lượng và dung lượng bằng `ffprobe` trước khi nhập.
- Phụ đề nguồn: SRT UTF-8, timestamp dạng `HH:MM:SS,mmm`, số thứ tự hợp lệ, `end > start`, không chồng cue và không có cue rỗng.
- Backend chuyển SRT sang WebVTT để trình duyệt phát. Không sửa timestamp trong quá trình dịch trừ khi người dùng yêu cầu biên tập timing.
- Tất cả bản dịch phải giữ nguyên số cue, thứ tự và timestamp của phụ đề nguồn. Kiểm tra đặc biệt tên riêng, niên đại, địa danh và số liệu.
- Mỗi video cần thumbnail, tiêu đề/mô tả cho bốn ngôn ngữ và bốn track phụ đề đã duyệt trước khi publish.
- `ready_for_review` không đồng nghĩa với đã duyệt; chỉ `completed` được tính là sẵn sàng xuất bản.

### Quy tắc an toàn nội dung

- Không tự ý copy file từ `Downloads` vào repository, upload lên storage, chạy dịch trả phí hoặc publish dữ liệu chỉ vì file đã xuất hiện trên máy.
- Không commit MP4 production, SRT khách hàng, token, signed URL, `.env` hoặc dữ liệu nhạy cảm nếu chưa có chỉ dẫn rõ ràng.
- Bản dịch máy luôn là bản nháp và phải được con người kiểm tra trước khi chuyển sang `completed`.
- `controlsList="nodownload"` và chặn menu chuột phải chỉ hạn chế giao diện; không tuyên bố đây là DRM hoặc ngăn sao chép tuyệt đối.

### Snapshot bàn giao — 11/11/2026

Đây là trạng thái đầu vào tại thời điểm lập tài liệu, không phải cấu hình vĩnh viễn:

- `/home/xiaoying/Downloads/VIDEO 2.mp4`: khoảng 415 MB; 1920 × 1080; H.264/AAC stereo; 24 fps; thời lượng `05:57.632`.
- `/home/xiaoying/Downloads/VIDEO 2.srt`: UTF-8; 106 cue; parser hiện tại đọc thành công; không cảnh báo, cue rỗng hoặc chồng thời gian; cue cuối kết thúc tại `05:55.904`.
- Khoảng trống 1.728 giây giữa cue cuối và cuối video là chấp nhận được, trừ khi kiểm duyệt nội dung phát hiện lời thoại bị thiếu.
- Video 1 và SRT tương ứng chưa xuất hiện trong bộ file được cung cấp. Không giả lập hoặc thay thế bằng media demo khi chưa được yêu cầu.

## 5. Workflow làm việc

### Trước khi sửa

1. Đọc file này, tài liệu kiến trúc và các file liên quan trực tiếp.
2. Chạy `git status --short`; coi mọi thay đổi có sẵn là của người dùng cho tới khi có bằng chứng khác.
3. Không hoàn nguyên, format lại hoặc ghi đè thay đổi không thuộc nhiệm vụ.
4. Nếu làm UI, đọc hai skill bắt buộc ở mục 3 và các reference cần thiết trước khi đề xuất giải pháp.
5. Xác định thay đổi có ảnh hưởng đến public route, locale, media ID mapping, publish rule hoặc schema hay không.

### Trong khi sửa

- Giữ diff nhỏ và đúng phạm vi; ưu tiên model/type hiện có thay vì tạo nguồn dữ liệu trùng lặp.
- Không hard-code secret, URL môi trường hoặc ID production trong component.
- Tránh inline style mới khi có thể dùng token/class dùng chung. Không refactor ngoài phạm vi chỉ để “dọn code”.
- Với tác vụ bất đồng bộ, hiển thị loading/progress, chặn submit lặp và cung cấp lỗi có cách khôi phục.
- Error message phải nói rõ vấn đề và hành động tiếp theo; không chỉ hiển thị “Có lỗi xảy ra”.
- Khi thay đổi behavior, thêm hoặc cập nhật test ở lớp gần nguyên nhân nhất.

### Sau khi sửa

1. Xem lại `git diff --check` và `git diff --stat`.
2. Chạy bộ kiểm tra phù hợp với phạm vi thay đổi.
3. Kiểm tra thủ công luồng liên quan trên kích thước mobile và desktop nếu có thay đổi UI.
4. Báo rõ test đã chạy, test chưa chạy và mọi rủi ro còn lại. Không tuyên bố hoàn thành khi chỉ kiểm tra bằng mắt.

## 6. Lệnh phát triển và kiểm tra

Chạy lệnh từ đúng thư mục được nêu; không chạy formatter có chế độ ghi trên toàn repository nếu nhiệm vụ không yêu cầu.

### Frontend

```bash
cd frontend
npm install
npm run dev
npm run build
```

`npm run build` là kiểm tra tối thiểu cho mọi thay đổi TypeScript/React/CSS. `package.json` hiện chưa định nghĩa test runner hoặc lint script; không bịa lệnh kiểm tra không tồn tại.

### Backend

```bash
cd backend
python -m pytest
```

Ưu tiên chạy test hẹp trước, sau đó toàn bộ suite khi thay đổi có ảnh hưởng rộng:

```bash
cd backend
python -m pytest tests/test_subtitle.py tests/test_subtitle_only_admin.py
python -m pytest tests/test_media_security.py tests/test_health.py
python -m pytest
```

Test integration cần API key hoặc dịch vụ ngoài phải tiếp tục được đánh dấu/skip rõ ràng; không dùng credential production để làm test mặc định.

### Kiểm tra media mẫu

```bash
ffprobe -v error -show_streams -show_format "/duong-dan/video.mp4"
```

Phụ đề phải được kiểm tra bằng parser và validator trong `backend/app/services/subtitle/`, không chỉ nhìn vài cue đầu/cuối.

## 7. Kịch bản nghiệm thu bắt buộc

### Public flow

- Quét QR chung mở đúng `/` trên domain public.
- Người dùng mới thấy đủ bốn lựa chọn ngôn ngữ; lựa chọn được lưu và có thể thay đổi sau đó.
- `/videos` luôn thể hiện đúng hai chương theo đúng thứ tự, kể cả khi một slot chưa có media; trạng thái thiếu dữ liệu phải rõ ràng.
- Mỗi chương mở đúng video production được ánh xạ, không phụ thuộc slug demo trùng UUID.
- Video không autoplay; play/pause, seek, mute, fullscreen và menu phụ đề hoạt động bằng chuột, cảm ứng và bàn phím.
- Có thể tắt phụ đề hoặc đổi giữa Việt/Anh/Nga/Trung mà không reset thời gian phát.
- Refresh, back navigation và đổi ngôn ngữ không làm mất trạng thái theo cách bất ngờ.

### Admin và publish

- Upload MP4 lớn đi đúng signed-upload flow khi storage hỗ trợ và có progress/error feedback.
- SRT sai encoding/cấu trúc, cue chồng nhau hoặc file vượt giới hạn bị từ chối với lỗi có thể xử lý.
- Không publish nếu thiếu video, thumbnail, tiêu đề bất kỳ ngôn ngữ nào hoặc có track chưa `completed`.
- Preview dùng đúng media và phụ đề chưa public; public API chỉ trả video đã publish.
- QR tải được cả PNG và SVG và chứa đúng public base URL.

### Accessibility và responsive

- Không có lỗi keyboard trap; focus luôn nhìn thấy và không bị sticky UI che khuất.
- Screen reader đọc đúng tên nút, ngôn ngữ, trạng thái phụ đề và lỗi.
- Giao diện vẫn dùng được ở 375 px, landscape mobile, desktop và zoom 200%.
- Reduced motion không làm mất nội dung hoặc trạng thái.

## 8. Định nghĩa hoàn thành

### Thay đổi UI

- Đã áp dụng cả hai skill bắt buộc và ghi nhận quyết định thiết kế quan trọng.
- Build frontend thành công; kiểm tra responsive, keyboard, focus, screen reader semantics và reduced motion cho luồng bị ảnh hưởng.
- Không làm thay đổi public flow hoặc hai-slot mapping ngoài yêu cầu.

### Thay đổi backend/schema

- Schema/type/API/repository đồng bộ, có migration mới nếu cần và có test regression.
- Test backend liên quan và toàn bộ suite phù hợp đã chạy; lỗi storage/translation không làm lộ secret hoặc publish dữ liệu dở dang.

### Nhập media/nội dung

- Video đã qua `ffprobe`; SRT đã qua parser/validator; thumbnail và metadata đủ bốn ngôn ngữ.
- Bốn track có cùng cue/timestamp, đã được người phụ trách nội dung duyệt và có thể đổi trong player.
- Hai slot trỏ đúng ID production; QR và public flow đã được kiểm tra trên deployment đích.

### Bàn giao

- Diff chỉ chứa thay đổi thuộc nhiệm vụ, không ghi đè công việc có sẵn của người dùng.
- Không có secret hoặc media khách hàng bị commit ngoài ý muốn.
- Báo cáo cuối nêu file đã đổi, test đã chạy, giới hạn và bước vận hành thủ công còn lại.
