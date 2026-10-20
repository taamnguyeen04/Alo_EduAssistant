# Alo_EduAssistant — Trợ lí AI học tập (môn đầu tiên có dữ liệu: Toán 11)

## Chạy thử (2 phút)

```bash
pip install -r requirements.txt
# tạo file .env chứa OPENROUTER_API_KEY (xem core/llm.py để biết tên biến)
python tools/seed_demo.py
streamlit run app.py
```

Tài khoản thử (đã seed sẵn, vai **Học sinh**): `hs_001` (yếu), `hs_002` (khá),
`hs_003` (giỏi). Vai **Giáo viên** vào thẳng không cần mã.

Kịch bản demo 6 phút: xem `DEMO.md`.

## Nó làm gì (3 lõi)

1. **Chat Socrates theo sức học** — không mớm đáp án, hỏi ngược từng nấc theo
   trình độ yếu/khá/giỏi, công thức chuẩn LaTeX, gợi ý đúng 1 video trong kho.
2. **Luyện tập thích ứng từ kho GV** — ưu tiên câu trong kho (ghi rõ nguồn),
   hết mới sinh bù (gắn cờ chờ duyệt); chấm **từng bước**, sai thì gợi ý sửa,
   câu sau tự tăng/giảm độ khó; xin "hướng dẫn" thì chỉ gợi mở bước 1.
3. **Điểm yếu tự gom cho GV** — mỗi lượt chat/bài luyện đều ghi điểm yếu,
   trình độ tự lên/xuống theo 5 bài gần nhất; GV bấm **Tổng hợp** ra báo cáo
   theo Bài + duyệt câu chờ + giao bài + quản lý lớp.

## Dữ liệu có sẵn

- **Kho đề** (`data/bank/`, 1070 câu): Bài 1 (166), Bài 2 (157), Bài 3 (201),
  Bài 4 (156) lượng giác + Bài 31 (130), Bài 32 (178), Bài 33 (82) đạo hàm.
  Trích từ PDF, kiểm tra chất lượng bằng `tools/loc_bank.py`
  (`chat_luong: ok / can_duyet` + lý do).
- **Video** (`data/video_data.json`, 12 bài): Chương I lượng giác (Bài 1–4),
  Chương II dãy số/cấp số (Bài 5–7), Chương III thống kê ghép nhóm (Bài 8–9),
  Chương IV quan hệ song song (Bài 10–12).
- **Wiki tri thức** (`data/wiki/`, mở bằng Obsidian): mục lục `index.md`,
  trang khái niệm liên kết `[[...]]`, cụm dạng bài, nhật ký `log.md`.
  Quy ước vận hành: `AGENTS.md`.

## Cấu trúc code

- `app.py` — Streamlit, cổng đăng nhập 2 vai trò.
- `core/` — `student.py` (chat), `grading.py` (chấm), `exercises.py` (ra bài),
  `teacher.py` (báo cáo), `knowledge.py` (truy xuất kho), `curriculum.py` (video),
  `conversations.py` (nhiều đoạn chat), `lop.py` (lớp/giao bài/nhóm),
  `visuals.py` (Plotly) + `visuals/` (render video Manim).
- `ui/` — màn hình HS (Tổng quan, Chat, Chương, Luyện tập, Hồ sơ) và
  GV (Báo cáo, Kho đề, Soạn bài trực quan, Giao bài, Học liệu, Lớp học).
- `tools/` — `ingest_pdf.py`, `fix_bank.py`, `loc_bank.py`, `export_wiki.py`,
  `seed_demo.py`, bộ `kiem_tra_*.py`.

## Lưu ý

- Key API để trong `.env`, không commit (xem `.gitignore`). File `test.py`
  cũng đọc key từ `.env`.
- Câu AI sinh luôn gắn cờ chờ duyệt — GV duyệt ở tab Kho đề trước khi vào kho chính.
