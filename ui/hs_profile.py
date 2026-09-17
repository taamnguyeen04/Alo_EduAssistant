import os
import pandas as pd
import streamlit as st
from core import store, subjects, curriculum, tkb as tkb_core, kehoach
from ui import widgets
from ui.theme import page_header

NGAY_TUAN = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
NGAY_DE = {"T2": "Thứ 2", "T3": "Thứ 3", "T4": "Thứ 4", "T5": "Thứ 5",
           "T6": "Thứ 6", "T7": "Thứ 7", "CN": "Chủ nhật"}
ATTEMPT_DIR = os.path.join("data", "attempts")

# Bảng màu pastel cho từng môn (xoay vòng theo hash tên môn)
_MAU_MON = [
    ("#eff6ff", "#bfdbfe", "#1d4ed8"),  # xanh dương
    ("#f0fdf4", "#bbf7d0", "#15803d"),  # xanh lá
    ("#fefce8", "#fde68a", "#a16207"),  # vàng
    ("#fdf2f8", "#fbcfe8", "#be185d"),  # hồng
    ("#f5f3ff", "#ddd6fe", "#6d28d9"),  # tím
    ("#fff7ed", "#fed7aa", "#c2410c"),  # cam
    ("#ecfeff", "#a5f3fc", "#0e7490"),  # cyan
    ("#fef2f2", "#fecaca", "#b91c1c"),  # đỏ
]


def _mau_mon(mon):
    return _MAU_MON[abs(hash(mon)) % len(_MAU_MON)]


def _html_tkb(lich):
    """Bảng TKB đẹp: mỗi buổi 1 bảng, cột = ngày, dòng = tiết."""
    buois = []
    for b in (["sáng", "chiều", "tối"] + sorted({bu for ng in lich.values() for bu in ng})):
        if b not in buois and any(lich.get(ng, {}).get(b) for ng in NGAY_TUAN):
            buois.append(b)
    ngays = [n for n in NGAY_TUAN if n in lich and any(lich[n].values())]
    if not ngays or not buois:
        return ""
    html = ["<div class='tkb-wrap'>"]
    for bu in buois:
        tiet_max = 0
        for n in ngays:
            for t in lich.get(n, {}).get(bu, {}):
                try:
                    tiet_max = max(tiet_max, int(t))
                except ValueError:
                    pass
        if tiet_max <= 0:
            continue
        html.append(f"<div class='tkb-buoi'>{bu.title()}</div>")
        html.append("<table class='tkb-table'><tr><th class='tkb-tiet'>Tiết</th>")
        for n in ngays:
            html.append(f"<th>{NGAY_DE.get(n, n)}</th>")
        html.append("</tr>")
        for t in range(1, tiet_max + 1):
            html.append(f"<tr><td class='tkb-tiet'>{t}</td>")
            for n in ngays:
                mon = (lich.get(n, {}).get(bu, {}) or {}).get(str(t), "")
                if mon:
                    bg, bd, tx = _mau_mon(mon)
                    html.append(
                        f"<td><span class='tkb-mon' style='background:{bg};border-color:{bd};color:{tx};'>{mon}</span></td>")
                else:
                    html.append("<td class='tkb-trong'>·</td>")
            html.append("</tr>")
        html.append("</table>")
    html.append("</div>")
    return "".join(html)


def _df_buoi(lich, buoi, ngays, n_tiet):
    """Dựng DataFrame (dòng=Tiết, cột=ngày) để sửa trực tiếp."""
    data = {}
    for n in ngays:
        tiet_map = ((lich.get(n) or {}).get(buoi) or {})
        data[n] = [(tiet_map.get(str(t), "") or "") for t in range(1, n_tiet + 1)]
    return pd.DataFrame(data, index=[str(t) for t in range(1, n_tiet + 1)])


def _buoi_lich_tu_editors(ss, ngays):
    """Đọc mọi data_editor pf_tkb_edit_* -> {ngày: {buổi: {tiết: môn}}}."""
    lich = {}
    for k in list(ss.keys()):
        if not k.startswith("pf_tkb_edit_"):
            continue
        buoi = k[len("pf_tkb_edit_"):]
        df = ss[k]
        if df is None:
            continue
        for ngay in (df.columns if hasattr(df, "columns") else []):
            if ngay not in NGAY_TUAN:
                continue
            for tiet, v in df[ngay].items():
                if v is None:
                    continue
                try:
                    if pd.isna(v):
                        continue
                except (TypeError, ValueError):
                    pass
                mon = str(v).strip()
                if mon and mon.lower() not in ("nan", "none", "nat"):
                    lich.setdefault(ngay, {}).setdefault(buoi, {})[str(tiet)] = mon
    return lich


