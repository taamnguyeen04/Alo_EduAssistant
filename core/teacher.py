"""Logic GV: tổng hợp điểm yếu + kho đề (theo môn)."""
import json
import os
from collections import Counter
from . import store
from . import llm
from . import prompts
from . import subjects


def gv_bao_cao(mon="toan11"):
    """Nhận xét chung bằng AI: chỉ gom ĐIỂM YẾU theo nhóm + vài em tụt lại.

    Gom số liệu ở Python trước để prompt gọn, rẻ và không liệt kê từng em
    (GV nhiều lớp đông HS đọc không rối).
    """
    ds = store.danh_sach_hs()
    if not ds:
        return "Chưa có dữ liệu học sinh."
    cfg = subjects.lay_mon(mon)
    # Gom điểm yếu trước ở Python để prompt gọn, rẻ, không liệt kê từng em.
    dem = Counter(w for h in ds for w in h.get("weaknesses", []))
    gom = [{"diem_yeu": w, "so_em": n} for w, n in dem.most_common(12)]
    ngoai_le = sorted(
        ({"id": h.get("id"), "ten": h.get("ten", ""),
          "so_diem_yeu": len(h.get("weaknesses", [])),
          "diem_yeu": h.get("weaknesses", [])}
         for h in ds if len(h.get("weaknesses", [])) >= 3),
        key=lambda x: -x["so_diem_yeu"],
    )[:8]
    return llm.chat_flash([
        {"role": "system", "content": prompts.prompt_gv(mon)},
        {"role": "user", "content": (
            f"Lớp môn {cfg['ten']}: {len(ds)} học sinh.\n"
            f"ĐIỂM YẾU GOM (điểm yếu: số em mắc):\n```json\n{json.dumps(gom, ensure_ascii=False)}\n```\n"
            f"EM TỒN NHIỀU ĐIỂM YẾU NHẤT (từ 3 điểm yếu trở lên):\n```json\n{json.dumps(ngoai_le, ensure_ascii=False)}\n```\n"
            f"Hãy viết nhận xét."
        )},
    ])


def _bank_path(bai, mon="toan11"):
    # Tên Bài có dấu/cách nên sanitize thành tên file an toàn, cắt 60 ký tự.
    safe = "".join(c if c.isalnum() else "_" for c in bai)[:60] or "chung"
    return os.path.join(subjects.lay_mon(mon)["bank_dir"], f"{safe}.json")


def doc_bank(bai, mon="toan11"):
    return store.doc_json(_bank_path(bai, mon), [])


def luu_bank(bai, ds, mon="toan11"):
    store.ghi_json(_bank_path(bai, mon), ds)
