import glob
import os
import streamlit as st
from core import teacher, subjects, bank_view
from core import store
from ui import widgets
from ui.theme import page_header

BANK_DIR = os.path.join("data", "bank")
SO_CAU_MOI_TRANG = 30


def _ds_bai_co_bank():
    """Liệt kê Bài từ file bank thật (khỏi lệ thuộc tên video, vd Bài 31-33)."""
    ds = []
    for f in sorted(glob.glob(os.path.join(BANK_DIR, "*.json"))):
        try:
            data = store.doc_json(f, [])
            bai = next((c.get("bai", "") for c in data if c.get("bai")), "")
            ds.append((bai or os.path.basename(f), f))
        except Exception:
            continue
    return ds


def _badge(c):
    if c.get("cho_duyet"):
        return "🤖 AI sinh — CHỜ DUYỆT"
    if c.get("chat_luong") != "ok":
        return f"🟡 Cần duyệt ({c.get('ly_do', '')})"
    return "🟢 Đạt chuẩn"


def _form_sua(bai, mon, c, key):
    """Form sửa 1 câu. Lưu xong đánh dấu GV đã duyệt tay."""
    with st.form(f"sua-{key}"):
        de = st.text_area("Đề", c.get("de", ""), height=120)
        c1, c2, c3 = st.columns(3)
        with c1:
            dk = st.slider("Độ khó", 1, 3, int(c.get("do_kho", 2) or 2))
        with c2:
            dp = st.text_input("Dạng phân loại", c.get("dang_phan", "") or "")
        with c3:
            st.caption(f"Dạng: {c.get('dang', '?')} • ID: {c.get('id', '?')}")
        da = st.text_area("Đáp án", c.get("dap_an", ""), height=68)
        bg = st.text_area("Bước giải (mỗi dòng 1 bước)", "\n".join(c.get("buoc_giai", []) or []), height=150)
        loi = st.text_input("Lỗi hay gặp (cách nhau dấu phẩy)", ", ".join(c.get("loi_hay_gap", []) or []))
        ok_sua, ok_xoa = st.columns(2)
        with ok_sua:
            luu = st.form_submit_button("💾 Lưu + đánh dấu đã duyệt", type="primary")
        with ok_xoa:
            xoa = st.form_submit_button("🗑 Xóa câu này")
    if luu:
        if not de.strip():
            st.error("Thiếu đề.")
        else:
            full = teacher.doc_bank(bai, mon)
            for x in full:
                if x.get("id") == c.get("id"):
                    x["de"] = de.strip()
                    x["do_kho"] = dk
                    x["dang_phan"] = dp.strip()
                    x["dap_an"] = da.strip()
                    x["buoc_giai"] = [b.strip() for b in bg.splitlines() if b.strip()]
                    x["loi_hay_gap"] = [x2.strip() for x2 in loi.split(",") if x2.strip()]
                    x.pop("cho_duyet", None)
                    x["chat_luong"] = "ok"  # GV đã đọc tay
                    x["ly_do"] = ""
            teacher.luu_bank(bai, full, mon)
            st.session_state.pop(f"dang_sua-{c.get('id')}", None)
            st.success("Đã lưu.")
            st.rerun()
    if xoa:
        full = [x for x in teacher.doc_bank(bai, mon) if x.get("id") != c.get("id")]
        teacher.luu_bank(bai, full, mon)
        st.session_state.pop(f"dang_sua-{c.get('id')}", None)
        st.warning("Đã xóa.")
        st.rerun()


