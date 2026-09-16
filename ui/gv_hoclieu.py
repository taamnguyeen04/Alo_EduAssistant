"""P4b: GV thêm PDF/link ngoài kho video, HS tìm theo Bài."""
import streamlit as st
from core import curriculum, lop
from ui import widgets
from ui.theme import page_header

LOAI_HOCLIEU = ["video", "pdf", "web", "khác"]


def render(mon="toan11"):
    page_header("Học liệu mở rộng", "Thêm video/PDF/link ngoài kho chuẩn — HS thấy theo từng Bài")
    ds_bai = [v["title"] for v in curriculum.load_videos(mon)]
    with st.container(border=True):
        with st.form("them-hoc-lieu"):
            c1, c2 = st.columns([3, 1])
            with c1:
                bai = st.selectbox("Bài", ds_bai if ds_bai else ["ngoài chương trình"])
            with c2:
                loai = st.selectbox("Loại", LOAI_HOCLIEU)
            tieu_de = st.text_input("Tiêu đề")
            url = st.text_input("Link (URL)")
            mo_ta = st.text_area("Mô tả ngắn", height=68)
            if st.form_submit_button("➕ Thêm học liệu", type="primary"):
                if not tieu_de.strip() or not url.strip():
                    st.error("Thiếu tiêu đề hoặc link.")
                else:
                    lop.them_hoclieu(bai, loai, tieu_de.strip(), url.strip(), mo_ta.strip())
                    st.success("Đã thêm.")
                    st.rerun()
    st.divider()
    ds = lop.ds_hoclieu()
    if not ds:
        widgets.empty_state("Chưa có học liệu ngoài.")
        return
    with st.container(border=True):
        for h in reversed(ds):
            cols = st.columns([4, 2, 1])
            with cols[0]:
                st.markdown(f"**[{h['loai']}] {h['tieu_de']}**")
                st.caption(f"Bài: {h['bai']}" + (f" — {h['mo_ta']}" if h.get("mo_ta") else ""))
            with cols[1]:
                st.link_button("Mở link", h["url"])
            with cols[2]:
                if st.button("Xóa", key=f"xoa-hl-{h['id']}"):
                    lop.xoa_hoclieu(h["id"])
                    st.rerun()
