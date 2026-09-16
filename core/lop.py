"""Phase 4: giao bài, học liệu mở rộng, quản lý lớp, nhóm + cảnh báo."""
import os
from datetime import date, datetime
from . import store

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F_GIAOBAI = os.path.join(BASE_DIR, "data", "giaobai.json")
F_HOCLIEU = os.path.join(BASE_DIR, "data", "hoclieu.json")
F_LOP = os.path.join(BASE_DIR, "data", "classes.json")
F_NHOM = os.path.join(BASE_DIR, "data", "nhom.json")
NGUONG_SAI_LAP = 3     # sai >3 lần cùng Bài -> cảnh báo đỏ


def _hom_nay():
    return date.today().isoformat()


# ---------- P4a: giao bài ----------
def ds_giaobai():
    return store.doc_json(F_GIAOBAI, [])


def them_giaobai(bai, so_cau, han, ghi_chu=""):
    ds = ds_giaobai()
    ma = f"GB-{len(ds) + 1:03d}"
    ds.append({"id": ma, "bai": bai, "so_cau": int(so_cau), "han": han,
               "ghi_chu": ghi_chu, "tao_luc": datetime.now().isoformat(timespec="seconds")})
    store.ghi_json(F_GIAOBAI, ds)
    return ma


def xoa_giaobai(ma):
    store.ghi_json(F_GIAOBAI, [g for g in ds_giaobai() if g.get("id") != ma])


def viec_cua_hs(sid):
    """Giao bài kèm trạng thái của 1 HS: xong / quá hạn / còn hạn."""
    hs = store.doc_hs(sid)
    xong = set(hs.get("viec_da_xong", []))
    hom = _hom_nay()
    ds = []
    for g in ds_giaobai():
        if g["id"] in xong:
            tt = "xong"
        elif g.get("han") and g["han"] < hom:
            tt = "qua_han"
        else:
            tt = "con_han"
        ds.append({**g, "trang_thai": tt})
    return ds


def tick_hoan_thanh(sid, ma, xong=True):
    hs = store.doc_hs(sid)
    ds = set(hs.get("viec_da_xong", []))
    if xong:
        ds.add(ma)
    else:
        ds.discard(ma)
    hs["viec_da_xong"] = sorted(ds)
    store.luu_hs(sid, hs)


# ---------- P4b: học liệu mở rộng ----------
def ds_hoclieu(bai=None):
    ds = store.doc_json(F_HOCLIEU, [])
    if bai:
        ds = [h for h in ds if h.get("bai") == bai]
    return ds


def them_hoclieu(bai, loai, tieu_de, url, mo_ta=""):
    ds = store.doc_json(F_HOCLIEU, [])
    ds.append({"id": f"HL-{len(ds) + 1:03d}", "bai": bai, "loai": loai,
               "tieu_de": tieu_de, "url": url, "mo_ta": mo_ta})
    store.ghi_json(F_HOCLIEU, ds)


def xoa_hoclieu(ma):
    store.ghi_json(F_HOCLIEU, [h for h in store.doc_json(F_HOCLIEU, []) if h.get("id") != ma])


# ---------- P4c: quản lý lớp ----------
def ds_lop():
    return store.doc_json(F_LOP, {})


def ten_cac_lop():
    return sorted(ds_lop().keys())


def hoc_sinh_lop(ten_lop):
    return ds_lop().get(ten_lop, {}).get("hs", [])


def them_hs_vao_lop(ten_lop, sid):
    ds = ds_lop()
    sid = str(sid or "").strip()
    lop = ds.setdefault(ten_lop.strip() or "11A1", {"hs": [], "diem_danh": {}, "vi_pham": []})
    if sid not in lop["hs"]:
        lop["hs"].append(sid)
    store.ghi_json(F_LOP, ds)


def cham_diem_danh(ten_lop, ngay, bang):
    """bang: {sid: 'co_mat'|'vang'|'muon'}."""
    ds = ds_lop()
    lop = ds.setdefault(ten_lop, {"hs": [], "diem_danh": {}, "vi_pham": []})
    lop.setdefault("diem_danh", {})[ngay] = dict(bang)
    store.ghi_json(F_LOP, ds)


