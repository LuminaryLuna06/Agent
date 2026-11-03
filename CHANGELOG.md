# Changelog

Mọi thay đổi đáng chú ý của dự án **Shorekeeper Agent** được ghi lại trong file này.

Định dạng dựa trên [Keep a Changelog](https://keepachangelog.com/vi/1.1.0/),
và dự án tuân theo [Semantic Versioning](https://semver.org/lang/vi/).

## [Unreleased]

### Added
- Hàm `update_state` trong repository quản lý upsert trạng thái runtime và tự động cập nhật `last_message_ts` sau mỗi lượt hội thoại.
- Bộ kiểm thử tiêu chí Stage 1 (`tests/e2e/test_stage1_criteria.py`) thẩm định tính dễ đọc của tick log, chuỗi suy nghĩ và độ đa dạng phản hồi.
- Bộ kiểm thử tích hợp (integration tests) cho hàm cập nhật trạng thái cơ sở dữ liệu (`TestUpdateState`).

### Changed
- Cải tiến trường `updated_at` của bảng `state` sang kiểu số thực (UNIX timestamp float) với cơ chế tự động cập nhật thời gian (`onupdate=time.time`) đồng nhất với bảng `messages` và `tick_log`.

## [0.3.0] - 2026-10-30

### Added
- Bộ kiểm thử tự động toàn diện:
  - **Unit tests:** Kiểm tra cấu hình môi trường, thuật toán tạo prompt và cơ chế tính toán ngân sách token.
  - **Integration tests:** Kiểm tra tính toàn vẹn khi lưu trữ tin nhắn/tick log và giao tiếp HTTP với server suy luận.
  - **End-to-End tests:** Giả lập trọn vẹn chu kỳ một lượt hội thoại của Agent (`ShorekeeperAgent.step`).
- Thiết lập môi trường test cô lập với SQLite In-Memory fixture trong `tests/conftest.py`.
- Tập trung hóa cấu hình kiểm thử với `pytest.ini`.

### Fixed
- Bổ sung cơ chế xác thực và trích xuất phòng thủ (defensive parsing) dữ liệu phản hồi từ backend LLM, loại bỏ nguy cơ crash ứng dụng khi nhận payload dị thường hoặc thiếu trường.

### Changed
- Cập nhật và tối ưu hóa file `.gitignore` cho môi trường macOS, VSCode/Cursor và công cụ agentic.

## [0.2.0] - 2026-10-28

### Added
- Tài liệu hướng dẫn dự án `README.md` bao gồm thông tin Tech Stack, cấu trúc thư mục và hướng dẫn khởi chạy nhanh.

### Changed
- Tái cấu trúc (Modularize) toàn bộ mã nguồn từ tệp notebook đơn lẻ (`main.ipynb`) thành kiến trúc gói mô-đun hướng tên miền (`src/agent`, `src/config`, `src/db`, `src/llm`, `src/prompts`, `src/tokens`).
- Chuẩn hóa quản lý cấu hình và tham số môi trường thông qua Pydantic Settings.

## [0.1.0] - 2026-10-27

### Added
- Tích hợp SQLite với SQLAlchemy 2.0 ORM:
  - Bảng `messages`: Lưu trữ vĩnh viễn toàn bộ lịch sử trò chuyện.
  - Bảng `state`: Lưu giữ các trạng thái đồng hành theo thời gian thực.
  - Bảng `tick_log`: Lưu vết toàn bộ prompt, thinking chain và tham số suy luận của từng tick phục vụ việc debug/replay.
- Cơ chế quản lý token linh hoạt (`dynamic_budget`) và thuật toán cắt tỉa lịch sử ưu tiên tin mới nhất (`fit_newest_first`).
- Thiết lập Persona Shorekeeper kèm các mỏ neo giọng điệu (voice anchors) giúp duy trì phong thái nhân vật ổn định.
- Vòng lặp hội thoại tương tác tại terminal thông qua `main.py`.

## [0.0.1] - 2026-10-26

### Added
- Bản thử nghiệm sơ khởi kết nối gọi suy luận văn bản tự do qua mô hình ngôn ngữ lớn (LLM).
- Khởi tạo repository và file cấu hình git cơ bản.

[Unreleased]: https://github.com/LuminaryLuna06/Agent/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/LuminaryLuna06/Agent/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/LuminaryLuna06/Agent/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/LuminaryLuna06/Agent/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/LuminaryLuna06/Agent/releases/tag/v0.0.1