def _gom_du_lieu_ho_so(ss, hs, sid, tkb_moi=None, tkb_tay=None):
    """Gom toàn bộ hồ sơ từ dict widget-state (hàm thuần -> test được).

    Quy tắc TKB để không bao giờ mất dữ liệu oan:
    - File mới upload (tkb_moi) -> thay thế hẳn.
    - Bảng sửa trực tiếp -> chỉ thay khi gom được lịch NON-EMPTY
      (tránh data_editor mất state khi expander đóng ghi đè TKB cũ);
      muốn xóa sạch thì dùng nút 🗑 Xóa.
    - Nhập tay -> chỉ thay khi có ít nhất 1 ngày (tránh form tay trống
      lúc đang ở chế độ file ghi đè mất TKB).
    """
    get = ss.get
    data = {
        "ten": get("pf_ten", hs.get("ten", sid)),
        "lop": get("pf_lop", hs.get("lop", "11")),
        "phong_cach": get("pf_pc", hs.get("phong_cach", "")),
        "mon_can_ho_tro": [m for m in get("pf_mon_ho_tro", hs.get("mon_can_ho_tro", []))
                            if m in subjects.MON_HOC],
        "muc_tieu": get("pf_muc_tieu", hs.get("muc_tieu", "")),
        "gio_tu_hoc": get("pf_gio_tu_hoc", hs.get("gio_tu_hoc", "")),
        "bai_hien_tai": get("pf_bai", hs.get("bai_hien_tai", "")),
    }
    mtgd = {}
    for gd in kehoach.GIAI_DOAN:
        g = {}
        for ma in subjects.MON_HOC:
            try:
                d = float(get(f"pf_mt_{gd}_{ma}", 0) or 0)
            except (TypeError, ValueError):
                d = 0
            if d > 0:
                g[ma] = round(min(d, 10), 1)
        if g:
            mtgd[gd] = g
    data["muc_tieu_giai_doan"] = mtgd
    tkb_cu = hs.get("tkb", {}) or {}
    if tkb_moi is not None:
        data["tkb"] = tkb_moi
    else:
        keys = list(ss.keys()) if hasattr(ss, "keys") else []
        if any(k.startswith("pf_tkb_edit_") for k in keys):
            lich = _buoi_lich_tu_editors(ss, NGAY_TUAN)
            if lich:
                meta = tkb_cu if tkb_core.la_tkb_file(tkb_cu) else {}
                data["tkb"] = {
                    "nguon": meta.get("nguon", ""),
                    "lop": meta.get("lop", ""),
                    "hieu_luc": meta.get("hieu_luc", ""),
                    "lich": lich,
                }
            else:
                data["tkb"] = tkb_cu  # editor rỗng bất thường -> GIỮ TKB cũ
        elif tkb_tay is not None:
            tay = {n: [m.strip() for m in tkb_tay[n].split(",") if m.strip()]
                   for n in NGAY_TUAN if tkb_tay[n].strip()}
            data["tkb"] = tay if tay else tkb_cu  # form tay trống -> GIỮ cũ
        else:
            data["tkb"] = tkb_cu
    return data


def _luu_ho_so(sid, hs, tkb_moi=None, tkb_tay=None):
    """Lưu toàn bộ hồ sơ: gom từ session_state hiện tại rồi ghi file."""
    ss = st.session_state
    data = _gom_du_lieu_ho_so(ss, hs, sid, tkb_moi=tkb_moi, tkb_tay=tkb_tay)
    if tkb_moi is not None:
        for k in list(ss.keys()):
            if k.startswith("pf_tkb_"):
                ss.pop(k)
    hs.update(data)
    store.luu_hs(sid, hs)
    return hs

def _render_html(s):
    st.html(s)

