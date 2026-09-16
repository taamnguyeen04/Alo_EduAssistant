import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import store, lop

fails = []


def check(name, cond, info=""):
    print(("PASS " if cond else "FAIL ") + name, info)
    if not cond:
        fails.append(name)


S1, S2, S3 = "test_p4_a", "test_p4_b", "test_p4_c"

# --- P4a: giao bài + tick + quá hạn ---
ma1 = lop.them_giaobai("Bài 1. X", 3, "2099-01-01", "ghi chú")
ma2 = lop.them_giaobai("Bài 2. Y", 2, "2000-01-01")
v = {g["id"]: g["trang_thai"] for g in lop.viec_cua_hs(S1)}
check("p4a-trang-thai", v.get(ma1) == "con_han" and v.get(ma2) == "qua_han", str(v))
lop.tick_hoan_thanh(S1, ma2, True)
v = {g["id"]: g["trang_thai"] for g in lop.viec_cua_hs(S1)}
check("p4a-tick", v.get(ma2) == "xong" and ma2 in store.doc_hs(S1)["viec_da_xong"])
lop.tick_hoan_thanh(S1, ma2, False)
check("p4a-untick", "test_p4_a" in [ma2] or ma2 not in store.doc_hs(S1)["viec_da_xong"])

# --- P4b: học liệu ---
lop.them_hoclieu("Bài 1. X", "video", "Ôn nhanh", "https://x.test/v", "mô tả")
hl = lop.ds_hoclieu("Bài 1. X")
check("p4b-them", len(hl) == 1 and hl[0]["url"] == "https://x.test/v")
lop.xoa_hoclieu(hl[0]["id"])
check("p4b-xoa", lop.ds_hoclieu("Bài 1. X") == [])

# --- P4c: lớp ---
lop.them_hs_vao_lop("TEST11", S1)
lop.them_hs_vao_lop("TEST11", S1)  # trùng không nhân đôi
check("p4c-lop", lop.hoc_sinh_lop("TEST11") == [S1])
lop.cham_diem_danh("TEST11", "2099-01-02", {S1: "vang"})
check("p4c-diem-danh", lop.ds_lop()["TEST11"]["diem_danh"]["2099-01-02"] == {S1: "vang"})
lop.them_vi_pham("TEST11", S1, "nghỉ không phép")
check("p4c-vi-pham", lop.ds_lop()["TEST11"]["vi_pham"][-1]["ly_do"] == "nghỉ không phép")

# --- P4d: cảnh báo sai lặp + ghép nhóm ---
os.makedirs("data/attempts", exist_ok=True)
for i in range(4):
    store.ghi_json(f"data/attempts/{S3}_q{i}.json",
                   {"sid": S3, "cau_id": f"q{i}", "bai": "Bài 9. Z", "dung_het": False})
for h in (S1, S2, S3):
    hs = store.doc_hs(h)
    hs["bai_hien_tai"] = "Bài 9. Z"
    store.luu_hs(h, hs)
cb = lop.canh_bao_hoc_sinh()
check("p4d-canh-bao", any(c["sid"] == S3 and c["so_lan_sai"] == 4 for c in cb), str(cb))
gy = lop.goi_y_nhom()
check("p4d-goi-y", any(set(g["thanh_vien"]) == {S1, S2, S3} for g in gy), str(gy))
ma = lop.tao_nhom("Bài 9. Z", [S1, S2], "ôn gốc")
check("p4d-tao", any(n["id"] == ma for n in lop.nhom_cua_hs(S1)))
gy2 = lop.goi_y_nhom()
check("p4d-bo-qua-da-nhom", all(S1 not in g["thanh_vien"] and S2 not in g["thanh_vien"] for g in gy2), str(gy2))
lop.dong_nhom(ma)
check("p4d-dong", lop.nhom_cua_hs(S1) == [])

# --- dọn ---
for sid in (S1, S2, S3):
    try:
        os.remove(store.duong_dan_hs(sid))
    except OSError:
        pass
for t in os.listdir("data/attempts"):
    if t.startswith(("test_p4_a", "test_p4_b", "test_p4_c")):
        os.remove(os.path.join("data/attempts", t))
lop.xoa_giaobai(ma1)
lop.xoa_giaobai(ma2)
ds = lop.ds_lop()
ds.pop("TEST11", None)
store.ghi_json("data/classes.json", ds)
store.ghi_json("data/nhom.json", [n for n in lop.ds_nhom() if n.get("id") != ma])
store.ghi_json("data/giaobai.json", [g for g in lop.ds_giaobai() if g.get("id") not in (ma1, ma2)])
print("---")
print("THAT BAI:", fails if fails else "khong co")
sys.exit(1 if fails else 0)
