import os
import streamlit as st
from core import exercises, grading, store, curriculum
from ui import widgets
from ui.theme import page_header
ATTEMPT_DIR = os.path.join("data", "attempts")


def _attempts(sid):
    if not os.path.isdir(ATTEMPT_DIR):
        return []
    ds = []
    for ten in sorted(os.listdir(ATTEMPT_DIR), reverse=True):
        if ten.startswith(sid + "_") and ten.endswith(".json"):
            ds.append(store.doc_json(os.path.join(ATTEMPT_DIR, ten), {}))
    return ds


def _tin_cau_moi(cau):
    """Tin nhắn bot khi ra đề (chỉ đề + meta, không lộ đáp án)."""
    nguon = cau.get("nguon", "")
    tag = "kho GV" if "kho GV" in nguon else "AI sinh"
    return (f"📝 **Câu {cau.get('id')}** • {cau.get('bai')} • "
            f"Độ khó {cau.get('do_kho')} {widgets.do_kho_sao(cau.get('do_kho', 2))} • _{tag}_\n\n"
            f"{cau.get('de')}\n\n_Viết mỗi bước giải 1 dòng rồi gửi để thầy chấm nhé._")


def _tin_cham(kq):
    dong = []
    for i, ok in enumerate(kq.get("dung_sai_tung_buoc", []), 1):
        dong.append(f"{'✅' if ok else '❌'} Bước {i}: {'đúng' if ok else 'sai'}")
    if kq.get("dung_het"):
        dong.append("\n🎉 **Đúng hết!** Bấm *Câu tiếp theo* để lên độ khó.")
    else:
        buoc = kq.get("sai_o_buoc")
        dong.append(f"\n⚠️ Sai ở **bước {buoc}**." if buoc else "\n⚠️ Chưa xác định được bước sai.")
        if kq.get("goi_y_sua"):
            dong.append(f"💡 Gợi ý: {kq['goi_y_sua']}")
        if kq.get("diem_yeu_moi"):
            dong.append("📝 Điểm yếu mới: " + ", ".join(kq["diem_yeu_moi"]))
    return "\n".join(dong)