def render(sid, mon="toan11"):
    # Đổi tài khoản (đăng xuất rồi vào mã khác) -> xóa state form cũ để
    # tên/TKB/mục tiêu của bạn trước không lẫn sang bạn sau.
    if st.session_state.get("_pf_sid") != sid:
        for k in [k for k in list(st.session_state.keys())
                  if k.startswith("pf_") or k == "tkb_file_da_xu_ly"]:
            st.session_state.pop(k, None)
        st.session_state["_pf_sid"] = sid

    cfg = subjects.lay_mon(mon)
    
    _render_html("""
        <style>
        .profile-header {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            border-radius: 20px; padding: 32px; color: white; display: flex; align-items: center; gap: 24px;
            margin-bottom: 32px; box-shadow: 0 10px 25px rgba(15,23,42,0.15);
        }
        .profile-avatar {
            width: 80px; height: 80px; background: #3b82f6; border-radius: 50%; color: #fff;
            display: flex; align-items: center; justify-content: center; font-size: 32px; font-weight: bold;
            box-shadow: 0 0 0 4px rgba(255,255,255,0.2);
        }
        .profile-header h1 {
            color: #fff !important;
        }
        .section-title {
            font-size: 18px; font-weight: 700; color: #1e293b; margin-bottom: 16px;
            padding-bottom: 8px; border-bottom: 2px solid #f1f5f9;
        }
        .stTextInput > div > div > input, .stSelectbox > div > div > div {
            background-color: #f8fafc !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 10px !important;
        }
        .stTextInput > div > div > input:focus, .stSelectbox > div > div > div:focus {
            border-color: #3b82f6 !important;
            box-shadow: 0 0 0 2px rgba(59,130,246,0.2) !important;
        }
        .tkb-wrap { margin: 4px 0 8px 0; }
        .tkb-buoi {
            font-size: 14px; font-weight: 700; color: #0f172a; margin: 12px 0 6px 0;
            display: flex; align-items: center; gap: 8px;
        }
        .tkb-buoi::after { content: ""; flex: 1; height: 1px; background: #e2e8f0; }
        .tkb-table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 13px; }
        .tkb-table th {
            background: #f8fafc; color: #475569; font-weight: 700; font-size: 12px;
            padding: 8px 6px; border-bottom: 2px solid #e2e8f0; text-align: center;
            text-transform: uppercase; letter-spacing: 0.3px;
        }
        .tkb-table td { padding: 4px; border-bottom: 1px solid #f1f5f9; text-align: center; }
        .tkb-tiet { color: #94a3b8 !important; font-weight: 700; width: 36px; }
        .tkb-mon {
            display: inline-block; border: 1px solid; border-radius: 8px;
            padding: 4px 10px; font-weight: 600; font-size: 13px; white-space: nowrap;
        }
        .tkb-trong { color: #cbd5e1; }
        .tkb-meta {
            background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 10px;
            padding: 8px 12px; font-size: 13px; color: #475569; margin-bottom: 4px;
        }
        </style>
    """)

    hs = store.doc_hs(sid)
    ten = hs.get("ten", sid)
    lop = hs.get("lop", "11")

    if (ten or "").strip() in ("", sid):
        st.info("👋 Chào em! Hồ sơ chưa có họ tên — cập nhật họ tên ở mục bên dưới rồi bấm Lưu nhé.")
    
    _render_html(f"""
        <div class="profile-header">
            <div class="profile-avatar">{ten[0].upper() if ten else 'H'}</div>
            <div>
                <h1 style="margin: 0 0 4px 0; font-size: 32px; font-weight: 800; color: #ffffff;">Hồ sơ học tập</h1>
                <div style="color: #cbd5e1; font-size: 17px;">Mã học sinh: {sid} • Lớp {lop}</div>
            </div>
        </div>
    """)
    
    c1, c2 = st.columns([1.2, 1])
    with c1:
        _render_html("<div class='section-title'>👤 Thông tin cá nhân</div>")
        st.text_input("Mã học sinh", sid, disabled=True,
                      help="Mã đăng nhập, không thay đổi được.")
        st.text_input("Họ và tên", hs.get("ten", ""), key="pf_ten",
                      placeholder="Nhập họ và tên của em")

        c_lop, c_gio = st.columns(2)
        with c_lop:
            lop_new = st.text_input("Lớp", hs.get("lop", "11"), key="pf_lop")
        with c_gio:
            gio_opts = ["", "Dưới 30 phút", "30–60 phút", "1–2 giờ", "Trên 2 giờ"]
            gio_cu = hs.get("gio_tu_hoc", "")
            st.selectbox("Tự học mỗi ngày", gio_opts,
                         index=gio_opts.index(gio_cu) if gio_cu in gio_opts else 0,
                         key="pf_gio_tu_hoc")

        mon_ht = [m for m in hs.get("mon_can_ho_tro", []) if m in subjects.MON_HOC]
        st.multiselect("Môn muốn được hỗ trợ nhiều nhất",
                       list(subjects.MON_HOC.keys()), default=mon_ht,
                       format_func=lambda m: f"{subjects.MON_HOC[m]['icon']} {subjects.MON_HOC[m]['ten']}",
                       key="pf_mon_ho_tro")
        st.text_input("Mục tiêu học tập (VD: đạt 8+ cuối kỳ, đỗ HSG)",
                      hs.get("muc_tieu", ""), key="pf_muc_tieu")
        pc = st.text_input("Cách học hiệu quả nhất (VD: thích ví dụ thực tế, học qua hình ảnh)", hs.get("phong_cach", ""), key="pf_pc")

        _render_html("<br><div class='section-title'>🎯 Mục tiêu điểm từng giai đoạn</div>")
        st.caption("Thang điểm 10 • để 0 nếu chưa đặt. Đổi mục tiêu hoặc thời khóa biểu → AI tự làm lại kế hoạch ở Trang chủ.")
        mt_cu = hs.get("muc_tieu_giai_doan", {}) or {}
        tabs_mt = st.tabs([kehoach.TEN_GIAI_DOAN[gd] for gd in kehoach.GIAI_DOAN])
        mons = list(subjects.MON_HOC.keys())
        for gd, tab in zip(kehoach.GIAI_DOAN, tabs_mt):
            with tab:
                g = mt_cu.get(gd, {}) or {}
                for i in range(0, len(mons), 2):
                    cc = st.columns(2)
                    for col, ma in zip(cc, mons[i:i + 2]):
                        with col:
                            try:
                                val = float(g.get(ma, 0) or 0)
                            except (TypeError, ValueError):
                                val = 0.0
                            st.number_input(
                                f"{subjects.MON_HOC[ma]['icon']} {subjects.MON_HOC[ma]['ten']}",
                                min_value=0.0, max_value=10.0, step=0.5, value=val,
                                key=f"pf_mt_{gd}_{ma}")

    with c2:
        _render_html("<div class='section-title'>📅 Kế hoạch học tập</div>")
        ds_bai = [""] + [v["title"] for v in curriculum.load_videos(mon)] + ["ngoài chương trình"]
        bai_ht = hs.get("bai_hien_tai", "")
        idx_bai = ds_bai.index(bai_ht) if bai_ht in ds_bai else 0
        bai = st.selectbox("Bài đang học trên lớp", ds_bai, index=idx_bai, key="pf_bai")

        _render_html("<div style='margin:12px 0 8px 0; font-size:14px; color:#334155; font-weight:600;'>📤 Tải thời khóa biểu (file .xlsx của lớp)</div>")
        up = st.file_uploader("Tải thời khóa biểu", type=["xlsx"], key="pf_tkb_file",
                              label_visibility="collapsed",
                              help="File Excel có bảng Tiết | Thứ 2..Thứ 7 cho buổi sáng/chiều, giống file mẫu của lớp.")

        tkb_cu = hs.get("tkb", {}) or {}
        co_file = tkb_core.la_tkb_file(tkb_cu) and bool((tkb_cu.get("lich") or {}))

        # Tải file -> đọc -> lưu TKB + toàn bộ hồ sơ luôn, rồi hiện bảng đẹp
        if up is not None:
            fid = f"{up.name}:{up.size}"
            if st.session_state.get("tkb_file_da_xu_ly") != fid:
                try:
                    tkb_moi = tkb_core.parse_tkb_xlsx(up.getvalue(), up.name)
                except Exception as e:
                    st.error(f"Không đọc được file: {e}")
                else:
                    hs = _luu_ho_so(sid, hs, tkb_moi=tkb_moi)
                    st.session_state["tkb_file_da_xu_ly"] = fid
                    st.success(f"Đã lưu thời khóa biểu {tkb_moi.get('lop', '')} + toàn bộ hồ sơ.")
                    st.rerun()

        if co_file:
            chuan = tkb_core.chuan_hoa_tkb(tkb_cu)
            meta = " • ".join(x for x in [
                f"📎 {chuan.get('nguon')}" if chuan.get("nguon") else "",
                f"Lớp {chuan.get('lop')}" if chuan.get("lop") else "",
                f"Hiệu lực {chuan.get('hieu_luc')}" if chuan.get("hieu_luc") else "",
            ] if x)
            if meta:
                _render_html(f"<div class='tkb-meta'>{meta}</div>")
            lich_chuan = chuan.get("lich", {})
            _render_html(_html_tkb(lich_chuan))
            ngays_co = [n for n in NGAY_TUAN if n in lich_chuan and any((lich_chuan[n] or {}).values())]
            buois_co = []
            for b in (["sáng", "chiều", "tối"] + sorted({bu for ng in lich_chuan.values() for bu in (ng or {})})):
                if b not in buois_co and any(((lich_chuan.get(n) or {}).get(b) or {}) for n in ngays_co):
                    buois_co.append(b)
            with st.expander("✏️ Chỉnh sửa trực tiếp trên thời khóa biểu", expanded=False):
                st.caption("Bấm đúp vào ô để sửa môn, xóa trắng ô để bỏ tiết, rồi bấm Lưu.")
                for buoi in buois_co:
                    tiet_max = 5
                    for n in ngays_co:
                        for t in ((lich_chuan.get(n) or {}).get(buoi) or {}):
                            try:
                                tiet_max = max(tiet_max, int(t))
                            except ValueError:
                                pass
                    st.markdown(f"**Buổi {buoi}**")
                    st.data_editor(
                        _df_buoi(lich_chuan, buoi, ngays_co, tiet_max),
                        key=f"pf_tkb_edit_{buoi}",
                        use_container_width=True,
                        column_config={n: st.column_config.TextColumn(NGAY_DE.get(n, n)) for n in ngays_co},
                    )
                if st.button("💾 Lưu thay đổi TKB + hồ sơ", key="pf_luu_tkb", use_container_width=True):
                    hs = _luu_ho_so(sid, hs)
                    st.success("Đã lưu thời khóa biểu.")
                    st.rerun()
            c_xoa, c_hint = st.columns([1, 2])
            with c_xoa:
                if st.button("🗑 Xóa", key="pf_xoa_tkb", help="Xóa TKB file, quay về nhập tay"):
                    hs["tkb"] = {}
                    store.luu_hs(sid, hs)
                    for k in list(st.session_state.keys()):
                        if k.startswith("pf_tkb_"):
                            st.session_state.pop(k)
                    st.success("Đã xóa thời khóa biểu.")
                    st.rerun()
            with c_hint:
                st.caption("Tải file mới để thay thế.")
            tkb_tay = None
        else:
            _render_html("<div style='margin-bottom:8px; font-size:14px; color:#334155; font-weight:600;'>Thời khóa biểu các môn (nhập tay)</div>")
            tkb_tay = {}
            for i in range(0, 7, 2):
                c_d1, c_d2 = st.columns(2)
                with c_d1:
                    ngay = NGAY_TUAN[i]
                    cu = tkb_cu.get(ngay, [])
                    tkb_tay[ngay] = st.text_input(ngay, ", ".join(cu) if isinstance(cu, list) else "", placeholder="Toán, Lý...", key=f"pf_tkb_{ngay}")
                with c_d2:
                    if i + 1 < 7:
                        ngay2 = NGAY_TUAN[i + 1]
                        cu2 = tkb_cu.get(ngay2, [])
                        tkb_tay[ngay2] = st.text_input(ngay2, ", ".join(cu2) if isinstance(cu2, list) else "", placeholder="Văn, Anh...", key=f"pf_tkb_{ngay2}")

        _render_html("<br>")
        if st.button("Lưu", type="primary", use_container_width=True):
            hs = _luu_ho_so(sid, hs, tkb_tay=tkb_tay)
            st.success("Đã lưu hồ sơ. AI sẽ cá nhân hóa bài giảng theo thiết lập này.")
            st.rerun()
