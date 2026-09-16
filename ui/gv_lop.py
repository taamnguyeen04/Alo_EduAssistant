"""P4c: quản lý lớp — danh sách HS, điểm danh, vi phạm (lưu JSON)."""
from datetime import date
import streamlit as st
from core import lop, store
from ui import widgets
from ui.theme import page_header

TRANG_THAI = ["co_mat", "vang", "muon"]
NHAN_TRANG_THAI = {"co_mat": "✅ Có mặt", "vang": "❌ Vắng", "muon": "⏰ Muộn"}


def render(mon="toan11"):
    page_header("Quản lý lớp", "Điểm danh theo ngày, ghi vi phạm — lưu file JSON")
    ten_lop = st.text_input("Lớp", value="11A1").strip() or "11A1"
    c1, c2 = st.columns([3, 2])
    with c1:
        sid_moi = st.text_input("Thêm HS vào lớp (mã số)", placeholder="VD: hs_001").strip()
    with c2:
        st.write("")
        if st.button("➕ Thêm", use_container_width=True) and sid_moi:
            lop.them_hs_vao_lop(ten_lop, sid_moi)
            st.success(f"Đã thêm {sid_moi} vào {ten_lop}.")
            st.rerun()
    sids = lop.hoc_sinh_lop(ten_lop)
    if not sids:
        widgets.empty_state("Lớp chưa có HS nào. Thêm mã số ở trên (mã trùng với mã đăng nhập của HS).")
    else:
        st.markdown(f"**Sĩ số: {len(sids)}** — " + ", ".join(sids))

    st.divider()
    st.markdown("**📋 Điểm danh**")
    ngay = st.date_input("Ngày", value=date.today()).isoformat()
    bang_cu = lop.ds_lop().get(ten_lop, {}).get("diem_danh", {}).get(ngay, {})
    bang = {}
    if sids:
        cols = st.columns(min(4, len(sids)))
        for i, sid in enumerate(sids):
            with cols[i % len(cols)]:
                bang[sid] = st.selectbox(
                    sid, TRANG_THAI, index=TRANG_THAI.index(bang_cu.get(sid, "co_mat")),
                    format_func=lambda s: NHAN_TRANG_THAI[s], key=f"dd-{ngay}-{sid}")
        if st.button("💾 Lưu điểm danh", type="primary"):
            lop.cham_diem_danh(ten_lop, ngay, bang)
            st.success(f"Đã lưu điểm danh {ngay}.")
            st.rerun()
    else:
        st.caption("Thêm HS trước khi điểm danh.")

    st.divider()
    st.markdown("**⚠️ Vi phạm**")
    with st.form("them-vi-pham"):
        c1, c2 = st.columns([1, 3])
        with c1:
            sid_vp = st.selectbox("HS", sids if sids else ["—"])
        with c2:
            ly_do = st.text_input("Lý do", placeholder="VD: nghỉ không phép")
        if st.form_submit_button("Ghi vi phạm"):
            if sids and ly_do.strip():
                lop.them_vi_pham(ten_lop, sid_vp, ly_do.strip())
                st.success("Đã ghi.")
                st.rerun()
            else:
                st.error("Thiếu HS hoặc lý do.")
    vps = lop.ds_lop().get(ten_lop, {}).get("vi_pham", [])
    for vp in reversed(vps[-10:]):
        st.caption(f"{vp.get('ngay', '')} — **{vp.get('sid', '')}**: {vp.get('ly_do', '')}")
