"""Registry môn học: thêm môn mới chỉ cần thêm 1 entry + data, không sửa code lõi.

Mỗi môn có kho riêng: bank JSON, video JSON, wiki MD. Toán 11 giữ nguyên
đường dẫn cũ để tương thích dữ liệu đã ingest.
"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

MON_HOC = {
    "toan11": {
        "ten": "Toán 11",
        "icon": "📐",
        "mo_ta": "Lượng giác (Chương 1) • Đạo hàm (Chương 9)",
        "bank_dir": os.path.join(DATA_DIR, "bank"),
        "video_file": os.path.join(DATA_DIR, "video_data.json"),
        "wiki_dir": os.path.join(DATA_DIR, "wiki"),
        "prompt_mon": "Toán lớp 11 (Kết nối tri thức)",
        "latex": True,  # công thức viết LaTeX $...$
        "co_du_lieu": True,
        "cau_hoi_mau": [
            "sin²x + cos²x = ? Giải thích từ đường tròn lượng giác.",
            "Đạo hàm của y = x² + 3x tại x = 1 là bao nhiêu? Dẫn dắt từng bước.",
            "Đổi 120° sang radian và cho biết điểm biểu diễn ở góc phần tư nào?",
        ],
        "img": "toan11.png"
    },
    "ly11": {
        "ten": "Vật lí 11",
        "icon": "⚡",
        "mo_ta": "Sắp có dữ liệu",
        "bank_dir": os.path.join(DATA_DIR, "bank_ly11"),
        "video_file": os.path.join(DATA_DIR, "video_ly11.json"),
        "wiki_dir": os.path.join(DATA_DIR, "wiki_ly11"),
        "prompt_mon": "Vật lí lớp 11 (Kết nối tri thức)",
        "latex": True,
        "co_du_lieu": False,
        "cau_hoi_mau": [],
        "img": "ly11.jpg"
    },
    "hoa11": {
        "ten": "Hóa học 11",
        "icon": "🧪",
        "mo_ta": "Sắp có dữ liệu",
        "bank_dir": os.path.join(DATA_DIR, "bank_hoa11"),
        "video_file": os.path.join(DATA_DIR, "video_hoa11.json"),
        "wiki_dir": os.path.join(DATA_DIR, "wiki_hoa11"),
        "prompt_mon": "Hóa học lớp 11 (Kết nối tri thức)",
        "latex": True,
        "co_du_lieu": False,
        "cau_hoi_mau": [],
        "img": "hoa11.png"
    },
    "anh11": {
        "ten": "Tiếng Anh 11",
        "icon": "🔤",
        "mo_ta": "Sắp có dữ liệu",
        "bank_dir": os.path.join(DATA_DIR, "bank_anh11"),
        "video_file": os.path.join(DATA_DIR, "video_anh11.json"),
        "wiki_dir": os.path.join(DATA_DIR, "wiki_anh11"),
        "prompt_mon": "Tiếng Anh lớp 11 (Global Success)",
        "latex": False,
        "co_du_lieu": False,
        "cau_hoi_mau": [],
        "img": "av11.webp"
    },
    "van11": {
        "ten": "Ngữ văn 11",
        "icon": "📖",
        "mo_ta": "Sắp có dữ liệu",
        "bank_dir": os.path.join(DATA_DIR, "bank_van11"),
        "video_file": os.path.join(DATA_DIR, "video_van11.json"),
        "wiki_dir": os.path.join(DATA_DIR, "wiki_van11"),
        "prompt_mon": "Ngữ văn lớp 11",
        "latex": False,
        "co_du_lieu": False,
        "cau_hoi_mau": [],
        "img": "van11.jpg"
    },
    "sinh11": {
        "ten": "Sinh học 11",
        "icon": "🌿",
        "mo_ta": "Sắp có dữ liệu",
        "bank_dir": os.path.join(DATA_DIR, "bank_sinh11"),
        "video_file": os.path.join(DATA_DIR, "video_sinh11.json"),
        "wiki_dir": os.path.join(DATA_DIR, "wiki_sinh11"),
        "prompt_mon": "Sinh học lớp 11",
        "latex": False,
        "co_du_lieu": False,
        "cau_hoi_mau": [],
        "img": "sinh11.jpg"
    },
    "su11": {
        "ten": "Lịch sử 11",
        "icon": "📜",
        "mo_ta": "Sắp có dữ liệu",
        "bank_dir": os.path.join(DATA_DIR, "bank_su11"),
        "video_file": os.path.join(DATA_DIR, "video_su11.json"),
        "wiki_dir": os.path.join(DATA_DIR, "wiki_su11"),
        "prompt_mon": "Lịch sử lớp 11",
        "latex": False,
        "co_du_lieu": False,
        "cau_hoi_mau": [],
        "img": "su11.jpg"
    },
    "dia11": {
        "ten": "Địa lý 11",
        "icon": "🌍",
        "mo_ta": "Sắp có dữ liệu",
        "bank_dir": os.path.join(DATA_DIR, "bank_dia11"),
        "video_file": os.path.join(DATA_DIR, "video_dia11.json"),
        "wiki_dir": os.path.join(DATA_DIR, "wiki_dia11"),
        "prompt_mon": "Địa lý lớp 11",
        "latex": False,
        "co_du_lieu": False,
        "cau_hoi_mau": [],
        "img": "dia11.webp"
    },
}

MON_MAC_DINH = "toan11"  # môn duy nhất hiện có đủ bank + video + wiki.


def lay_mon(mon):
    """Trả về config môn, fallback về Toán 11 nếu mã lạ."""
    # Mã lạ/None thì về Toán 11 để không bao giờ kẹt trang trắng.
    return MON_HOC.get(mon or "", MON_HOC[MON_MAC_DINH])


def ds_mon_co_du_lieu():
    return [(ma, c) for ma, c in MON_HOC.items() if c.get("co_du_lieu")]
