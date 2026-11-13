<!--
Sync Impact Report
- Version change: template (unratified) → 1.0.0
- Modified principles:
  - Template Principle 1 → I. Trung thực với nội dung gốc
  - Template Principle 2 → II. Bản dịch là bản nháp cho đến khi được duyệt
  - Template Principle 3 → III. Bảo mật theo ranh giới tin cậy
  - Template Principle 4 → IV. Toàn vẹn hợp đồng và dữ liệu
  - Template Principle 5 → V. Thay đổi phải được kiểm chứng
- Added sections:
  - Ràng buộc kiến trúc và vận hành
  - Quy trình phát triển và cổng chất lượng
- Removed sections: none
- Follow-up TODOs: none
-->
# Video Guide Constitution

## Core Principles

### I. Trung thực với nội dung gốc
Mỗi video MUST giữ nguyên hình ảnh và âm thanh tiếng Việt của tài sản nguồn. Việc bản địa hóa
MUST chỉ thay đổi tiêu đề, mô tả và phụ đề cho bốn locale `vi-VN`, `en-US`, `ru-RU` và `zh-CN`.
Luồng MVP MUST NOT tạo, trộn, chọn hoặc phát thuyết minh/TTS thay cho âm thanh gốc. Mọi đề xuất
thay đổi ranh giới này MUST được phê chuẩn bằng một sửa đổi hiến pháp trước khi lập kế hoạch.
Nguyên tắc này bảo vệ tính xác thực của nội dung văn hóa và ngăn phạm vi sản phẩm trôi dạt.

### II. Bản dịch là bản nháp cho đến khi được duyệt
Bản dịch do Groq hoặc bất kỳ nhà cung cấp AI nào tạo ra MUST được lưu như bản nháp và MUST NOT
được xuất bản tự động. Quản trị viên MUST có thể xem, sửa và duyệt từng phụ đề; tải SRT thủ công
MUST luôn là một đường lui khả dụng. Một video chỉ được publish khi có MP4, thumbnail, tiêu đề cho
cả bốn locale và mọi phụ đề đều ở trạng thái `completed`. Trạng thái nghiệp vụ MUST tuân theo
`pending → processing → ready_for_review → completed`, trừ khi migration và đặc tả đã phê chuẩn
một thay đổi tương thích.

### III. Bảo mật theo ranh giới tin cậy
Người xem công khai MUST không cần tài khoản và MUST chỉ truy cập nội dung đã publish. Mọi thao
tác quản trị MUST yêu cầu xác thực JWT và kiểm tra quyền ở backend. Secret, service-role key,
khóa R2/Groq và thông tin quản trị MUST NOT xuất hiện trong frontend, Git hoặc phản hồi API.
Media riêng tư MUST được truy cập qua URL ký có thời hạn; upload MUST dùng đường dẫn/object key
được backend cấp và phải kiểm tra loại, kích thước cùng quyền sở hữu. Production MUST từ chối
khởi động khi còn secret hoặc mật khẩu mặc định không an toàn.

### IV. Toàn vẹn hợp đồng và dữ liệu
API công khai, schema database và quy ước object key là các hợp đồng tương thích. Thay đổi schema
MUST đi qua migration có thể review; không được sửa production schema bằng thao tác thủ công
không được ghi nhận. Các ràng buộc duy nhất, khóa ngoại, trạng thái publish và quan hệ giữa video,
locale, cue phụ đề MUST được bảo toàn ở database hoặc repository layer. Thay đổi API MUST giữ
tương thích ngược hoặc ghi rõ migration path và tác động đến frontend. Supabase giữ metadata;
Cloudflare R2 giữ media; code MUST không làm rò rỉ chi tiết storage vào domain contract.

### V. Thay đổi phải được kiểm chứng
Mọi thay đổi hành vi MUST có test tự động phù hợp ở backend và/hoặc frontend. Trước khi merge,
backend MUST vượt qua `pytest -q` và frontend MUST vượt qua `npm run build`; thay đổi liên quan
API, storage, xác thực, publish hoặc migration MUST có test tích hợp hoặc test contract tương ứng.
Các trường hợp chưa thể kiểm thử tự động MUST được ghi rõ bằng bằng chứng kiểm tra thủ công và lý
do. Log backend MUST đủ ngữ cảnh để chẩn đoán lỗi nhưng MUST NOT chứa secret hoặc dữ liệu nhạy cảm.

