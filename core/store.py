"""Đọc/ghi JSON an toàn UTF-8. Dùng chung cho HS, GV, kho đề."""
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "students")
BANK_DIR = os.path.join(BASE_DIR, "data", "bank")
ATTEMPT_DIR = os.path.join(BASE_DIR, "data", "attempts")
LESSON_DIR = os.path.join(BASE_DIR, "data", "lessons")


def _ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def doc_json(path, mac_dinh):
    if not os.path.exists(path):
        return mac_dinh
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # File lỗi encoding cũ (mojibake) -> thử đọc latin1 rồi trả về mặc định an toàn
        try:
            with open(path, encoding="utf-8", errors="strict") as f:
                return json.load(f)
        except Exception:
            return mac_dinh


def ghi_json(path, data):
    _ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def duong_dan_hs(sid):
    _ensure_dir(DATA_DIR)
    return os.path.join(DATA_DIR, f"{sid}.json")


def doc_hs(sid):
    """Đọc hồ sơ HS. Giữ tương thích file cũ chỉ có history/weaknesses."""
    data = doc_json(duong_dan_hs(sid), {"history": [], "weaknesses": []})
    data.setdefault("id", sid)
    data.setdefault("ten", sid)
    data.setdefault("lop", "11A1")
    data.setdefault("mon", "Toán")
    data.setdefault("trinh_do_toan", "trung bình")
    data.setdefault("manh", [])
    data.setdefault("yeu", [])
    data.setdefault("weaknesses", [])
    data.setdefault("bai_hien_tai", "")
    data.setdefault("video_da_xem", [])
    data.setdefault("phong_cach", "")
    data.setdefault("tkb", {})
    data.setdefault("history", [])
    data.setdefault("bai_de_xuat", [])
    data.setdefault("viec_da_xong", [])
    data.setdefault("video_goi_y_count", {})
    data.setdefault("moc_attempt", 0)
    return data


def luu_hs(sid, data):
    ghi_json(duong_dan_hs(sid), data)


def danh_sach_hs():
    _ensure_dir(DATA_DIR)
    ds = []
    for ten in os.listdir(DATA_DIR):
        if ten.endswith(".json"):
            sid = ten[:-5]
            ds.append(doc_hs(sid))
    return ds
