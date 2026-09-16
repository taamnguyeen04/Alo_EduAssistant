import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from visuals.render import render, validate

# 1. Param bẩn bị chặn trước khi render (NaN/vô cực thì kẹp về default, không crash)
for preset, params in [
    ("preset-la", {}),
    ("do_thi", {"func": "eval"}),
    ("tiep_tuyen", {"expr": "__import__('os')", "a": 1}),
]:
    try:
        validate(preset, params)
        raise SystemExit(f"FAIL: lọt param bẩn {preset} {params}")
    except ValueError:
        pass
assert validate("duong_tron", {"angle_deg": float("nan")}) == {"angle_deg": 30}
assert validate("duong_tron", {"angle_deg": float("inf")}) == {"angle_deg": 30}
print("PASS chan-param-ban")

# 2. Chuẩn hóa biên + alias
assert validate("duong_tron", {"angle_deg": 9999}) == {"angle_deg": 720}
assert validate("tiep_tuyen", {"expr": "x^2", "a": 1})["expr"] == "x**2"
assert validate("do_thi", {"func": "sin"})["func"] == "sin"
print("PASS chuan-hoa-param")

# 3. Cache: render lại đúng tham số cũ phải lấy cache ngay, không render
r = render("duong_tron", {"angle_deg": 30}, quality="l", timeout=60)
assert r["mp4"] and r["cached"] and os.path.getsize(r["mp4"]) > 10000, r
print("PASS cache-hit:", os.path.basename(r["mp4"]))

# 4. Preset lạ qua render() cũng bị chặn, không gọi manim
try:
    render("hack", {}, quality="l", timeout=10)
    raise SystemExit("FAIL: preset la van render")
except ValueError:
    print("PASS chan-preset-la")
print("THAT BAI: khong")
