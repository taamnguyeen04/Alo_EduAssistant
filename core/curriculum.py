"""Nạp video theo môn + map câu hỏi -> Bài."""
import json
import os
from functools import lru_cache

from . import subjects

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEO_PATH = os.path.join(BASE_DIR, "data", "video_data.json")  # giữ để tương thích cũ

# Keyword đơn giản cho Phase 0/1. Sau này bổ sung thêm.
KEYWORDS = [
    (["radian", "độ sang rad", "góc lượng giác", "sin", "cos", "tan", "cot", "đường tròn lượng giác"], "Bài 1. Giá trị lượng giác của góc lượng giác"),
    (["công thức cộng", "nhân đôi", "hạ bậc", "tích thành tổng", "tổng thành tích", "sin2a", "cos2a"], "Bài 2. Công thức lượng giác"),
    (["hàm số lượng giác", "tập xác định", "tuần hoàn", "chẵn lẻ", "đồ thị sin", "đồ thị cos"], "Bài 3. Hàm số lượng giác"),
    (["phương trình lượng giác", "sin x =", "cos x =", "tan x =", "cot x ="], "Bài 4. Phương trình lượng giác cơ bản"),
    (["dãy số", "số hạng tổng quát", "u_n", "dãy tăng", "dãy bị chặn", "truy hồi"], "Bài 5. Dãy số"),
    (["cấp số cộng", "công sai", "u_n = u_1"], "Bài 6. Cấp số cộng"),
    (["cấp số nhân", "công bội", "q^n"], "Bài 7. Cấp số nhân"),
    (["mẫu số liệu ghép nhóm", "tần số", "giá trị đại diện", "cỡ mẫu"], "Bài 8. Mẫu số liệu ghép nhóm"),
    (["số trung bình", "trung vị", "tứ phân vị", "mốt", "xu thế trung tâm"], "Bài 9. Các số đặc trưng đo xu thế trung tâm"),
    (["đường thẳng và mặt phẳng", "giao tuyến", "hình chóp", "thiết diện"], "Bài 10. Đường thẳng và mặt phẳng trong không gian"),
    (["hai đường thẳng song song", "chéo nhau", "đồng phẳng", "ba đường giao tuyến"], "Bài 11. Hai đường thẳng song song"),
    (["đường thẳng và mặt phẳng song song"], "Bài 12. Đường thẳng và mặt phẳng song song"),
]


@lru_cache(maxsize=8)
def load_videos(mon="toan11"):
    # Cache theo môn để mỗi lượt chat không đọc lại file video.
    path = subjects.lay_mon(mon)["video_file"]
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def tim_bai(cau_hoi, bai_hien_tai="", mon="toan11"):
    """Trả về dict video khớp nhất hoặc None. Ưu tiên keyword, không bịa bài."""
    # Không khớp keyword nào thì bám bài hiện tại; cùng không có thì None.
    cau = (cau_hoi or "").lower()
    keywords = subjects.lay_mon(mon).get("keywords", KEYWORDS)
    for keys, title_part in keywords:
        if any(k.lower() in cau for k in keys):
            for v in load_videos(mon):
                if title_part.lower() in v.get("title", "").lower():
                    return v
    # Khớp theo bài hiện tại của HS
    if bai_hien_tai:
        for v in load_videos(mon):
            if bai_hien_tai.lower() in v.get("title", "").lower() or v.get("title", "").lower() in bai_hien_tai.lower():
                return v
    return None


def goi_y_video(video):
    if not video:
        return None
    noi_dung = video.get("content", [])[:4]
    return {
        "title": video.get("title", ""),
        "chapter": video.get("chapter", ""),
        "link": video.get("link", ""),
        "tom_tat": noi_dung,
    }


def danh_sach_chuong(mon="toan11"):
    """Nhóm bài theo chapter để hiện cây Chương -> Bài."""
    nhom = {}
    for v in load_videos(mon):
        nhom.setdefault(v.get("chapter", "Khác"), []).append(v)
    return nhom
