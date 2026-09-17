import streamlit as st
from core import student, store, conversations, subjects
from ui import widgets
from ui.theme import page_header


def _dong_bo_chon_cuoc():
    st.session_state["cid"] = st.session_state["cid_chon"]


def render(sid, mon="toan11"):
    cfg = subjects.lay_mon(mon)
    
    ds = conversations.ds_cuoc(sid)
    if "cid" not in st.session_state:
        st.session_state.cid = ds[0]["id"] if ds else ""
    if not conversations.lay_cuoc(sid, st.session_state.cid):
        st.session_state.cid = ds[0]["id"] if ds else ""
    cid = st.session_state.cid
    cuoc = conversations.lay_cuoc(sid, cid) if cid else None

    # Header with title and new chat button inline
    # (tiêu đề trang đã có ở header chung app.py — ở đây chỉ giữ dòng mô tả + nút)
    c_title, c_new = st.columns([3, 1])
    with c_title:
        st.markdown("<p style='font-size:15px; color:#64748b; margin:8px 0 16px 0; text-align:center;'>Hỏi từng bước nhỏ — AI dẫn dắt, không mớm đáp án</p>", unsafe_allow_html=True)
    with c_new:
        st.markdown("<div style='height: 4px'></div>", unsafe_allow_html=True)
        if st.button("＋ Trò chuyện mới", type="primary", use_container_width=True):
            st.session_state.cid = conversations.tao_cuoc(sid, bai=store.doc_hs(sid).get("bai_hien_tai", ""))
            st.rerun()

    # Context badges and History popover
    c_badge, ch2 = st.columns([3.25, 0.75])
    with c_badge:
        bai_hien_tai = cuoc.get("bai") if cuoc and cuoc.get("bai") else store.doc_hs(sid).get("bai_hien_tai", "Chưa chọn bài")
        trinh_do = store.doc_hs(sid).get("trinh_do_toan", "trung bình")
        st.html(f"""
            <div style='display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin-bottom: 24px;'>
                <div style='background:#f1f5f9; color:#475569; padding:6px 14px; border-radius:20px; font-size:13px; font-weight:600;'>📌 {bai_hien_tai}</div>
                <div style='background:#eff6ff; color:#2563eb; padding:6px 14px; border-radius:20px; font-size:13px; font-weight:600;'>🎯 Trình độ: {trinh_do}</div>
            </div>
        """)

    with ch2:
        with st.popover("🕒 Lịch sử", use_container_width=True):
            if ds:
                lua_chon = {c["id"]: f"{c['tieu_de']} ({len(c.get('messages', [])) // 2} lượt)" for c in ds}
                st.session_state.cid_chon = cid if cid in lua_chon else ""
                st.selectbox("Chọn đoạn chat", [""] + list(lua_chon),
                             format_func=lambda x: "— Chọn đoạn chat —" if not x else lua_chon.get(x, x),
                             key="cid_chon", on_change=_dong_bo_chon_cuoc)
                if st.button("🗑 Xóa đoạn chat này", disabled=not cid, use_container_width=True):
                    conversations.xoa_cuoc(sid, cid)
                    st.session_state.cid = ""
                    st.rerun()
            else:
                st.info("Chưa có lịch sử")

    st.markdown("<hr style='margin: 0 0 24px 0; border-color: #f1f5f9;'>", unsafe_allow_html=True)

    hs = store.doc_hs(sid)

    # Chỉ hiện câu mẫu khi chưa có cuộc nào (đỡ chật màn hình)
    mau_list = widgets.cau_hoi_mau(mon)
    if not ds and mau_list:
        st.markdown("**Thử 1 câu mẫu:**")
        cols = st.columns(len(mau_list))
        for col, mau in zip(cols, mau_list):
            if col.button(mau[:28] + "...", key=f"chat-mau-{mau[:10]}", help=mau):
                st.session_state["goiy_cauhoi"] = mau

    # Hiện tin nhắn của cuộc đang mở
    for m in (cuoc.get("messages", []) if cuoc else [])[-30:]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    q = st.chat_input(f"Hỏi bài {cfg['ten']}...")
    goiy = st.session_state.pop("goiy_cauhoi", "")
    if goiy and not q:
        q = goiy
        st.info(f"Câu mẫu: {q}")
    if q:
        if not cid:  # chưa có cuộc nào -> tự tạo rồi chat
            cid = conversations.tao_cuoc(sid, bai=hs.get("bai_hien_tai", ""), cau_mo_dau=q)
            st.session_state.cid = cid
        with st.chat_message("user"):
            st.markdown(q)
        with st.spinner("AI đang dẫn dắt từng bước..."):
            try:
                tra_loi, extra = student.hs_chat(sid, q, cid=cid, mon=mon)
            except Exception as e:
                msg = str(e) or "AI chưa trả lời được."
                # Lỗi kỹ thuật thường tiếng Anh -> dịch gọn sang tiếng Việt cho HS
                if "not iterable" in msg or "NoneType" in msg:
                    msg = "AI chưa trả kết quả, bạn gửi lại câu hỏi giúp mình nhé."
                elif "OPENROUTER_API_KEY" in msg:
                    msg = "Thầy chưa cấu hình API key, bạn báo thầy nhé."
                elif "API lỗi" in msg or "Lỗi mạng" in msg:
                    msg = "Mạng/model đang bận, bạn đợi chút rồi gửi lại nhé."
                st.error(msg)
                return
        with st.chat_message("assistant"):
            st.markdown(tra_loi)
        if extra.get("video"):
            v = extra["video"]
            with st.expander(f"Video gợi ý: {v['title']}", expanded=True):
                widgets.video_card(v, key_prefix="chat")
                hs_now = store.doc_hs(sid)
                if v["link"] not in hs_now.get("video_da_xem", []):
                    if st.button("✓ Đã xem video này", key=f"dx-{v['link'][-11:]}"):
                        from core import student as _st
                        _st.ghi_nhan_video(sid, v["link"])
                        st.success("Đã ghi nhận. AI sẽ gợi ý video tiếp theo.")
                        st.rerun()
        if extra.get("cau_goi_y"):
            st.markdown("**Bài nên làm tiếp (từ kho GV):**")
            for c in extra["cau_goi_y"]:
                with st.expander(f"{c.get('id')} • {c.get('bai')} • khó {c.get('do_kho')}", expanded=False):
                    st.markdown(c.get("de", ""))
                    if st.button("Làm câu này", key=f"lam-{c.get('id')}", type="primary"):
                        from core import exercises
                        cau = exercises.lay_cau_theo_id(sid, c.get("id"), mon)
                        if cau:
                            st.session_state["cau_hien_tai"] = cau
                            st.session_state.pop("kq_cuoi", None)
                            st.success("Đã nạp câu vào tab Luyện tập. Sang đó để làm bài.")
                        else:
                            st.error("Câu này chưa đạt chuẩn duyệt.")
        elif extra.get("bai_de_xuat"):
            st.info("Bài nên làm tiếp:\n- " + "\n- ".join(extra["bai_de_xuat"]))
            if st.button("Sang Luyện tập ngay"):
                st.info("Sang tab Luyện tập ở sidebar để làm bài.")
        if extra.get("diem_yeu"):
            st.warning("Ghi nhận điểm yếu: " + ", ".join(extra["diem_yeu"]))
        st.rerun()
