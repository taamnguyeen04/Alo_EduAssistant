"""Kho đề: duyệt / sửa / thêm câu hỏi theo từng Bài (nguồn: data/bank).

Lọc trực quan: Bài • Dạng câu hỏi (Trắc nghiệm / Đúng–Sai / Trả lời ngắn)
• Mức độ (Nhận biết / Thông hiểu / Vận dụng) • Tìm kiếm.
Hình công thức/minh họa từ wiki tự hiện trong đề (bank_view.hien_thi).
"""
import glob
import os
import streamlit as st
from core import teacher, subjects, bank_view
from core import store
from ui import widgets
from ui.theme import page_header

BANK_DIR = os.path.join("data", "bank")
SO_CAU_MOI_TRANG = 15

MUC_DO_CHOICE = ["Tất cả", "Nhận biết", "Thông hiểu", "Vận dụng"]
LOAI_CHOICE = ["Tất cả", "Trắc nghiệm", "Đúng – Sai", "Trả lời ngắn"]


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


def _nguon(c):
    if c.get("nguon"):
        return c["nguon"]
    if c.get("nguon_pdf"):
        return "PDF"
    if c.get("id", "").startswith("GV-"):
        return "GV tự thêm"
    if c.get("cho_duyet"):
        return "AI sinh"
    return "Kho GV"


def _form_sua(bai, mon, c, key):
    """Form sửa 1 câu. Mức độ chọn theo tên, tự quy ra số cho Luyện tập."""
    with st.form(f"sua-{key}"):
        de = st.text_area("Đề", c.get("de", ""), height=120)
        c1, c2 = st.columns(2)
        with c1:
            muc = st.selectbox("Mức độ", ["Nhận biết", "Thông hiểu", "Vận dụng"],
                               index=bank_view.muc_do_cau(c) - 1)
        with c2:
            dp = st.text_input("Chủ đề (phân loại)", c.get("dang_phan", "") or "")
        st.caption(f"Dạng: {bank_view.ten_loai(c)} • ID: {c.get('id', '?')}")
        da = st.text_area("Đáp án", c.get("dap_an", ""), height=68)
        bg = st.text_area("Lời giải (mỗi dòng 1 bước)", "\n".join(c.get("buoc_giai", []) or []), height=150)
        loi = st.text_input("Lỗi hay gặp (cách nhau dấu phẩy)", ", ".join(c.get("loi_hay_gap", []) or []))
        ok_sua, ok_xoa = st.columns(2)
        with ok_sua:
            luu = st.form_submit_button("💾 Lưu", type="primary")
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
                    x["do_kho"] = {"Nhận biết": 1, "Thông hiểu": 2, "Vận dụng": 3}[muc]
                    x["muc_do"] = muc
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


def _ve_trang_de(c):
    """Thân đề + hình minh họa (nếu có)."""
    st.markdown(bank_view.hien_thi(c.get("de", "") or ""))


def _ve_trac_nghiem(c):
    than, pas = bank_view.tach_phuong_an(c.get("de", ""))
    dung = bank_view.dap_an_dung(c.get("dap_an", ""))
    with st.container(border=True):
        st.markdown(bank_view.hien_thi(than))
    if pas:
        st.markdown("**Các phương án:**")
        for nhan, nd in pas:
            nd_dep = bank_view.hien_thi(nd) or "*(trống)*"
            if dung and nhan == dung:
                st.success(f"**{nhan}.** {nd_dep} ✅")
            else:
                with st.container(border=True):
                    st.markdown(f"**{nhan}.** {nd_dep}")
        if not dung:
            st.warning("⚠️ Đáp án gốc không ghi rõ phương án — thầy/cô kiểm tra rồi sửa.")
    else:
        st.warning("⚠️ Không tách được phương án A–D (đề trích thiếu) — cần sửa tay.")


