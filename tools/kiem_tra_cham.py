import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.grading import lam_sach_goi_y, tach_json_cham

# 1. Đúng mẫu rò rỉ trong ảnh chụp: JSON lẫn câu chữ, không fence
raw = ('rung gian, cụ thể là tính riêng $\\sin(\\pi/6) = 1/2$ và $\\cos(\\pi/3) = 1/2$ '
       'trước khi ghi tổng kết quả.", "diem_yeu_moi": ["thiếu các bước tính toán trung gian"]}')
sach = lam_sach_goi_y(raw)
assert "diem_yeu_moi" not in sach, sach
assert "{" not in sach and "}" not in sach, sach
assert "sin" in sach, sach  # giữ lại gợi ý, chỉ xóa JSON
print("PASS loc-json-ro-ri:", sach[:80])

# 2. JSON không fence vẫn tách được
raw2 = 'Nhận xét xong.\n{"dung_sai_tung_buoc": [true, false], "sai_o_buoc": 2, "goi_y_sua": "xem lại bước 2", "diem_yeu_moi": []}'
chat, data = tach_json_cham(raw2)
assert data.get("sai_o_buoc") == 2, data
assert "```" not in chat
print("PASS tach-khong-fence")

# 3. Fence chuẩn vẫn chạy như cũ
raw3 = 'Ổn.\n```json\n{"dung_sai_tung_buoc": [true, true], "sai_o_buoc": null, "goi_y_sua": "tốt", "diem_yeu_moi": []}\n```'
_, data3 = tach_json_cham(raw3)
assert data3.get("dung_sai_tung_buoc") == [True, True], data3
print("PASS tach-co-fence")
print("THAT BAI: khong")
