import base64
import streamlit as st
from core import student, store, conversations, subjects
from ui import widgets
from ui.theme import page_header


_MIME_ANH = {"png": "image/png", "jpg": "image/jpeg",
             "jpeg": "image/jpeg", "webp": "image/webp"}


def _file_sang_data_url(f):
    raw = f.getvalue()
    if len(raw) > 4 * 1024 * 1024:
        return None  # ảnh >4MB thì bỏ (đỡ tràn token)
    ext = (f.name.rsplit(".", 1)[-1].lower() if "." in (f.name or "") else "")
    mime = _MIME_ANH.get(ext) or getattr(f, "type", "") or "image/jpeg"
    return "data:%s;base64,%s" % (mime, base64.b64encode(raw).decode("ascii"))


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
        trinh_do = student.lay_trinh_do(sid, mon)
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

    # Composer kiểu chat app: nút 📎 đầu ô nhập (popover) + Enter để gửi
    if "chat_anh_ver" not in st.session_state:
        st.session_state.chat_anh_ver = 0
    goiy = st.session_state.pop("goiy_cauhoi", "")
    up_key = f"chat_anh_{st.session_state.chat_anh_ver}"
    with st.form(key=f"composer_{cid or 'new'}", clear_on_submit=True, border=False):
        c_attach, c_input, c_send = st.columns([0.7, 7.8, 0.9])
        with c_attach:
            with st.popover("📎", help="Đính kèm ảnh bài toán (tối đa 3 ảnh, mỗi ảnh <4MB)",
                            use_container_width=True):
                up_files = st.file_uploader(
                    "Ảnh bài toán", type=["png", "jpg", "jpeg", "webp"],
                    accept_multiple_files=True, key=up_key,
                    label_visibility="collapsed")
                st.caption("Tối đa 3 ảnh, mỗi ảnh <4MB.")
        with c_input:
            q = st.text_input(
                "Hỏi bài", value=goiy or "",
                placeholder=f"Hỏi bài {cfg['ten']}... (kèm ảnh nếu cần, Enter để gửi)",
                label_visibility="collapsed")
        with c_send:
            send = st.form_submit_button("➤", use_container_width=True)
    if up_files:
        st.image(up_files[:3], width=90)
    co_gui = send or bool(goiy)
    if goiy and not q:
        q = goiy
    if co_gui and (q or up_files):
        if not cid:  # chưa có cuộc nào -> tự tạo rồi chat
            cid = conversations.tao_cuoc(
                sid, bai=hs.get("bai_hien_tai", ""),
                cau_mo_dau=(q or "Hỏi qua ảnh"))
            st.session_state.cid = cid
        data_urls = []
        if up_files:
            for f in up_files[:3]:
                url = _file_sang_data_url(f)
                if url:
                    data_urls.append(url)
            if len(up_files) > 3:
                st.caption("Chỉ gửi 3 ảnh đầu để đỡ tốn token.")
            if up_files and not data_urls:
                st.error("Ảnh quá lớn (>4MB). Bạn nén/chụp lại giúp mình nhé.")
                return
        with st.chat_message("user"):
            if q:
                st.markdown(q)
            if up_files:
                st.image(up_files[:3], width=220)
        with st.spinner("AI đang xem ảnh và dẫn dắt từng bước..."):
            try:
                tra_loi, extra = student.hs_chat(
                    sid, q or "", cid=cid, mon=mon, hinh_data_urls=data_urls)
            except Exception as e:
                msg = str(e) or "AI chưa trả lời được."
                # Lỗi kỹ thuật thường tiếng Anh -> dịch gọn sang tiếng Việt cho HS
                if "not iterable" in msg or "NoneType" in msg:
                    msg = "AI chưa trả kết quả, bạn gửi lại câu hỏi giúp mình nhé."
                elif "OPENROUTER_API_KEY" in msg:
                    msg = "Giáo viên chưa cấu hình API key, bạn báo giáo viên nhé."
                elif "API lỗi" in msg or "Lỗi mạng" in msg:
                    msg = "Mạng/model đang bận, bạn đợi chút rồi gửi lại nhé."
                st.error(msg)
                return
        with st.chat_message("assistant"):
            st.markdown(tra_loi)
            # Minh bạch accuracy (ưu tiên 1): hiện căn cứ bank + model đã trả lời.
            can_cu = extra.get("can_cu") or []
            if can_cu:
                st.caption("Căn cứ kho GV: " + ", ".join(can_cu))
            else:
                st.caption("Câu ngoài kho GV — AI đã tự kiểm tra lại, nếu chưa chắc bạn gửi thêm dữ kiện nhé.")
            try:
                from core import llm as _llm
                st.caption(f"Model: {_llm.LAST_MODEL} | temp thấp (accuracy trước)")
            except Exception:
                pass
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
        if extra.get("cau_tu_soan"):
            st.markdown("**Bài AI tự soạn (kho chưa có đúng dạng, đáp án theo đúng công thức chuẩn — GV sẽ duyệt sau):**")
            for c in extra["cau_tu_soan"]:
                with st.expander(f"{c.get('id')} • {c.get('dang_phan')} • AI tự soạn", expanded=False):
                    st.markdown(c.get("de", ""))
                    with st.expander("Xem đáp án"):
                        st.markdown(c.get("dap_an", ""))
                        for i, b in enumerate(c.get("buoc_giai", []), 1):
                            st.markdown(f"Bước {i}: {b}")
        if extra.get("diem_yeu"):
            st.warning("Ghi nhận điểm yếu: " + ", ".join(extra["diem_yeu"]))
        if up_files:
            st.session_state.chat_anh_ver += 1  # xóa ảnh đã gửi, tránh gửi lặp
        st.rerun()
