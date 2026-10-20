# LLM Wiki Toán 11 — Chương 1

Bộ ingest này được xây dựng từ 4 file bài học chi tiết và 1 file chương tổng hợp. Mục tiêu là **bảo toàn nguồn trước, chuẩn hóa sau**: công thức MathType/OLE không bị bỏ qua như khi chỉ đọc `paragraph.text`, mà được render từ preview gốc thành SVG; câu hỏi, đáp án và lời giải được lưu theo JSON; lớp wiki có LaTeX cốt lõi để truy hồi/hiển thị thuận tiện.

## Kết quả hiện tại

- 4 bài học, 34 knowledge units.
- 497 câu hỏi được tách từ phần rèn luyện.
- Các file câu hỏi: `questions/C1_B1.json` … `C1_B4.json`.
- Nội dung nguồn đầy đủ: `source_md/`.
- Lớp tri thức gọn, có LaTeX: `wiki/`.
- Kiểm tra chất lượng: `qa/` (lint + deep integrity + review queue + hướng dẫn giáo viên).
- JSON Schema chính thức: `questions/question.schema.json`.
- Helper Streamlit: `tools/streamlit_adapter.py` (hỗ trợ cả Markdown image và HTML `<img>` trỏ đến SVG nguồn).

Bắt đầu từ [index.md](index.md).
