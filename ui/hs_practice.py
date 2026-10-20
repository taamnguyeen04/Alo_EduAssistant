"""Luyện tập trắc nghiệm: 4 phương án A-D + E 'Mình không biết'.

Luồng:
- HS chọn bài giảng -> phát 1 câu TN đúng trình độ per-Bài (1 Nhận biết /
  2 Thông hiểu / 3 Vận dụng), trình độ đổi CHẬM (ngưỡng + đủ số câu).
- Chọn A-D: chấm local tuyệt đối, hiện đáp án + bước giải ngay.
- Chọn E: trừ điểm nhẹ, AI sinh 2-3 câu TN con dẫn dắt (lưu điểm yếu vào
  hồ sơ), rồi cho chọn lại câu gốc đúng 1 lần mới hiện đáp án thật.
Công thức render qua bank_view.lam_dep_hien_thi + st.markdown (KaTeX $...$).
"""
import base64
import os
import streamlit as st
from core import bank_view, exercises, grading, store
from core.student import lay_trinh_do_bai, ten_muc_do
from ui import widgets

ATTEMPT_DIR = os.path.join("data", "attempts")

_E_LABEL = "E — Mình không biết làm bài này"

_MIME_ANH = {"png": "image/png", "jpg": "image/jpeg",
             "jpeg": "image/jpeg", "webp": "image/webp"}


def _file_sang_data_url(f):
    raw = f.getvalue()
    if len(raw) > 4 * 1024 * 1024:
        return None
    ext = (f.name.rsplit(".", 1)[-1].lower() if "." in (f.name or "") else "")
    mime = _MIME_ANH.get(ext) or getattr(f, "type", "") or "image/jpeg"
    return "data:%s;base64,%s" % (mime, base64.b64encode(raw).decode("ascii"))


def _attempts(sid, bai=None):
    if not os.path.isdir(ATTEMPT_DIR):
        return []
    ds = []
    for ten in sorted(os.listdir(ATTEMPT_DIR), reverse=True):
        if ten.startswith(sid + "_") and ten.endswith(".json"):
            d = store.doc_json(os.path.join(ATTEMPT_DIR, ten), {})
            if bai and d.get("bai") != bai:
                continue
            ds.append(d)
    return ds


def _reset_cau():
    for k in ("tn_cau", "tn_che_do", "tn_kq", "tn_con", "tn_con_idx",
              "tn_con_kq", "tn_yeu"):
        st.session_state.pop(k, None)


def _phat_de(sid, bai, mon):
    tri = lay_trinh_do_bai(sid, bai)
    cau = exercises.ra_bai_tn(
        sid, bai, tri["level"], mon,
        loai_tru=set(st.session_state.get("tn_ids", [])),
        cau_hien_tai_id=(st.session_state.get("tn_cau") or {}).get("id"))
    st.session_state["tn_cau"] = cau
    st.session_state["tn_che_do"] = "lam_bai"
    for k in ("tn_kq", "tn_con", "tn_con_idx", "tn_con_kq", "tn_yeu"):
        st.session_state.pop(k, None)
    ids = st.session_state.get("tn_ids", [])
    if cau.get("id") not in ids:
        ids.append(cau.get("id"))
    st.session_state["tn_ids"] = ids[-200:]


def _hienLuaChon(phuong_an):
    """Hiện nội dung A-D bằng markdown riêng để KaTeX $...$ luôn render đúng."""
    for nhan, nd in phuong_an:
        st.markdown(f"**{nhan}.** {nd or '*(trống)*'}")


def _badge_trinh_do(tri):
    muc = ten_muc_do(tri["level"])
    return (f"🎚 {muc} (mức {tri['level']}/3) • "
            f"điểm đệm {tri['diem']:+g} • đã làm {tri['so_cau']} câu")


def render(sid, mon="toan11"):
    tab_tn, tab_tl = st.tabs(["Trắc nghiệm", "Tự luận"])
    with tab_tn:
        _render_tn(sid, mon)
    with tab_tl:
        _render_tl(sid, mon)


