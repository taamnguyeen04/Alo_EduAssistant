"""Kiểm tra đường template-first: match -> slot -> render -> cache -> fallback."""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import manim_template as tpl
from core import manim_ai

# 1. Match đường tròn lượng giác + trích góc
muc, diem = tpl.chon_template("Minh họa điểm M(cos α; sin α) trên đường tròn lượng giác với góc 60 độ")
assert muc and muc["template_id"] == "LTG_01_unit_circle", (muc, diem)
params = tpl.dien_slot("Minh họa điểm M trên đường tròn lượng giác với góc 60 độ", muc)
assert params["angle_deg"] == 60, params
print("PASS match LTG_01 + goc 60 (diem %.1f)" % diem)

# 2. Match cát tuyến/tiếp tuyến + trích hàm
muc2, diem2 = tpl.chon_template("Cho Q tiến về P để cát tuyến thành tiếp tuyến, hàm x^2 tại a = 1")
assert muc2 and muc2["template_id"] == "DH_01_secant_to_tangent", (muc2, diem2)
params2 = tpl.dien_slot("Cho Q tiến về P để cát tuyến thành tiếp tuyến, hàm x^2 tại a = 1", muc2)
assert params2["function"] == "x^2", params2
print("PASS match DH_01 + ham x^2 (diem %.1f)" % diem2)

# 3. Mô tả ngoài phủ -> None (không cố dùng template sai)
muc3, _ = tpl.chon_template("Quang hợp ở lá cây tạo tinh bột")
assert muc3 is None, muc3
print("PASS mo ta la -> khong match")

# 4. not_for chặn: giải PT nhiều nghiệm dù có chữ "đường tròn"
muc4, d4 = tpl.chon_template("Giải phương trình lượng giác nhiều nghiệm trên đường tròn")
assert muc4 is None, (muc4, d4)
print("PASS not_for chan template sai")

# 5. Kẹp slot theo manifest (góc 1000 -> 720)
muc5, _ = tpl.chon_template("đường tròn lượng giác minh họa sin cos")
p5 = tpl.dien_slot("đường tròn lượng giác góc 1000 độ minh họa sin cos", muc5)
assert p5["angle_deg"] == 720, p5
print("PASS kep slot goc 1000 -> 720")

# 6. Render thật template + cache lần 2
kq = tpl.render_template("LTG_01_unit_circle", {"angle_deg": 60, "show_numeric": True,
                         "show_radius_label": True, "show_final_summary": True,
                         "duration_scale": 1.0}, quality="l", timeout=600)
assert kq["mp4"] and os.path.getsize(kq["mp4"]) > 50000, kq["log"][-300:]
print("PASS render template that:", os.path.basename(kq["mp4"]), os.path.getsize(kq["mp4"]), "bytes")
kq2 = tpl.render_template("LTG_01_unit_circle", {"angle_deg": 60, "show_numeric": True,
                          "show_radius_label": True, "show_final_summary": True,
                          "duration_scale": 1.0}, quality="l", timeout=600)
assert kq2["cached"] and kq2["mp4"] == kq["mp4"], kq2
print("PASS cache template lan 2")

# 7. End-to-end qua pipeline (không tốn token LLM): mô tả khớp -> ra mp4 template
kq3 = manim_ai.sinh_video_tu_mo_ta(
    "Minh họa điểm M(cos α; sin α) trên đường tròn lượng giác với góc 60 độ, hiện giá trị số",
    bai="Bài 1", quality="l", timeout=600)
assert kq3.get("template") == "LTG_01_unit_circle", kq3.get("log", "")[-300:]
assert kq3["mp4"] and os.path.exists(kq3["mp4"]), kq3.get("log", "")[-300:]
print("PASS end-to-end template-first:", os.path.basename(kq3["mp4"]))
print("THAT BAI: khong")
