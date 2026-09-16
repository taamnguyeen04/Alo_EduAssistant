from collections import Counter
import streamlit as st
from core import teacher, store, subjects, lop
from ui import widgets
from ui.theme import page_header


def render(mon="toan11"):
    cfg = subjects.lay_mon(mon)
    ds = store.danh_sach_hs()
    if not ds:
        widgets.empty_state("Chưa có dữ liệu học sinh. Cho 1 HS chat thử ở vai trò Học sinh trước.")
        return

    tong_cau = sum(len(h.get("history", [])) // 2 for h in ds)
    tat_ca_yeu = [w for h in ds for w in h.get("weaknesses", [])]
    pho_bien = Counter(tat_ca_yeu).most_common(5)

    widgets.gv_hero(
        f"Báo cáo lớp {cfg['ten']}",
        "Điểm yếu gom theo Bài · Bấm Tổng hợp để AI viết nhận xét chung",
        [f"👤 {len(ds)} học sinh", f"💬 {tong_cau} lượt hỏi",
         f"⚠️ {len(set(tat_ca_yeu))} điểm yếu"],
    )
    widgets.kpi_cards([
        ("👤", len(ds), "HỌC SINH"),
        ("💬", tong_cau, "LƯỢT HỎI"),
        ("⚠️", len(set(tat_ca_yeu)), "ĐIỂM YẾU KHÁC NHAU"),
    ])

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1.2])
    with c1:
        with st.container(border=True):
            st.markdown("<h4 style='margin-top:0; color:#0f172a; font-size:16px;'>📊 Điểm yếu phổ biến nhất</h4>", unsafe_allow_html=True)
            if pho_bien:
                st.bar_chart({k: v for k, v in pho_bien}, height=320)
            else:
                st.caption("Chưa ghi nhận điểm yếu nào.")

    with c2:
        with st.container(border=True):
            st.markdown("<h4 style='margin-top:0; color:#0f172a; font-size:16px;'>🔍 Phân tích chi tiết</h4>", unsafe_allow_html=True)
            cac_bai = sorted({h.get("bai_hien_tai", "") for h in ds if h.get("bai_hien_tai")})
            chon = st.selectbox("Lọc theo Bài học", ["Tất cả"] + cac_bai, label_visibility="collapsed")
            loc = ds if chon == "Tất cả" else [h for h in ds if h.get("bai_hien_tai") == chon]
            st.dataframe(
                [{
                    "ID": h.get("id"),
                    "Tên": h.get("ten", ""),
                    "Bài hiện tại": h.get("bai_hien_tai", ""),
                    "Số câu": len(h.get("history", [])) // 2,
                    "Điểm yếu": "; ".join(h.get("weaknesses", [])),
                } for h in loc],
                use_container_width=True,
                height=264
            )

    with st.expander("👥 Chi tiết từng học sinh"):
        for h in ds:
            st.markdown(
                f"<div style='margin-bottom:4px;'><strong>{h.get('id')} — {h.get('ten', '')}</strong>"
                f"<span style='color:#64748b;font-size:0.85rem;margin-left:8px;'>({h.get('bai_hien_tai', 'Chưa chọn bài')})</span></div>",
                unsafe_allow_html=True,
            )
            widgets.tags(h.get("weaknesses", []), "chưa có điểm yếu")
            st.markdown("<hr style='margin:8px 0;border-color:#f1f5f9;'>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    widgets.section_title("🚨 Cảnh báo sớm <span style='font-size:13px;font-weight:600;color:#64748b;'>(sai >3 lần cùng 1 Bài)</span>")
    with st.container(border=True):
        cb = lop.canh_bao_hoc_sinh()
        if cb:
            st.dataframe([{"HS": f"{c['sid']} ({c['ten']})", "Bài": c["bai"],
                           "Số lần sai": c["so_lan_sai"]} for c in cb], use_container_width=True)
        else:
            st.caption("Chưa có em nào sai lặp — lớp đang ổn.")

    widgets.section_title("👥 Ghép nhóm cùng yếu 1 Bài")
    with st.container(border=True):
        goi_y = lop.goi_y_nhom()
        if not goi_y:
            st.info("Không còn gợi ý mới — hoặc HS đã vào nhóm mở, hoặc mỗi Bài còn lẻ 1 em, "
                    "hoặc HS chưa chọn Bài hiện tại (nhắc em vào Hồ sơ → Bài đang học).")
        for i, g in enumerate(goi_y):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**{g['bai']}** — {', '.join(g['thanh_vien'])}")
                st.caption(f"👉 Bấm Tạo nhóm → các em {', '.join(g['thanh_vien'])} sẽ thấy nhóm ở Trang chủ.")
            with c2:
                if st.button("Tạo nhóm", key=f"tao-nhom-{i}"):
                    ma = lop.tao_nhom(g["bai"], g["thanh_vien"], f"Ôn {g['bai']}")
                    st.success(f"Đã tạo nhóm {ma} cho {', '.join(g['thanh_vien'])}. "
                               f"Dặn các em đăng nhập đúng mã + mở Trang chủ → mục Nhóm học.")
                    st.rerun()
        nhom_mo = [n for n in lop.ds_nhom() if n.get("trang_thai") == "mo"]
        if nhom_mo:
            st.caption("Nhóm đang mở:")
            # Map id -> tên để GV đối chiếu mã đăng nhập của HS
            ten_theo_id = {h.get("id"): h.get("ten", h.get("id")) for h in ds}
            for n in nhom_mo:
                c1, c2 = st.columns([3, 1])
                with c1:
                    tv = n.get('thanh_vien', [])
                    tv_hien = ", ".join(f"{m} ({ten_theo_id.get(m, '?')})" for m in tv)
                    st.markdown(f"**{n['id']}** — {n['bai']}: {', '.join(tv)} ({n.get('muc_tieu', '')})")
                    st.caption(f"Thành viên: {tv_hien}")
                with c2:
                    if st.button("Kết thúc", key=f"dong-{n['id']}"):
                        lop.dong_nhom(n["id"])
                        st.rerun()
        else:
            st.caption("Chưa có nhóm nào đang mở.")

    st.markdown("<br>", unsafe_allow_html=True)
    widgets.section_title("🤖 Nhận xét chung bằng AI")
    if st.button("🤖 Tổng hợp bằng AI", type="primary"):
        with st.spinner("AI đang phân tích toàn lớp..."):
            try:
                bc = teacher.gv_bao_cao(mon)
                st.session_state["bc_gv"] = bc
            except Exception as e:
                st.error(str(e))
                return
    bc = st.session_state.get("bc_gv")
    if bc:
        st.markdown(bc)
        st.download_button("⬇️ Tải báo cáo (.md)", bc, file_name="bao-cao-lop.md")