def _ve_dung_sai(c):
    than, mds = bank_view.tach_menh_de(c.get("de", ""))
    ds = bank_view.dap_an_dung_sai(c.get("dap_an", ""))
    with st.container(border=True):
        st.markdown(bank_view.hien_thi(than))
    if mds:
        st.markdown("**Các mệnh đề:**")
        for nhan, nd in mds:
            nd_dep = bank_view.hien_thi(nd) or "*(trống)*"
            if nhan in ds:
                icon = "✅ Đúng" if ds[nhan] else "❌ Sai"
                st.success(f"**{nhan})** {nd_dep} — **{icon}**")
            else:
                with st.container(border=True):
                    st.markdown(f"**{nhan})** {nd_dep}")
    else:
        _ve_trang_de(c)


def _ve_tra_loi_ngan(c):
    with st.container(border=True):
        st.markdown(bank_view.hien_thi(c.get("de", "")))
    if c.get("dap_an"):
        st.info(f"**📋 Đáp án:** {bank_view.hien_thi(c.get('dap_an', ''))}")


def render(mon="toan11"):
    cfg = subjects.lay_mon(mon)
    page_header(f"Kho đề {cfg['ten']}", "Đề theo từng bài — bấm vào từng câu để xem đề, đáp án và lời giải")
    st.markdown(
        """<style>
        .kho-de img { max-width: 100%; }
        .kho-de p img { vertical-align: middle; }
        </style>""",
        unsafe_allow_html=True,
    )
    ds_bai = _ds_bai_co_bank()
    if not ds_bai:
        st.info("Chưa có file bank nào trong data/bank/.")
        return
    ten_bai = [b for b, _ in ds_bai]
    bai = st.selectbox("Bài", ten_bai)

    f1, f2, f3 = st.columns([1.4, 1.2, 2])
    with f1:
        loc_loai = st.selectbox("Dạng câu hỏi", LOAI_CHOICE)
    with f2:
        loc_muc = st.selectbox("Mức độ", MUC_DO_CHOICE)
    with f3:
        tk = st.text_input("Tìm trong kho", placeholder="Gõ từ khóa trong đề...")

    kho = teacher.doc_bank(bai, mon)
    dem_muc = {"Nhận biết": 0, "Thông hiểu": 0, "Vận dụng": 0}
    dem_loai = {"Trắc nghiệm": 0, "Đúng – Sai": 0, "Trả lời ngắn": 0}
    for c in kho:
        dem_muc[bank_view.ten_muc_do(c)] = dem_muc.get(bank_view.ten_muc_do(c), 0) + 1
        dem_loai[bank_view.ten_loai(c)] = dem_loai.get(bank_view.ten_loai(c), 0) + 1
    widgets.kpi_row([("Tổng câu", len(kho)),
                     ("🟢 Nhận biết", dem_muc.get("Nhận biết", 0)),
                     ("🟡 Thông hiểu", dem_muc.get("Thông hiểu", 0)),
                     ("🔴 Vận dụng", dem_muc.get("Vận dụng", 0))])
    widgets.kpi_row([("Trắc nghiệm", dem_loai.get("Trắc nghiệm", 0)),
                     ("Đúng – Sai", dem_loai.get("Đúng – Sai", 0)),
                     ("Trả lời ngắn", dem_loai.get("Trả lời ngắn", 0)),
                     ("🖼 Có hình", sum(1 for c in kho if c.get("assets")))])

    def hop(c):
        if loc_loai != "Tất cả" and bank_view.ten_loai(c) != loc_loai:
            return False
        if loc_muc != "Tất cả" and bank_view.ten_muc_do(c) != loc_muc:
            return False
        if tk.strip() and tk.strip().lower() not in (c.get("de", "") or "").lower():
            return False
        return True

    kho_hien = [c for c in kho if hop(c)]
    hien = st.session_state.get("bank_hien", SO_CAU_MOI_TRANG)
    st.caption(f"Hiển thị {min(len(kho_hien), hien)}/{len(kho_hien)} câu khớp lọc.")
    for c in kho_hien[:hien]:
        loai = bank_view.ten_loai(c)
        muc = bank_view.ten_muc_do(c)
        icons = ""
        if c.get("assets"):
            icons += " 🖼"
        if c.get("cho_duyet"):
            icons += " 🤖 chờ duyệt"
        if c.get("chat_luong") not in (None, "", "ok"):
            icons += " 📝 cần đối chiếu gốc"
        # Cảnh báo công thức rã khi trích nguồn → icon ngay trên tiêu đề
        van_de = bank_view.phat_hien_cong_thuc_ra(
            c.get("de", ""), c.get("dap_an", ""), c.get("buoc_giai", [])
        )
        if van_de:
            icons += " 🔧"
        with st.expander(f"{c.get('id')} • {loai} • {muc}{icons}"):
            meta = f"Dạng: **{loai}** &nbsp;·&nbsp; Mức độ: **{muc}** &nbsp;·&nbsp; Nguồn: {_nguon(c)}"
            if c.get("dang_phan"):
                meta += f" &nbsp;·&nbsp; Chủ đề: {c['dang_phan']}"
            if c.get("bai"):
                meta += f" &nbsp;·&nbsp; Bài: {c['bai']}"
            st.markdown(meta)

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

            with st.container():
                st.markdown("<div class='kho-de'>", unsafe_allow_html=True)
                if loai == "Trắc nghiệm":
                    _ve_trac_nghiem(c)
                elif loai == "Đúng – Sai":
                    _ve_dung_sai(c)
                else:
                    _ve_tra_loi_ngan(c)
                st.markdown("</div>", unsafe_allow_html=True)

            # ── Lời giải ────────────────────────────────────────────
            if c.get("buoc_giai"):
                with st.expander(f"📐 Lời giải ({len(c['buoc_giai'])} bước)", expanded=False):
                    for i, b in enumerate(c["buoc_giai"], 1):
                        st.markdown(f"**Bước {i}:** {bank_view.hien_thi(b)}")

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
    if len(kho_hien) > hien:
        if st.button(f"Hiện thêm {SO_CAU_MOI_TRANG} câu"):
            st.session_state["bank_hien"] = hien + SO_CAU_MOI_TRANG
            st.rerun()
    st.divider()
    widgets.section_title("➕ Thêm câu mới vào kho")
    with st.container(border=True):
        with st.form("them-cau"):
            de = st.text_area("Đề", placeholder="VD: Cho cấp số cộng u1=3, d=4. Tính u5.")
            c1, c2 = st.columns(2)
            with c1:
                dang_moi = st.selectbox("Dạng câu hỏi", ["Trắc nghiệm", "Trả lời ngắn"])
            with c2:
                muc_moi = st.selectbox("Mức độ", ["Nhận biết", "Thông hiểu", "Vận dụng"], index=1)
            da = st.text_input("Đáp án", placeholder="Trắc nghiệm ghi: Chọn A/B/C/D")
            bg = st.text_area("Lời giải (mỗi dòng 1 bước)")
            loi = st.text_input("Lỗi hay gặp (cách nhau dấu phẩy)")
            if st.form_submit_button("Lưu vào kho"):
                if not de.strip():
                    st.error("Thiếu đề.")
                else:
                    kho = teacher.doc_bank(bai, mon)
                    dk = {"Nhận biết": 1, "Thông hiểu": 2, "Vận dụng": 3}[muc_moi]
                    kho.append({"id": f"GV-{len(kho)+1:03d}", "bai": bai, "do_kho": dk, "muc_do": muc_moi,
                                "dang": "TN" if dang_moi == "Trắc nghiệm" else "TL",
                                "loai": "trac_nghiem" if dang_moi == "Trắc nghiệm" else "tra_loi_ngan",
                                "de": de.strip(),
                                "dap_an": da.strip(), "buoc_giai": [x.strip() for x in bg.splitlines() if x.strip()],
                                "loi_hay_gap": [x.strip() for x in loi.split(",") if x.strip()],
                                "chat_luong": "ok", "ly_do": ""})
                    teacher.luu_bank(bai, kho, mon)
                    st.success("Đã lưu vào kho.")
                    st.rerun()
