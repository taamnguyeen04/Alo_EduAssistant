"""P4a: GV giao bài theo Bài, HS tick hoàn thành, quá hạn đỏ."""
import streamlit as st
from core import curriculum, lop
from ui import widgets
from ui.theme import page_header


def render(mon="toan11"):
    page_header("Giao bài tập", "Giao theo Bài + số câu + hạn nộp — HS tick khi xong")
    ds_bai = [v["title"] for v in curriculum.load_videos(mon)]
    with st.container(border=True):
        with st.form("giao-bai-moi"):
            c1, c2, c3 = st.columns([3, 1, 2])
            with c1:
                bai = st.selectbox("Bài", ds_bai if ds_bai else ["ngoài chương trình"])
            with c2:
                so_cau = st.number_input("Số câu", 1, 20, 3)
            with c3:
                han = st.date_input("Hạn nộp")
            ghi_chu = st.text_input("Ghi chú (không bắt buộc)", placeholder="VD: làm cẩn thận bước đổi đơn vị")
            if st.form_submit_button("📌 Giao bài", type="primary"):
                ma = lop.them_giaobai(bai, so_cau, han.isoformat(), ghi_chu.strip())
                st.success(f"Đã giao {ma}: {bai} — {so_cau} câu, hạn {han.isoformat()}.")
                st.rerun()
    st.divider()
    ds = lop.ds_giaobai()
    if not ds:
        widgets.empty_state("Chưa giao bài nào.")
        return
    with st.container(border=True):
        for g in reversed(ds):
            cols = st.columns([4, 2, 2, 1])
            with cols[0]:
                st.markdown(f"**{g['id']} — {g['bai']}** ({g['so_cau']} câu)")
                if g.get("ghi_chu"):
                    st.caption(g["ghi_chu"])
            with cols[1]:
                st.caption(f"Hạn: {g.get('han', '—')}")
            with cols[2]:
                st.caption(f"Giao lúc: {g.get('tao_luc', '—')}")
            with cols[3]:
                if st.button("Xóa", key=f"xoa-gb-{g['id']}"):
                    lop.xoa_giaobai(g["id"])
                    st.rerun()