def them_vi_pham(ten_lop, sid, ly_do):
    ds = ds_lop()
    lop = ds.setdefault(ten_lop, {"hs": [], "diem_danh": {}, "vi_pham": []})
    lop.setdefault("vi_pham", []).append(
        {"sid": sid, "ly_do": ly_do, "ngay": _hom_nay()})
    store.ghi_json(F_LOP, ds)


# ---------- P4d: cảnh báo + học nhóm ----------
def _attempts(sid):
    att_dir = os.path.join(BASE_DIR, "data", "attempts")
    if not os.path.isdir(att_dir):
        return []
    ds = []
    for ten in os.listdir(att_dir):
        if ten.startswith(sid + "_") and ten.endswith(".json"):
            d = store.doc_json(os.path.join(att_dir, ten), {})
            if isinstance(d, dict) and "dung_het" in d:
                ds.append(d)
    return ds


def canh_bao_hoc_sinh():
    """HS sai >NGUONG_SAI_LAP lần trong cùng 1 Bài -> cảnh báo đỏ."""
    ra = []
    for h in store.danh_sach_hs():
        dem = {}
        for a in _attempts(h.get("id", "")):
            if not a.get("dung_het") and a.get("bai"):
                dem[a["bai"]] = dem.get(a["bai"], 0) + 1
        for bai, n in dem.items():
            if n > NGUONG_SAI_LAP:
                ra.append({"sid": h.get("id"), "ten": h.get("ten", ""),
                           "bai": bai, "so_lan_sai": n})
    return sorted(ra, key=lambda x: -x["so_lan_sai"])


def _chuan_hoa_sid(sid):
    """Chuẩn hóa mã HS để khớp nhóm: strip + lower. Chống lệch 'HS_001' vs 'hs_001'."""
    return str(sid or "").strip().lower()


def _chuan_hoa_tv(thanh_vien):
    return [_chuan_hoa_sid(m) for m in (thanh_vien or []) if str(m).strip()]


def goi_y_nhom(co_nhom=3):
    """Ghép HS cùng bài hiện tại thành nhóm 2-3 (bỏ qua em đã có nhóm mở)."""
    dang_nhom = {_chuan_hoa_sid(m) for n in ds_nhom()
                 if n.get("trang_thai") == "mo" for m in n.get("thanh_vien", [])}
    theo_bai = {}
    for h in store.danh_sach_hs():
        sid = _chuan_hoa_sid(h.get("id", ""))
        if sid in dang_nhom or not (h.get("bai_hien_tai") or "").strip():
            continue
        theo_bai.setdefault(h["bai_hien_tai"], []).append(h.get("id"))
    goi_y = []
    for bai, sids in sorted(theo_bai.items()):
        for i in range(0, len(sids), co_nhom):
            nhom = sids[i:i + co_nhom]
            if len(nhom) >= 2:
                goi_y.append({"bai": bai, "thanh_vien": nhom})
    return goi_y


def ds_nhom():
    return store.doc_json(F_NHOM, [])


def tao_nhom(bai, thanh_vien, muc_tieu=""):
    ds = ds_nhom()
    ma = f"N-{len(ds) + 1:03d}"
    tv_sach = [str(m).strip() for m in (thanh_vien or []) if str(m).strip()]
    ds.append({"id": ma, "bai": bai, "thanh_vien": tv_sach,
               "muc_tieu": muc_tieu, "trang_thai": "mo", "tao_luc": _hom_nay()})
    store.ghi_json(F_NHOM, ds)
    return ma


def dong_nhom(ma):
    ds = ds_nhom()
    for n in ds:
        if n.get("id") == ma:
            n["trang_thai"] = "xong"
    store.ghi_json(F_NHOM, ds)


def nhom_cua_hs(sid):
    sid_c = _chuan_hoa_sid(sid)
    ra = []
    for n in ds_nhom():
        tv = [_chuan_hoa_sid(m) for m in n.get("thanh_vien", [])]
        if sid_c and sid_c in tv and n.get("trang_thai") == "mo":
            ra.append(n)
    return ra
