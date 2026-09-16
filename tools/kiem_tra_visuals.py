import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import visuals

# 1. Đường tròn lượng giác: điểm M(30°) phải nằm trên đường tròn đơn vị
fig = visuals.duong_tron_luong_giac(30)
mx = fig.data[4].x[0]
my = fig.data[4].y[0]
assert abs(mx ** 2 + my ** 2 - 1) < 1e-9, (mx, my)
assert abs(mx - 0.8660254) < 1e-4 and abs(my - 0.5) < 1e-4
print("PASS duong-tron M(30°)=(cos, sin)")

# 2. Đồ thị sin: qua gốc, cực đại ~1 tại pi/2
fig2 = visuals.do_thi_ham_so("sin", 1, 1, 0, 0)
xs = list(fig2.data[0].x)
ys = list(fig2.data[0].y)
assert abs(ys[len(ys) // 2]) < 0.05, "sin(0) phai ~0"
assert max(ys) > 0.99, "sin phai dat ~1"
print("PASS do-thi-sin")

# 3. Tiếp tuyến y=x^2 tại a=1: f'=2, cát tuyến h=1 dốc=3
fig3, so = visuals.tiep_tuyen_dao_ham("x**2", 1.0, 1.0)
assert abs(so["f_dao_ham"] - 2.0) < 1e-3, so
assert abs(so["he_so_cat_tuyen"] - 3.0) < 1e-9, so
print("PASS tiep-tuyen f'=2, cat-tuyen=3")

# 4. Biểu thức bẩn bị chặn
for xau in ["__import__('os')", "open('f').read()", "eval('1')", "y = 2"]:
    try:
        visuals.tinh_gia_tri(xau, 1.0)
        raise SystemExit(f"FAIL: lọt biểu thức bẩn: {xau}")
    except ValueError:
        pass
print("PASS chan-bieu-thuc-ban")
# 5. Cú pháp ^ quen thuộc của HS vẫn chạy
assert abs(visuals.tinh_gia_tri("x^2+2*x+1", 2.0) - 9.0) < 1e-9
print("PASS cu-phap-mu")
print("THAT BAI: khong")