def render(sid, mon="toan11"):
    atts = _attempts(sid)
    dung = sum(1 for a in atts if a.get("dung_het"))

    # Banner nhóm: để HS biết mình đang làm bài nhóm nào (GV tạo ở Báo cáo lớp)
    try:
        from core import lop as lop_core
        nhom_hs = lop_core.nhom_cua_hs(sid)
        if nhom_hs:
            for n in nhom_hs[:2]:
                st.info(f"👥 Bạn đang ở nhóm **{n.get('id', '')}** — {n.get('bai', '')} "
                        f"cùng {', '.join(n.get('thanh_vien', []))} "
                        f"({n.get('muc_tieu', '')}). Hãy luyện đúng Bài này nhé!")
        else:
            st.caption(f"Chưa vào nhóm nào (mã: {sid}) — GV ghép ở Báo cáo lớp → Ghép nhóm.")
    except Exception:
        pass
    
    if "luyen_messages" not in st.session_state:
        st.session_state.luyen_messages = []
    if "luyen_ids" not in st.session_state:
        st.session_state.luyen_ids = []

    def _loai_tru():
        return set(st.session_state.get("luyen_ids", []))

    def _nhan_cau_moi(cau):
        st.session_state["cau_hien_tai"] = cau
        st.session_state.pop("kq_cuoi", None)
        st.session_state.luyen_messages.append({"role": "assistant", "content": _tin_cau_moi(cau)})
        st.session_state["cau_da_hien"] = cau.get("id")
        ids = st.session_state.get("luyen_ids", [])
        if cau.get("id") not in ids:
            ids.append(cau.get("id"))
        st.session_state.luyen_ids = ids[-200:]
        
    # Header (tiêu đề trang đã có ở header chung app.py — ở đây chỉ giữ dòng mô tả)
    c_title, c_new = st.columns([3, 1])
    with c_title:
        st.markdown("<p style='font-size:15px; color:#64748b; margin:8px 0 16px 0; text-align:center;'>Thầy ra đề trong chat — em nhắn từng bước giải, mỗi bước 1 dòng</p>", unsafe_allow_html=True)
    with c_new:
        st.markdown("<div style='height: 4px'></div>", unsafe_allow_html=True)
        cau_hien_tai = st.session_state.get("cau_hien_tai")
        nhan = "Phát đề tiếp theo" if cau_hien_tai else "Bắt đầu luyện tập"
        if st.button(nhan, type="primary", use_container_width=True):
            # Same logic as lay_moi / tiep
            kq_cu = st.session_state.get("kq_cuoi")
            if cau_hien_tai and kq_cu is None:
                # Chưa nộp bài cũ -> giữ nguyên độ khó, chỉ đổi sang câu chưa gặp
                do_kho_chon = cau_hien_tai.get("do_kho", 2)
                bai_chon = cau_hien_tai.get("bai")
            elif cau_hien_tai:
                lam_dung = bool(kq_cu and kq_cu.get("dung_het"))
                do_kho_chon = exercises.doi_kho_hien_tai(sid, cau_hien_tai.get("bai"), cau_hien_tai.get("do_kho", 2), lam_dung)
                bai_chon = cau_hien_tai.get("bai")
            else:
                do_kho_chon = 2
                ds_bai = [v["title"] for v in curriculum.load_videos(mon)]
                bai_chon = ds_bai[0] if ds_bai else ""
                
            # If user explicitly set them in popover, it will override.
            # Wait, we need to read session state for popover settings if we want to override.
            # Actually, let's keep it simple.
            
            with st.spinner("Đang tìm bài trong kho..."):
                try:
                    cau = exercises.ra_bai(sid, bai_chon, do_kho_chon, mon,
                                           loai_tru=_loai_tru(),
                                           cau_hien_tai_id=(cau_hien_tai or {}).get("id"))
                    _nhan_cau_moi(cau)
                except Exception as e:
                    st.error(str(e))
            st.rerun()

    # Badges & Settings
    c_badge, c_settings = st.columns([3, 1])
    with c_badge:
        tl = round(dung/len(atts)*100) if atts else 0
        hs0 = store.doc_hs(sid)
        trinh0 = hs0.get("trinh_do_toan", "trung bình")
        try:
            diem0 = int(hs0.get("diem_trinh_do", 0) or 0)
        except (TypeError, ValueError):
            diem0 = 0
        st.html(f"""
            <div style='display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin-bottom: 24px;'>
                <div style='background:#f1f5f9; color:#475569; padding:6px 14px; border-radius:20px; font-size:13px; font-weight:600;'>📝 Đã luyện: {len(atts)}</div>
                <div style='background:#dcfce7; color:#16a34a; padding:6px 14px; border-radius:20px; font-size:13px; font-weight:600;'>✓ Đúng hết: {dung}</div>
                <div style='background:#eff6ff; color:#2563eb; padding:6px 14px; border-radius:20px; font-size:13px; font-weight:600;'>📈 Tỉ lệ đúng: {tl}%</div>
                <div title='Đúng +1, sai -1; đủ +5 lên bậc, -5 xuống bậc' style='background:#fefce8; color:#a16207; padding:6px 14px; border-radius:20px; font-size:13px; font-weight:600;'>🎚 {trinh0} ({diem0:+d})</div>
            </div>
        """)
        
    with c_settings:
        with st.popover("⚙️ Cài đặt đề", use_container_width=True):
            ds_bai = [v["title"] for v in curriculum.load_videos(mon)]
            bai = st.selectbox("Chọn Bài", ds_bai, index=0 if ds_bai else None)
            do_kho = st.selectbox("Độ khó", [1, 2, 3], index=1, format_func=lambda n: f"{n} {widgets.do_kho_sao(n)}")
            
            b1, b2 = st.columns(2)
            with b1:
                if st.button("Câu mới", use_container_width=True):
                    with st.spinner("Tìm..."):
                        try:
                            cau_ht = st.session_state.get("cau_hien_tai") or {}
                            cau = exercises.ra_bai(sid, bai, do_kho, mon,
                                                   loai_tru=_loai_tru(),
                                                   cau_hien_tai_id=cau_ht.get("id"))
                            _nhan_cau_moi(cau)
                        except Exception as e:
                            st.error(str(e))
                    st.rerun()
            with b2:
                if st.button("Bắt đầu lại", use_container_width=True):
                    st.session_state.luyen_messages = []
                    st.session_state.luyen_ids = []
                    st.session_state.pop("cau_hien_tai", None)
                    st.session_state.pop("cau_da_hien", None)
                    st.session_state.pop("kq_cuoi", None)
                    st.rerun()

    st.markdown("<hr style='margin: 0 0 24px 0; border-color: #f1f5f9;'>", unsafe_allow_html=True)

    # Câu nạp từ tab Chat ("Làm câu này") chưa có tin nhắn bot -> dựng tin nhắn
    cau = st.session_state.get("cau_hien_tai")
    if cau and st.session_state.get("cau_da_hien") != cau.get("id"):
        st.session_state.luyen_messages.append({"role": "assistant", "content": _tin_cau_moi(cau)})
        st.session_state["cau_da_hien"] = cau.get("id")
        ids = st.session_state.get("luyen_ids", [])
        if cau.get("id") not in ids:
            ids.append(cau.get("id"))
        st.session_state.luyen_ids = ids[-200:]

    # Lịch sử chat luyện tập
    for m in st.session_state.luyen_messages[-40:]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    cau = st.session_state.get("cau_hien_tai")
    if cau and cau.get("buoc_giai"):
        with st.expander("Xem bước chuẩn (chỉ mở khi đã cố gắng)"):
            for i, b in enumerate(cau["buoc_giai"], 1):
                st.markdown(f"{i}. {b}")

    if not cau:
        st.info("Bấm **Câu mới** để thầy ra đề. Ưu tiên kho GV, hết mới sinh.")
        return
    tra_loi = st.chat_input("Viết bài làm (mỗi bước 1 dòng) — hoặc nhắn 'không biết, hướng dẫn em'...")
    if not tra_loi:
        with st.expander(f"Lịch sử luyện ({len(atts)})"):
            for a in atts[:10]:
                icon = "✅" if a.get("dung_het") else "❌"
                st.markdown(f"{icon} **{a.get('cau_id')}** — {a.get('bai', '')}: {a.get('de', '')[:80]}")
        return
    cac_buoc = [d.strip() for d in tra_loi.splitlines() if d.strip()]
    if not cac_buoc:
        cac_buoc = [tra_loi.strip()]
    st.session_state.luyen_messages.append({"role": "user", "content": tra_loi})
    with st.chat_message("user"):
        st.markdown(tra_loi)
    if grading.la_xin_goi_y(tra_loi):
        # Xin gợi ý: hỏi Socrates đúng bước 1, KHÔNG chấm, KHÔNG lưu rớt
        with st.spinner("Thầy đang nghĩ cách gợi mở..."):
            try:
                kq = grading.goi_y_buoc_dau(sid, cau, mon)
            except Exception as e:
                st.error(str(e))
                return
        st.session_state.luyen_messages.append(
            {"role": "assistant", "content": f"💡 {kq['goi_y']}\n\n_Em thử làm bước 1 rồi nhắn tiếp nhé._"})
        st.rerun()
    cac_buoc = [d.strip() for d in tra_loi.splitlines() if d.strip()]
    if not cac_buoc:
        cac_buoc = [tra_loi.strip()]
    with st.spinner("Thầy đang chấm từng bước..."):
        try:
            kq, _ = grading.cham_tung_buoc(sid, cau, cac_buoc, mon)
            st.session_state["kq_cuoi"] = kq
        except Exception as e:
            st.error(str(e))
            return
    st.session_state.luyen_messages.append({"role": "assistant", "content": _tin_cham(kq)})
    if kq.get("trinh_do_moi"):
        from core.student import TRINH_DO
        tm = kq["trinh_do_moi"]
        len_huong = "tiến bộ, bài tiếp theo sẽ thử thách hơn" if TRINH_DO.index(tm["moi"]) > TRINH_DO.index(tm["cu"]) \
            else "cần chắc lại nền tảng, bài tiếp theo sẽ nhẹ nhàng hơn"
        st.session_state.luyen_messages.append(
            {"role": "assistant",
             "content": f"📈 Trình độ của em: **{tm['cu']} → {tm['moi']}** ({len_huong})."})
    st.rerun()