def render(mon="toan11"):
    cfg = subjects.lay_mon(mon)
    page_header(f"Kho đề {cfg['ten']}", "Nguồn chính cho bài luyện — câu AI sinh phải duyệt mới lên sóng")
    ds_bai = _ds_bai_co_bank()
    if not ds_bai:
        st.info("Chưa có file bank nào trong data/bank/.")
        return
    ten_bai = [b for b, _ in ds_bai]
    bai = st.selectbox("Bài", ten_bai)

    f1, f2, f3, f4 = st.columns([2, 2, 2, 3])
    with f1:
        loc_cl = st.selectbox("Chất lượng", ["Tất cả", "Đạt chuẩn", "Cần duyệt", "AI sinh"])
    with f2:
        loc_dang = st.selectbox("Dạng", ["Tất cả", "TN", "TL"])
    with f3:
        loc_kho = st.selectbox("Độ khó", ["Tất cả", "1", "2", "3"])
    with f4:
        tk = st.text_input("Tìm trong kho", "")

    kho = teacher.doc_bank(bai, mon)
    de1 = sum(1 for c in kho if int(c.get("do_kho", 2) or 2) == 1)
    de2 = sum(1 for c in kho if int(c.get("do_kho", 2) or 2) == 2)
    de3 = sum(1 for c in kho if int(c.get("do_kho", 2) or 2) == 3)
    ok = sum(1 for c in kho if c.get("chat_luong") == "ok" and not c.get("cho_duyet"))
    widgets.kpi_row([("Tổng câu", len(kho)), ("Đạt chuẩn", ok),
                     ("Dễ/Toolbox", f"{de1}/{de2}/{de3}"),
                     ("TN/TL", f"{sum(1 for c in kho if c.get('dang') == 'TN')}/{sum(1 for c in kho if c.get('dang') == 'TL')}")])

    def hop(c):
        if loc_dang != "Tất cả" and c.get("dang") != loc_dang:
            return False
        if loc_kho != "Tất cả" and str(int(c.get("do_kho", 2) or 2)) != loc_kho:
            return False
        if loc_cl == "Đạt chuẩn" and not (c.get("chat_luong") == "ok" and not c.get("cho_duyet")):
            return False
        if loc_cl == "Cần duyệt" and not (c.get("chat_luong") != "ok" and not c.get("cho_duyet")):
            return False
        if loc_cl == "AI sinh" and not c.get("cho_duyet"):
            return False
        if tk.strip() and tk.strip().lower() not in (c.get("de", "") or "").lower():
            return False
        return True

    kho_hien = [c for c in kho if hop(c)]
    st.caption(f"Hiển thị {min(len(kho_hien), st.session_state.get('bank_hien', SO_CAU_MOI_TRANG))}/{len(kho_hien)} câu khớp lọc.")
    for c in kho_hien[: st.session_state.get("bank_hien", SO_CAU_MOI_TRANG)]:
        badge = _badge(c)
        sao = widgets.do_kho_sao(int(c.get("do_kho", 2) or 2))
        # Kiểm tra trước công thức có bị rã không → thêm icon cảnh báo vào label
        van_de = bank_view.phat_hien_cong_thuc_ra(
            c.get("de", ""), c.get("dap_an", ""), c.get("buoc_giai", [])
        )
        warn_icon = " 🔧" if van_de else ""
        exp_label = f"{c.get('id')} • khó {c.get('do_kho')} {sao} • {badge}{warn_icon}"
        with st.expander(exp_label):
            # ── Meta ──────────────────────────────────────────────
            meta_parts = [f"Dạng: **{c.get('dang', '?')}**"]
            if c.get("dang_phan"):
                meta_parts.append(f"Phân loại: {c['dang_phan']}")
            if c.get("bai"):
                meta_parts.append(f"Bài: {c['bai']}")
            st.markdown(" &nbsp;·&nbsp; ".join(meta_parts))

            # ── Cảnh báo công thức rã ─────────────────────────────
            if van_de:
                st.markdown(
                    "<div style='background:#fef3c7;border:1px solid #fcd34d;border-radius:8px;"
                    "padding:8px 14px;margin:6px 0;font-size:0.85rem;color:#92400e;'>"
                    "🔧 <strong>Công thức cần kiểm tra:</strong> "
                    + " · ".join(van_de)
                    + "<br><small>Bấm <em>Sửa</em> để chỉnh lại biểu thức toán học đúng cú pháp $...$</small></div>",
                    unsafe_allow_html=True,
                )
            st.markdown("---")

            # ── Nội dung đề ───────────────────────────────────────
            if c.get("dang") == "TN":
                than, pas = bank_view.tach_phuong_an(c.get("de", ""))
                dung = bank_view.dap_an_dung(c.get("dap_an", ""))

                # Thân đề
                than_dep = bank_view.lam_dep_hien_thi(than)
                with st.container(border=True):
                    st.markdown(than_dep)

                if pas:
                    st.markdown("**Phương án:**")
                    for nhan, nd in pas:
                        nd_dep = bank_view.lam_dep_hien_thi(nd) or "*(trống)*"
                        if dung and nhan == dung:
                            st.success(f"**{nhan}.** {nd_dep} *(đáp án đúng)*")
                        else:
                            with st.container(border=True):
                                st.markdown(f"**{nhan}.** {nd_dep}")
                    if not dung:
                        st.warning("⚠️ Đáp án gốc không ghi rõ phương án — thầy/cô kiểm tra rồi sửa.")
                else:
                    st.warning("⚠️ Không tách được phương án A–D (đề trích thiếu) — cần sửa tay.")
            else:
                # Câu tự luận
                de_dep = bank_view.lam_dep_hien_thi(c.get("de", ""))
                with st.container(border=True):
                    st.markdown(de_dep)

            # ── Đáp án ────────────────────────────────────────────
            if c.get("dap_an"):
                da_dep = bank_view.lam_dep_hien_thi(c.get("dap_an", ""))
                st.info(f"**📋 Đáp án:** {da_dep}")

            # ── Bước giải ─────────────────────────────────────────
            if c.get("buoc_giai"):
                with st.expander(f"📐 Bước giải ({len(c['buoc_giai'])} bước)", expanded=False):
                    for i, b in enumerate(c["buoc_giai"], 1):
                        b_dep = bank_view.lam_dep_hien_thi(b)
                        st.markdown(f"**Bước {i}:** {b_dep}")

            # ── Lỗi hay gặp ───────────────────────────────────────
            if c.get("loi_hay_gap"):
                st.markdown(
                    "<span style='color:#92400e;font-size:0.82rem;font-weight:600;'>⚠️ Lỗi hay gặp:</span> "
                    + "<span style='font-size:0.85rem;color:#78350f;'>" + " · ".join(c["loi_hay_gap"]) + "</span>",
                    unsafe_allow_html=True,
                )

            # ── Raw text (để GV đối chiếu khi cần sửa) ───────────
            with st.expander("🔍 Xem text gốc (để kiểm tra lỗi công thức)", expanded=False):
                st.code(c.get("de", ""), language=None)
                if c.get("dap_an"):
                    st.caption(f"Đáp án gốc: {c.get('dap_an', '')}")

            # ── Nút hành động ─────────────────────────────────────
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
            cc1, cc2, cc3 = st.columns(3)
            with cc1:
                sua = st.button("✏️ Sửa", key=f"sua-{c.get('id')}", use_container_width=True)
            with cc2:
                duyet = c.get("cho_duyet") and st.button("✅ Duyệt", key=f"duyet-{c.get('id')}", use_container_width=True)
            with cc3:
                xoa = st.button("🗑 Xóa", key=f"xoa-{c.get('id')}", use_container_width=True)
            if sua:
                st.session_state[f"dang_sua-{c.get('id')}"] = not st.session_state.get(f"dang_sua-{c.get('id')}", False)
            if st.session_state.get(f"dang_sua-{c.get('id')}"):
                _form_sua(bai, mon, c, c.get("id"))
            if duyet:
                full = teacher.doc_bank(bai, mon)
                for x in full:
                    if x.get("id") == c.get("id"):
                        x.pop("cho_duyet", None)
                teacher.luu_bank(bai, full, mon)
                st.rerun()
            if xoa:
                full = [x for x in teacher.doc_bank(bai, mon) if x.get("id") != c.get("id")]
                teacher.luu_bank(bai, full, mon)
                st.rerun()
    if len(kho_hien) > st.session_state.get("bank_hien", SO_CAU_MOI_TRANG):
        if st.button(f"Hiện thêm {SO_CAU_MOI_TRANG} câu"):
            st.session_state["bank_hien"] = st.session_state.get("bank_hien", SO_CAU_MOI_TRANG) + SO_CAU_MOI_TRANG
            st.rerun()
    st.divider()
    widgets.section_title("➕ Thêm câu mới vào kho")
    with st.container(border=True):
        with st.form("them-cau"):
            de = st.text_area("Đề", placeholder="VD: Cho cấp số cộng u1=3, d=4. Tính u5.")
            c1, c2 = st.columns(2)
            with c1:
                dk = st.slider("Độ khó", 1, 3, 2)
            with c2:
                da = st.text_input("Đáp án")
            bg = st.text_area("Bước giải (mỗi dòng 1 bước)")
            loi = st.text_input("Lỗi hay gặp (cách nhau dấu phẩy)")
            if st.form_submit_button("Lưu vào kho"):
                if not de.strip():
                    st.error("Thiếu đề.")
                else:
                    kho = teacher.doc_bank(bai, mon)
                    kho.append({"id": f"GV-{len(kho)+1:03d}", "bai": bai, "do_kho": dk, "de": de.strip(),
                                "dap_an": da.strip(), "buoc_giai": [x.strip() for x in bg.splitlines() if x.strip()],
                                "loi_hay_gap": [x.strip() for x in loi.split(",") if x.strip()],
                                "chat_luong": "ok", "ly_do": ""})
                    teacher.luu_bank(bai, kho, mon)
                    st.success("Đã lưu vào kho.")
                    st.rerun()