def _render_tn(sid, mon="toan11"):
    ds_bai = exercises.ds_bai_tn(mon)
    if not ds_bai:
        st.warning("Kho chưa có câu trắc nghiệm dùng được — nhờ GV bổ sung ở Kho đề.")
        return
    hs = store.doc_hs(sid)
    bai_mac_dinh = hs.get("bai_hien_tai", "") or sorted(ds_bai)[0]
    if bai_mac_dinh not in ds_bai:
        bai_mac_dinh = sorted(ds_bai)[0]

    c_bai, c_muc = st.columns([2.2, 1])
    with c_bai:
        bai = st.selectbox(
            "Bài giảng",
            sorted(ds_bai),
            index=sorted(ds_bai).index(bai_mac_dinh),
            format_func=lambda b: f"{b} ({ds_bai[b]} câu TN)",
            key="tn_bai")
    if bai != hs.get("bai_hien_tai"):
        hs["bai_hien_tai"] = bai
        store.luu_hs(sid, hs)
    if st.session_state.get("tn_bai_da_chon") != bai:
        st.session_state["tn_bai_da_chon"] = bai
        _reset_cau()
    tri = lay_trinh_do_bai(sid, bai)
    with c_muc:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        st.caption(f"Mức hiện tại: **{ten_muc_do(tri['level'])}**")

    atts = _attempts(sid, bai)
    dung = sum(1 for a in atts if a.get("dung_het") or a.get("dung"))
    st.html(
        "<div style='display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin:8px 0 16px 0;'>"
        f"<div style='background:#f1f5f9; color:#475569; padding:6px 14px; border-radius:20px; font-size:13px; font-weight:600;'>📝 Bài này đã luyện: {len(atts)}</div>"
        f"<div style='background:#dcfce7; color:#16a34a; padding:6px 14px; border-radius:20px; font-size:13px; font-weight:600;'>✓ Đúng: {dung}</div>"
        f"<div title='Đúng +1 (VD +1.5), sai -1, không biết -0.5; đủ +4 lên mức, -3 xuống mức (tối thiểu 6 câu)' style='background:#fefce8; color:#a16207; padding:6px 14px; border-radius:20px; font-size:13px; font-weight:600;'>{_badge_trinh_do(tri)}</div>"
        "</div>")

    # Nhận câu từ tab Chat ("Làm câu này") nếu là TN dùng được.
    if not st.session_state.get("tn_cau") and st.session_state.get("cau_hien_tai"):
        raw = st.session_state.pop("cau_hien_tai")
        st.session_state.pop("cau_da_hien", None)
        if isinstance(raw, dict) and exercises.cau_tn_dung_duoc(raw):
            st.session_state["tn_cau"] = exercises.lam_giau_tn(raw)
            st.session_state["tn_che_do"] = "lam_bai"
        elif isinstance(raw, dict) and raw.get("id"):
            st.info(f"Câu {raw.get('id')} là tự luận/chưa đủ chuẩn trắc nghiệm nên mình phát câu TN khác — bạn bấm Phát đề nhé.")

    cau = st.session_state.get("tn_cau")
    if not cau:
        st.info("Bấm **Phát đề** để bắt đầu. Mỗi lượt 1 câu trắc nghiệm đúng trình độ của bạn ở Bài này.")
        if st.button("▶ Phát đề", type="primary", use_container_width=True):
            try:
                with st.spinner("Đang tìm câu trắc nghiệm..."):
                    _phat_de(sid, bai, mon)
            except Exception as e:
                st.error(str(e))
                return
            st.rerun()
        return

    che_do = st.session_state.get("tn_che_do", "lam_bai")
    meta = f"📝 **Câu {cau.get('id')}** • {widgets.muc_do_label(cau.get('do_kho', 1))}"
    if cau.get("dang_phan"):
        meta += f" • {cau['dang_phan']}"
    st.markdown(meta)
    with st.container(border=True):
        st.markdown(cau.get("than_de", ""))

    if che_do == "lam_bai":
        st.markdown("**Chọn đáp án:**")
        _hienLuaChon(cau.get("phuong_an", []))
        chon = st.radio("Đáp án của em", ["A", "B", "C", "D", _E_LABEL],
                        index=None, key=f"tn_chon_{cau.get('id')}")
        c_nop, c_bo = st.columns([1, 1])
        with c_nop:
            nop = st.button("Trả lời", type="primary", use_container_width=True)
        with c_bo:
            bo = st.button("Câu khác", use_container_width=True)
        if bo:
            try:
                with st.spinner("Đang đổi câu..."):
                    _phat_de(sid, bai, mon)
            except Exception as e:
                st.error(str(e))
                return
            st.rerun()
        if not nop:
            return
        if not chon:
            st.warning("Bạn chọn 1 phương án (A–E) rồi bấm Trả lời nhé.")
            return
        if chon == _E_LABEL:
            grading.ghi_nhan_khong_biet(sid, cau, mon)
            with st.spinner("Mình đang soạn câu dẫn dắt cho bạn..."):
                cons, yeu = grading.sinh_cau_dan_dat(sid, cau, mon)
            st.session_state["tn_con"] = cons
            st.session_state["tn_con_idx"] = 0
            st.session_state["tn_con_kq"] = []
            st.session_state["tn_yeu"] = yeu
            st.session_state["tn_che_do"] = "dan_dat"
            st.rerun()
        kq = grading.cham_trac_nghiem(sid, cau, chon, mon)
        st.session_state["tn_kq"] = kq
        st.session_state["tn_che_do"] = "ket_qua"
        st.rerun()

    elif che_do == "ket_qua":
        kq = st.session_state.get("tn_kq", {})
        _hien_ket_qua_cuoi(cau, kq, False)
        if st.button("Câu tiếp theo →", type="primary", use_container_width=True):
            try:
                with st.spinner("Đang tìm câu tiếp theo..."):
                    _phat_de(sid, bai, mon)
            except Exception as e:
                st.error(str(e))
                return
            st.rerun()

    elif che_do == "dan_dat":
        cons = st.session_state.get("tn_con", [])
        idx = st.session_state.get("tn_con_idx", 0)
        if idx >= len(cons):
            st.session_state["tn_che_do"] = "lam_lai"
            st.rerun()
            return
        cc = cons[idx]
        st.info(f"💡 Bạn chọn chưa biết làm — mình đi từng bước nhỏ nhé "
                f"(câu dẫn dắt {idx + 1}/{len(cons)}). Trả lời xong bạn được chọn lại câu gốc 1 lần.")
        with st.container(border=True):
            st.markdown(f"**Dẫn dắt {idx + 1}:** {cc.get('de', '')}")
            for i, nd in enumerate(cc.get("phuong_an", [])):
                st.markdown(f"**{'ABCD'[i]}.** {bank_view.hien_thi(nd)}")
        chon = st.radio("Đáp án", ["A", "B", "C", "D"], index=None,
                        key=f"tn_con_{cau.get('id')}_{idx}")
        if st.button("Trả lời câu dẫn dắt", type="primary", use_container_width=True):
            if not chon:
                st.warning("Bạn chọn A–D nhé.")
                return
            dung = chon == cc.get("dap_an")
            kqs = st.session_state.get("tn_con_kq", [])
            kqs.append(dung)
            st.session_state["tn_con_kq"] = kqs
            st.session_state[f"tn_con_dung_{idx}"] = dung
            st.session_state[f"tn_con_chon_{idx}"] = chon
            st.rerun()
        if f"tn_con_dung_{idx}" in st.session_state:
            dung = st.session_state[f"tn_con_dung_{idx}"]
            if dung:
                st.success(f"✅ Đúng rồi! {cc.get('giai_thich', '')}")
            else:
                st.error(f"❌ Chưa đúng — đáp án là **{cc.get('dap_an')}**. {cc.get('giai_thich', '')}")
            if st.button("Tiếp tục →", type="primary", use_container_width=True):
                for k in (f"tn_con_dung_{idx}", f"tn_con_chon_{idx}", f"tn_con_{cau.get('id')}_{idx}"):
                    st.session_state.pop(k, None)
                st.session_state["tn_con_idx"] = idx + 1
                st.rerun()

    elif che_do == "lam_lai":
        st.success("Bạn đã đi qua các bước dẫn dắt — giờ chọn lại câu gốc 1 lần nhé (đúng vẫn được cộng điểm bù).")
        with st.container(border=True):
            st.markdown(cau.get("than_de", ""))
            _hienLuaChon(cau.get("phuong_an", []))
        chon = st.radio("Chọn lại đáp án", ["A", "B", "C", "D"], index=None,
                        key=f"tn_lamlai_{cau.get('id')}")
        if st.button("Chốt đáp án", type="primary", use_container_width=True):
            if not chon:
                st.warning("Bạn chọn A–D nhé.")
                return
            kq = grading.cham_lam_lai(sid, cau, chon,
                                      st.session_state.get("tn_yeu", []), mon)
            st.session_state["tn_kq"] = kq
            st.session_state["tn_che_do"] = "xong_lam_lai"
            st.rerun()

    elif che_do == "xong_lam_lai":
        kq = st.session_state.get("tn_kq", {})
        _hien_ket_qua_cuoi(cau, kq, True)
        if st.button("Câu tiếp theo →", type="primary", use_container_width=True):
            try:
                with st.spinner("Đang tìm câu tiếp theo..."):
                    _phat_de(sid, bai, mon)
            except Exception as e:
                st.error(str(e))
                return
            st.rerun()

    with st.expander(f"Lịch sử Bài này ({len(atts)})"):
        for a in atts[:15]:
            icon = "✅" if (a.get("dung_het") or a.get("dung")) else "❌"
            loai = {"khong_biet": " (không biết)", "lam_lai": " (làm lại)"}.get(a.get("loai", ""), "")
            st.markdown(f"{icon} **{a.get('cau_id')}**{loai} — chọn {a.get('chon', '?')}")


