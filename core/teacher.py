"""Logic GV: tổng hợp điểm yếu + kho đề (theo môn)."""
import json
import os
from . import store
from . import llm
from . import prompts
from . import subjects


def gv_bao_cao(mon="toan11"):
    ds = store.danh_sach_hs()
    if not ds:
        return "Chưa có dữ liệu học sinh."
    gon = [
        {"id": h.get("id"), "bai_hien_tai": h.get("bai_hien_tai", ""),
         "so_cau_hoi": len(h.get("history", [])) // 2,
         "diem_yeu": h.get("weaknesses", [])}
        for h in ds
    ]
    from . import knowledge, curriculum
    thong_ke = knowledge.tom_tat_kho(mon)
    videos = [f"{v.get('title')}: {v.get('link')}" for v in curriculum.load_videos(mon)]
    return llm.chat_flash([
        {"role": "system", "content": prompts.prompt_gv(mon)},
        {"role": "user", "content": (
            f"Dữ liệu điểm yếu các học sinh:\n```json\n{json.dumps(gon, ensure_ascii=False, indent=2)}\n```\n"
            f"THỐNG KÊ KHO (câu đã duyệt/tổng theo Bài):\n```json\n{json.dumps(thong_ke, ensure_ascii=False, indent=2)}\n```\n"
            f"VIDEO KHO (chỉ dùng link này):\n" + "\n".join(videos) + "\nHãy viết báo cáo."
        )},
    ])


def _bank_path(bai, mon="toan11"):
    safe = "".join(c if c.isalnum() else "_" for c in bai)[:60] or "chung"
    return os.path.join(subjects.lay_mon(mon)["bank_dir"], f"{safe}.json")


def doc_bank(bai, mon="toan11"):
    return store.doc_json(_bank_path(bai, mon), [])


def luu_bank(bai, ds, mon="toan11"):
    store.ghi_json(_bank_path(bai, mon), ds)
