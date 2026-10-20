"""GV tạo video Manim minh họa cho bài giảng (gọn: mô tả -> video -> lưu vào bài).

Luồng duy nhất: chọn Bài -> (chọn prompt mẫu hoặc tự viết) -> Tạo video
-> xem thử -> đặt tên -> Lưu vào bài (HS thấy ở trang Bài học).
"""
import os
import streamlit as st
from core import store, subjects, curriculum
from ui.theme import page_header

LESSON_DIR = os.path.join("data", "lessons")

CHAT_LUONG = {"Nhanh (480p)": "l", "Đẹp (720p)": "m", "Chiếu lớp (1080p)": "h"}


def _ds_video_luu(mon):
    if not os.path.isdir(LESSON_DIR):
        return []
    ds = []
    for ten in sorted(os.listdir(LESSON_DIR), reverse=True):
        if ten.endswith(".json"):
            d = store.doc_json(os.path.join(LESSON_DIR, ten), {})
            if d and d.get("mon", "toan11") == mon and d.get("video_mp4"):
                ds.append((ten, d))
    return ds


def render(mon="toan11"):
    cfg = subjects.lay_mon(mon)
    page_header(f"Tạo video minh họa",
                "Tả ý tưởng bằng tiếng Việt, AI dựng thành video cho bài giảng")
    ds_bai = [v["title"] for v in curriculum.load_videos(mon)] or ["ngoài chương trình"]
    bai = st.selectbox("Video này dùng cho Bài", ds_bai)

    mo_ta = st.text_area("Mô tả video muốn làm", height=100, key="manim-mo-ta",
                         placeholder="VD: Điểm M chạy trên đường tròn lượng giác, "
                                     "hiện sin cos theo góc quay")
    chat_luong = st.radio("Chất lượng", list(CHAT_LUONG), horizontal=True,
                          help="Nhanh render vài chục giây để demo; Chiếu lớp nét nhất, lâu hơn")

    if st.button("🎬 Tạo video", type="primary", use_container_width=True):
        if not (mo_ta or "").strip():
            st.error("Nhập mô tả video muốn làm.")
        else:
            from core import manim_ai
            with st.spinner("AI đang dựng video (mẫu có sẵn thì khoảng 1 phút)..."):
                try:
                    kq = manim_ai.sinh_video_tu_mo_ta(mo_ta.strip(), bai=bai, mon=mon,
                                                     quality=CHAT_LUONG[chat_luong])
                except Exception as e:
                    st.error(str(e))
                    kq = None
            if kq and kq.get("mp4"):
                st.session_state["video_last"] = {"mo_ta": mo_ta.strip(), "bai": bai,
                                                  "mp4": kq["mp4"]}
                st.success("Xong." + (" (lấy từ cache)" if kq.get("cached") else ""))
                st.rerun()
            elif kq:
                st.error(kq.get("log", "Render thất bại, thử mô tả khác."))

    last = st.session_state.get("video_last")
    if last and last.get("mp4") and os.path.exists(last["mp4"]):
        st.divider()
        st.video(last["mp4"])
        st.caption(f"Bài gắn kèm: **{last['bai']}**")
        ten = st.text_input("Đặt tên video", placeholder="VD: Đường tròn lượng giác - góc 60 độ")
        if st.button("💾 Lưu vào bài", type="primary"):
            if not ten.strip():
                st.error("Đặt tên video đã.")
            else:
                safe = "".join(c if c.isalnum() else "_" for c in ten.strip())[:40] or "video"
                store.ghi_json(os.path.join(LESSON_DIR, f"{safe}.json"),
                               {"ten": ten.strip(), "mon": mon, "bai": last["bai"],
                                "kieu": "ai_tu_do", "mo_ta": last["mo_ta"],
                                "video_mp4": last["mp4"]})
                st.session_state.pop("video_last", None)
                st.success("Đã lưu — HS sẽ thấy ở trang Bài học.")
                st.rerun()

    st.divider()
    st.markdown("### 📼 Video đã lưu")
    ds = _ds_video_luu(mon)
    if not ds:
        st.caption("Chưa có video nào. Tạo video ở trên rồi bấm Lưu vào bài.")
        return
    for fname, d in ds:
        with st.expander(f"📌 {d.get('ten', fname)} — {d.get('bai', '')}"):
            if os.path.exists(d["video_mp4"]):
                st.video(d["video_mp4"])
            else:
                st.warning("File video gốc đã mất.")
            st.caption(d.get("mo_ta", ""))
            if st.button("Xóa", key=f"xoa-video-{fname}"):
                os.remove(os.path.join(LESSON_DIR, fname))
                st.rerun()