def _hien_ket_qua_cuoi(cau, kq, la_lam_lai):
    if kq.get("dung"):
        st.success(f"🎉 **Đúng rồi!** Đáp án là **{kq.get('dap_an_dung')}**."
                   + (" (cộng điểm bù sau dẫn dắt)" if la_lam_lai else ""))
    else:
        st.error(f"❌ Chưa đúng. Bạn chọn **{kq.get('chon', '?')}** — đáp án đúng là "
                 f"**{kq.get('dap_an_dung')}**.")
    if kq.get("diem_yeu_moi"):
        st.warning("📝 Điểm yếu mình ghi nhận: " + ", ".join(kq["diem_yeu_moi"]))
    with st.expander("Xem bước giải chuẩn", expanded=False):
        for i, b in enumerate(cau.get("buoc_giai", []) or [], 1):
            st.markdown(f"{i}. {bank_view.hien_thi(b)}")
    if kq.get("trinh_do_moi"):
        tm = kq["trinh_do_moi"]
        st.info(f"📈 Mức độ Bài này: **{tm['cu']} → {tm['moi']}**.")


# ── Luyện tự luận: phát đề → làm ra vở → chụp ảnh nộp ──────────────────

def _reset_tl():
    for k in ("tl_cau", "tl_kq", "tl_goi_y"):
        st.session_state.pop(k, None)