## Ràng buộc kiến trúc và vận hành

- Frontend MUST tiếp tục dùng React, TypeScript và Vite theo cấu trúc hiện tại; giao diện công khai
  MUST mobile-first và hoạt động tốt trên màn hình nhỏ.
- Backend MUST tiếp tục dùng FastAPI và Pydantic; route xử lý HTTP, còn nghiệp vụ và tích hợp bên
  ngoài MUST nằm trong service/repository phù hợp.
- Supabase PostgreSQL là nguồn dữ liệu chuẩn. Cloudflare R2 là nơi lưu MP4, thumbnail và VTT trong
  production; tài sản media lớn MUST NOT được commit vào Git.
- Object key chuẩn MUST nằm dưới `video/{video_id}/`; thay đổi cấu trúc key MUST có chiến lược
  tương thích hoặc migration tài sản.
- Groq chỉ là nhà cung cấp tạo bản dịch nháp. Hệ thống MUST vẫn hoạt động với upload SRT thủ công
  khi AI không khả dụng, hết quota hoặc trả lỗi.
- CORS, public URL, nhà cung cấp storage và mọi credential MUST được cấu hình qua environment.
- Cơ chế giao diện như `controlsList="nodownload"` MUST NOT được mô tả như biện pháp chống sao chép
  tuyệt đối; bảo mật MUST dựa trên kiểm soát truy cập và URL ký ở backend.

## Quy trình phát triển và cổng chất lượng

1. Mỗi thay đổi có phạm vi đáng kể MUST bắt đầu bằng một `spec.md` nêu kết quả, tiêu chí chấp nhận
   và các hành vi hiện có phải giữ nguyên.
2. `plan.md` MUST xác định tác động tới frontend, backend, API, database, storage, bảo mật và vận
   hành. Quyết định làm tăng độ phức tạp MUST có lý do và phương án đơn giản hơn đã cân nhắc.
3. `tasks.md` MUST sắp xếp migration và hợp đồng trước các consumer phụ thuộc, đồng thời bao gồm
   test, tài liệu vận hành và bước xác minh.
4. Trước khi implement, đặc tả, kế hoạch và task MUST không còn mâu thuẫn nghiêm trọng. Các câu hỏi
   ảnh hưởng dữ liệu, bảo mật hoặc hành vi publish MUST được làm rõ trước khi viết code.
5. Review MUST kiểm tra hiến pháp, diff, migration, secret, test và khả năng rollback. Không được
   merge khi cổng build/test bắt buộc thất bại hoặc chưa chạy mà không có ngoại lệ được ghi nhận.
6. Sau implement, `$speckit-converge` MUST được dùng cho thay đổi được quản lý bằng Spec Kit; mọi
   khoảng trống phát hiện được MUST quay lại `tasks.md` trước khi xem tính năng là hoàn tất.

## Governance

Hiến pháp này là nguồn quy tắc cao nhất cho đặc tả, kế hoạch và review trong repository. Khi tài
liệu hoặc thói quen hiện có mâu thuẫn với hiến pháp, hiến pháp được ưu tiên cho công việc mới và
phải tạo kế hoạch migration cho hành vi cũ.

Mọi sửa đổi MUST nêu lý do, tác động tới nguyên tắc, yêu cầu migration và phiên bản đề xuất. Chủ
dự án phê chuẩn sửa đổi qua review Git. Phiên bản dùng Semantic Versioning: MAJOR khi loại bỏ hoặc
định nghĩa lại nguyên tắc theo cách không tương thích; MINOR khi thêm nguyên tắc/section hoặc mở
rộng nghĩa vụ; PATCH khi chỉ làm rõ câu chữ mà không thay đổi yêu cầu.

Mỗi spec, plan và code review MUST kiểm tra tuân thủ các nguyên tắc liên quan. Ngoại lệ tạm thời
MUST được ghi trong artifact của feature với người chịu trách nhiệm, lý do, rủi ro và ngày hết hạn.
Sync Impact Report ở đầu file là tài liệu review tạm thời và MUST được xóa trước khi commit sau khi
người review xác nhận thay đổi.

**Version**: 1.0.0 | **Ratified**: 2026-11-05 | **Last Amended**: 2026-11-05