def _phat_de_tl(sid, bai, mon):
    tri = lay_trinh_do_bai(sid, bai)
    cau = exercises.ra_bai_tl(
        sid, bai, tri["level"], mon,
        loai_tru=set(st.session_state.get("tl_ids", [])),
        cau_hien_tai_id=(st.session_state.get("tl_cau") or {}).get("id"))
    st.session_state["tl_cau"] = cau
    st.session_state.pop("tl_kq", None)
    st.session_state.pop("tl_goi_y", None)
    ids = st.session_state.get("tl_ids", [])
    if cau.get("id") not in ids:
        ids.append(cau.get("id"))
    st.session_state["tl_ids"] = ids[-200:]


def _render_tl(sid, mon="toan11"):
    """Tab tự luận: HS nhận đề, giải vào vở, chụp ảnh tải lên để AI chấm."""
    ds_bai = exercises.ds_bai_tl(mon)
    if not ds_bai:
        st.warning("Kho chưa có câu tự luận dùng được — nhờ GV bổ sung ở Kho đề.")
        return
    hs = store.doc_hs(sid)
    bai_mac_dinh = hs.get("bai_hien_tai", "") or sorted(ds_bai)[0]
    if bai_mac_dinh not in ds_bai:
        bai_mac_dinh = sorted(ds_bai)[0]
    bai = st.selectbox(
        "Bài giảng (tự luận)",
        sorted(ds_bai),
        index=sorted(ds_bai).index(bai_mac_dinh),
        format_func=lambda b: f"{b} ({ds_bai[b]} câu TL)",
        key="tl_bai")
    if st.session_state.get("tl_bai_da_chon") != bai:
        st.session_state["tl_bai_da_chon"] = bai
        _reset_tl()
    tri = lay_trinh_do_bai(sid, bai)
    st.caption(f"Mức hiện tại: **{ten_muc_do(tri['level'])}** • {tri['so_cau']} câu đã luyện")

    atts = [a for a in _attempts(sid, bai) if a.get("dang", "TL") == "TL"]
    dung = sum(1 for a in atts if a.get("dung_het") or a.get("dung"))
    st.html(
        "<div style='display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin:8px 0 16px 0;'>"
        f"<div style='background:#f1f5f9; color:#475569; padding:6px 14px; border-radius:20px; font-size:13px; font-weight:600;'>📝 Đã nộp: {len(atts)}</div>"
        f"<div style='background:#dcfce7; color:#16a34a; padding:6px 14px; border-radius:20px; font-size:13px; font-weight:600;'>✓ Đúng hết: {dung}</div>"
        "</div>")

    cau = st.session_state.get("tl_cau")
    if not cau:
        st.info("Bấm **Phát đề** để nhận 1 câu tự luận. Bạn giải vào vở rồi chụp ảnh nộp.")
        if st.button("▶ Phát đề tự luận", type="primary", use_container_width=True):
            try:
                with st.spinner("Đang tìm câu tự luận..."):
                    _phat_de_tl(sid, bai, mon)
            except Exception as e:
                st.error(str(e))
                return
            st.rerun()
        return

    st.markdown(f"📝 **Câu {cau.get('id')}** • {widgets.muc_do_label(cau.get('do_kho', 1))}"
                + (f" • {cau['dang_phan']}" if cau.get("dang_phan") else ""))
    with st.container(border=True):
        st.markdown(bank_view.hien_thi(cau.get("de", "")))
    st.caption("Bạn giải vào vở từng bước, chụp rõ chữ rồi tải lên (tối đa 3 ảnh, mỗi ảnh <4MB). "
               "Bí thì bấm **Cần gợi ý** — mình mở từng nấc, không đọc đáp án ngay.")

    goi_ys = st.session_state.get("tl_goi_y", [])
    if goi_ys:
        st.markdown("**💡 Gợi ý đã mở:**")
        for i, g in enumerate(goi_ys, 1):
            if g.get("kieu") == "buoc":
                st.success(f"{i}. {bank_view.hien_thi(g.get('nd', ''))}")
            else:
                st.info(f"{i}. {g.get('nd', '')}")

    if "tl_anh_ver" not in st.session_state:
        st.session_state.tl_anh_ver = 0
    up_files = st.file_uploader(
        "📷 Ảnh bài giải trong vở",
        type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True,
        key=f"tl_anh_{st.session_state.tl_anh_ver}")
    if up_files:
        st.image(up_files, width=180)

    kq = st.session_state.get("tl_kq")
    if kq and not up_files:
        pass  # đã chấm xong, giữ kết quả để xem lại
    c_nop, c_goi, c_doi = st.columns([1, 1, 1])
    with c_nop:
        nop = st.button("Nộp bài chấm", type="primary", use_container_width=True,
                        disabled=not up_files)
    with c_goi:
        goi = st.button("💡 Cần gợi ý", use_container_width=True)
    with c_doi:
        doi = st.button("Câu khác", use_container_width=True)
    if goi:
        if not any(g.get("kieu") == "ai" for g in goi_ys):
            try:
                with st.spinner("Mình đang nghĩ gợi ý cho bước đầu..."):
                    gh = grading.goi_y_buoc_dau(sid, cau, mon)
                goi_ys.append({"kieu": "ai", "nd": gh.get("goi_y", "")})
            except Exception as e:
                st.error(str(e) or "Chưa nghĩ được gợi ý, bạn thử lại nhé.")
                return
        else:
            buocs = [str(b or "").strip() for b in (cau.get("buoc_giai") or [])
                     if str(b or "").strip()]
            da_mo = sum(1 for g in goi_ys if g.get("kieu") == "buoc")
            if da_mo < len(buocs):
                goi_ys.append({"kieu": "buoc", "nd": f"Bước {da_mo + 1}: {buocs[da_mo]}"})
            else:
                st.info("Đã mở hết các bước chuẩn — bạn làm vào vở rồi nộp bài nhé.")
                return
        st.session_state["tl_goi_y"] = goi_ys
        st.rerun()
    if doi:
        try:
            with st.spinner("Đang đổi câu..."):
                _phat_de_tl(sid, bai, mon)
        except Exception as e:
            st.error(str(e))
            return
        st.session_state.tl_anh_ver += 1
        st.rerun()
    if nop:
        if not up_files:
            st.warning("Bạn tải ảnh bài giải lên đã nhé.")
            return
        data_urls = []
        for f in up_files[:3]:
            url = _file_sang_data_url(f)
            if url:
                data_urls.append(url)
        if not data_urls:
            st.error("Ảnh quá lớn (>4MB). Bạn nén/chụp lại giúp mình nhé.")
            return
        try:
            with st.spinner("Mình đang đọc ảnh và chấm từng bước..."):
                kq, _ = grading.cham_tu_luan_qua_anh(sid, cau, data_urls, mon)
        except Exception as e:
            st.error(str(e) or "Chấm chưa được, bạn thử lại nhé.")
            return
        st.session_state["tl_kq"] = kq
        st.session_state.tl_anh_ver += 1  # xóa ảnh đã nộp
        st.rerun()

    kq = st.session_state.get("tl_kq")
    if kq:
        if kq.get("dung_het"):
            st.success("🎉 **Đúng hết các bước!** Giỏi lắm.")
        else:
            st.error("Chưa đúng hết — xem mình chỉ chỗ sai bên dưới.")
        ds = kq.get("dung_sai_tung_buoc") or []
        if ds:
            st.markdown("**Chấm từng bước:** " + " ".join(
                f"{'✅' if x else '❌'} B{i + 1}" for i, x in enumerate(ds)))
            if kq.get("sai_o_buoc") is not None:
                st.caption(f"Sai ở bước {kq.get('sai_o_buoc')}.")
        if kq.get("goi_y_sua"):
            st.info(f"💡 Gợi ý sửa: {kq['goi_y_sua']}")
        if kq.get("diem_yeu_moi"):
            st.warning("📝 Điểm yếu mình ghi nhận: " + ", ".join(kq["diem_yeu_moi"]))
        with st.expander("Xem bước giải chuẩn", expanded=False):
            for i, b in enumerate(cau.get("buoc_giai", []) or [], 1):
                st.markdown(f"{i}. {bank_view.hien_thi(b)}")
        if st.button("Câu tiếp theo →", type="primary", use_container_width=True):
            try:
                with st.spinner("Đang tìm câu tiếp theo..."):
                    _phat_de_tl(sid, bai, mon)
            except Exception as e:
                st.error(str(e))
                return
            st.rerun()

    with st.expander(f"Lịch sử tự luận Bài này ({len(atts)})"):
        for a in atts[:15]:
            icon = "✅" if (a.get("dung_het") or a.get("dung")) else "❌"
            st.markdown(f"{icon} **{a.get('cau_id')}**")
