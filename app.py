"""Entry Streamlit: trợ lí học tập đa môn (môn đầu tiên có dữ liệu: Toán 11)."""

# ═══════════════════════════════════════════════════════════
#  CHẾ ĐỘ AI — MUỐN ĐỔI THÌ ĐỔI NGAY DÒNG DƯỚI:
#    "test" = miễn phí như cũ (code/test hằng ngày)
#    "prod" = thi/demo (2 DeepSeek: PRO hỏi đáp + FLASH việc ngầm)
#  Đổi xong lưu file, chạy lại:  streamlit run app.py
# ═══════════════════════════════════════════════════════════
LLM_MODE = "prod"

import os
import streamlit as st

try:
    import pandas  # noqa: F401 — nạp sẵn: plotly sờ pd.Series khi pandas đang nạp dở sẽ crash
except ImportError:
    pass

from core import store, curriculum, teacher, subjects
from ui import theme

# Hằng LLM_MODE ở đầu file làm mặc định; env gõ tay lúc chạy được ưu tiên:
#   $env:LLM_MODE="prod"; streamlit run app.py
os.environ.setdefault("LLM_MODE", LLM_MODE)

st.set_page_config(page_title="Alo_EduAssistant — Trợ lí học tập", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")
theme.apply_theme()

MON = st.session_state.get("mon", subjects.MON_MAC_DINH)
CFG = subjects.lay_mon(MON)

# Số liệu nhanh cho sidebar (theo môn đang chọn)
try:
    ds_hs = store.danh_sach_hs()
    so_bai_video = len(curriculum.load_videos(MON))
    tong_cau_kho = sum(len(teacher.doc_bank(v["title"], MON)) for v in curriculum.load_videos(MON))
except Exception:
    ds_hs, so_bai_video, tong_cau_kho = [], 0, 0


def _chon_mon(key, label="Môn học"):
    """Picker môn: môn có dữ liệu chọn được, môn khác ghi 'sắp có'."""
    lua_chon, ten_hien = [], {}
    for ma, c in subjects.MON_HOC.items():
        ten = f"{c['icon']} {c['ten']}" + ("" if c.get("co_du_lieu") else " (sắp có)")
        lua_chon.append(ma)
        ten_hien[ma] = ten
    mon_moi = st.selectbox(label, lua_chon, index=lua_chon.index(MON),
                           format_func=lambda m: ten_hien[m], key=key)
    if mon_moi != MON:
        if subjects.lay_mon(mon_moi).get("co_du_lieu"):
            st.session_state.mon = mon_moi
            st.session_state.pop("cau_hien_tai", None)
            st.session_state.pop("cau_da_hien", None)
            st.session_state.pop("kq_cuoi", None)
            st.rerun()
        else:
            st.info(f"Môn {subjects.lay_mon(mon_moi)['ten']} sắp có dữ liệu — hiện tại học {CFG['ten']} nhé.")
    return MON


def trang_dang_nhap():
    """Cổng vào SaaS: UI chuyên nghiệp, logic đăng nhập giữ nguyên."""
    # Thu hẹp + căn giữa trang login, ẩn sidebar để thoát cảm giác demo
    st.markdown(
        """<style>
        /* 1. Thu nhỏ layout & Tăng khoảng trắng */
        .main .block-container { 
            max-width: 460px !important; 
            padding-top: 8vh !important; 
            padding-bottom: 5vh !important;
        }
        
        /* 5. Ẩn hoàn toàn menu, footer, deploy, header */
        [data-testid="stSidebar"], [data-testid="collapsedControl"], [data-testid="stExpandSidebarButton"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }
        footer { display: none !important; }
        .stDeployButton { display: none !important; }
        
        /* 2. Hierarchy - Logo & Titles */
        .saas-logo { display: flex; justify-content: center; margin-bottom: 12px; }
        .saas-logo svg { width: 44px; height: 44px; }
        .saas-title {
            text-align: center;
            font-size: 26px;
            font-weight: 800;
            color: #0f172a;
            margin: 0 0 8px 0;
            letter-spacing: -0.5px;
        }
        .saas-tagline {
            text-align: center;
            font-size: 15px;
            color: #64748b;
            margin: 0 0 36px 0;
        }
        
        /* 3. Card */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 20px !important;
            box-shadow: 0 10px 40px -10px rgba(0,0,0,0.08), 0 1px 3px rgba(0,0,0,0.04) !important;
            border: 1px solid #f1f5f9 !important;
            background: #ffffff !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            padding: 32px !important;
            gap: 1.2rem !important; /* Space between elements */
        }
        
        .saas-card-title {
            font-size: 22px;
            font-weight: 700;
            color: #0f172a;
            margin: 0 0 4px 0;
            letter-spacing: -0.3px;
        }
        .saas-card-sub {
            font-size: 14.5px;
            color: #64748b;
            margin: 0 0 16px 0;
        }

        /* 2. Vai trò dạng 2 nút lựa chọn đẹp */
        [data-testid="stRadio"] > label {
            display: none; /* Ẩn label "Bạn là:" nếu muốn sạch hơn, hoặc giữ lại */
        }
        [data-testid="stRadio"] div[role="radiogroup"] {
            background: #f1f5f9;
            border-radius: 14px;
            padding: 4px;
            display: flex;
            gap: 4px;
            margin-bottom: 4px;
        }
        [data-testid="stRadio"] label[data-baseweb="radio"] {
            flex: 1;
            background: transparent;
            margin: 0 !important;
            padding: 10px 0 !important;
            border-radius: 10px;
            justify-content: center;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
            background: #ffffff;
            box-shadow: 0 2px 8px rgba(15,23,42,0.08);
        }
        [data-testid="stRadio"] label[data-baseweb="radio"] div {
            font-weight: 600;
            font-size: 14.5px;
            color: #64748b;
        }
        [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) div {
            color: #0f172a;
        }
        /* Ẩn dấu chấm tròn của radio */
        [data-testid="stRadio"] div[data-baseweb="radio"] > div:first-child {
            display: none;
        }
        
        /* 2. Button lớn */
        .stButton > button[kind="primary"] {
            height: 52px;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            margin-top: 12px;
            background: #2563EB;
            border: none;
            box-shadow: 0 4px 14px rgba(37,99,235,0.25);
            transition: all 0.2s ease;
        }
        .stButton > button[kind="primary"]:hover {
            background: #1d4ed8;
            box-shadow: 0 6px 20px rgba(37,99,235,0.35);
            transform: translateY(-1px);
        }

        /* 4. Hướng dẫn (Help card nhỏ) */
        .saas-help-card {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 20px;
            margin-top: 32px;
        }
        .saas-help-title {
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 600;
            color: #334155;
            font-size: 14px;
            margin-bottom: 12px;
        }
        .saas-help-card ol {
            margin: 0;
            padding-left: 20px;
            color: #475569;
            font-size: 13.5px;
            line-height: 1.6;
        }
        .saas-help-card ol li {
            margin-bottom: 4px;
        }
        .saas-support-text {
            margin-top: 12px;
            font-size: 13px;
            color: #64748b;
            padding-top: 12px;
            border-top: 1px solid #e2e8f0;
        }
        </style>""",
        unsafe_allow_html=True,
    )
    
    st.markdown(
        """<div class="saas-logo">
        <svg viewBox="0 0 52 52" xmlns="http://www.w3.org/2000/svg">
          <rect width="52" height="52" rx="14" fill="#2563EB"/>
          <path d="M26 11.5 L38.5 38 H34.4 L31.6 31.2 H20.4 L17.6 38 H13.5 L26 11.5 Z M26 18.2 L22.7 27.2 H29.3 L26 18.2 Z" fill="white"/>
          <circle cx="37" cy="14" r="2.6" fill="#BFDBFE"/>
        </svg>
        </div>
        <h1 class="saas-title">Trợ lý AI hỗ trợ học sinh và giáo viên trong học tập</h1>
        <p class="saas-tagline">Trợ lý học tập AI cho học sinh và giáo viên</p>""",
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown(
            '<div class="saas-card-title">Chào mừng trở lại 👋</div>'
            '<p class="saas-card-sub">Đăng nhập để bắt đầu học</p>',
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        role = st.radio("Vai trò", ["Học sinh", "Giáo viên"], horizontal=True, label_visibility="collapsed")

        if role == "Học sinh":
            sid_raw = st.text_input("Mã số học sinh", placeholder="Nhập mã truy cập (VD: hs_001)").strip()
            # Chuẩn hóa mã để khớp nhóm GV đã tạo (chống lệch hoa/thường, khoảng trắng)
            sid = sid_raw.strip().lower()
            if st.button("Bắt đầu học →", type="primary", use_container_width=True):
                if not sid:
                    st.error("Vui lòng nhập mã số học sinh.")
                else:
                    hs = store.doc_hs(sid)
                    if not any((h.get("id") or "").strip().lower() == sid for h in ds_hs):
                        store.luu_hs(sid, hs)
                    st.session_state.auth_role = "hs"
                    st.session_state.auth_sid = sid
                    st.session_state.tab_hs = "🏠 Trang chủ"
                    st.session_state.mon = subjects.MON_MAC_DINH
                    st.rerun()
        else:
            # Giáo viên
            st.text_input("Mã truy cập", placeholder="Dành cho giáo viên", value="gv_demo", disabled=True)
            if st.button("Bắt đầu học →", type="primary", use_container_width=True):
                st.session_state.auth_role = "gv"
                st.session_state.tab_gv = "Báo cáo lớp"
                st.session_state.mon = subjects.MON_MAC_DINH
                st.rerun()

    st.markdown(
        """<div class="saas-help-card">
        <div class="saas-help-title">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#64748b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <path d="M12 16v-4"></path>
            <path d="M12 8h.01"></path>
          </svg>
          Hướng dẫn đăng nhập
        </div>
        <ol>
            <li>Chọn vai trò tương ứng của bạn.</li>
            <li>Nhập mã truy cập được cấp để vào lớp.</li>
        </ol>
        <div class="saas-support-text">Cần hỗ trợ? Vui lòng liên hệ giáo viên chủ nhiệm hoặc bộ phận hỗ trợ kỹ thuật để được cấp mã.</div>
        </div>""",
        unsafe_allow_html=True,
    )


if not st.session_state.get("auth_role"):
    trang_dang_nhap()
    st.stop()

# ─── Lấy dữ liệu cơ bản ───
vai_tro = st.session_state.get("auth_role") # "hs" or "gv"
sid = st.session_state.get("auth_sid", "")
hs = store.doc_hs(sid) if vai_tro == "hs" else {}
MON = st.session_state.get("mon", subjects.MON_MAC_DINH)
CFG = subjects.lay_mon(MON)

# ─── Áp dụng điều hướng + Bài mới TRƯỚC khi header/sidebar tạo widget ───
# (luật Streamlit: chỉ được gán session key của widget trước khi nó hiện;
# để ở đây thì header có rerun sớm cũng không nuốt mất lệnh nhảy tab,
# và selectbox header không revert Bài vừa đổi ở trang khác.)
if vai_tro == "hs":
    if "_bai_moi" in st.session_state:
        st.session_state["header_bai"] = st.session_state.pop("_bai_moi")
    if "_tab_hs_pending" in st.session_state:
        st.session_state.tab_hs = st.session_state.pop("_tab_hs_pending")
else:
    if "_tab_gv_pending" in st.session_state:
        st.session_state.tab_gv = st.session_state.pop("_tab_gv_pending")

# ─── Ghi nhận lịch sử điều hướng (cho nút ← Quay lại) ───
_tab_ss = st.session_state.get("tab_hs" if vai_tro == "hs" else "tab_gv")
if _tab_ss:
    theme.ghi_nhan_tab(vai_tro, _tab_ss)

# ─── Header chính sau đăng nhập ───
tab_hien_tai = st.session_state.get("tab_hs", "🏠 Trang chủ") if vai_tro == "hs" else st.session_state.get("tab_gv", "👥 Lớp học")
if tab_hien_tai not in ["🏠 Trang chủ", "👤 Hồ sơ"]:
    st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
    theme.ve_nut_quay_lai(vai_tro)
    if vai_tro == "hs":
        # HS: tiêu đề trang duy nhất — căn giữa, cỡ lớn
        # (đổi môn ở 🏠 Trang chủ, đổi bài ở 📚 Bài học / 👤 Hồ sơ).
        st.markdown(f"""<div style='text-align:center;margin:10px 0 4px 0;'>
        <h1 style='font-size:40px;font-weight:800;margin:0;color:#0f172a;letter-spacing:-1px;'>{tab_hien_tai}</h1>
        <div style='width:72px;height:4px;border-radius:2px;margin:10px auto 0 auto;background:linear-gradient(90deg,#3b82f6,#8b5cf6);'></div>
        </div>""", unsafe_allow_html=True)
    else:
        # GV: bỏ hẳn ô "Môn đang học / Chương-bài" ở đầu trang cho gọn.
        # (Môn đang xem mặc định theo MON_MAC_DINH; mỗi trang GV đã có
        # tiêu đề + bộ lọc riêng bên trong.)
        pass
    st.divider()

with st.sidebar:
    st.markdown(
        """<div style='display: flex; align-items: center; gap: 10px; margin-bottom: 28px; padding-left: 4px;'>
        <svg width="32" height="32" viewBox="0 0 52 52" xmlns="http://www.w3.org/2000/svg">
          <rect width="52" height="52" rx="14" fill="#2563EB"/>
          <path d="M26 11.5 L38.5 38 H34.4 L31.6 31.2 H20.4 L17.6 38 H13.5 L26 11.5 Z M26 18.2 L22.7 27.2 H29.3 L26 18.2 Z" fill="white"/>
          <circle cx="37" cy="14" r="2.6" fill="#BFDBFE"/>
        </svg>
        <div style='font-weight: 800; font-size: 16px; color: #0f172a; letter-spacing: -0.3px;'>Trợ lý AI hỗ trợ học sinh và giáo viên trong học tập</div>
        </div>""",
        unsafe_allow_html=True
    )
    
    if vai_tro == "hs":
        ten_hs = hs.get("ten", sid)
        lop = hs.get("lop", "11")
        st.markdown(
            f"""<div style='background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 14px; padding: 16px; margin-bottom: 24px; display:flex; gap:12px; align-items:center;'>
                <div style='width:40px; height:40px; background:#2563eb; color:white; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:bold; font-size:16px;'>{ten_hs[0].upper()}</div>
                <div>
                    <div style='color:#64748b; font-size:12px; margin-bottom:2px;'>Xin chào:</div>
                    <div style='font-weight: 700; color: #1e293b; font-size: 15px;'>{ten_hs}</div>
                    <div style='color:#475569; font-size:12px; margin-top:2px;'>Học sinh lớp {lop}</div>
                </div>
            </div>""",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            """<div style='background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 14px; padding: 16px; margin-bottom: 24px; display:flex; gap:12px; align-items:center;'>
                <div style='width:40px; height:40px; background:#7c3aed; color:white; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:bold; font-size:16px;'>G</div>
                <div>
                    <div style='color:#64748b; font-size:12px; margin-bottom:2px;'>Xin chào:</div>
                    <div style='font-weight: 700; color: #1e293b; font-size: 15px;'>Giáo viên</div>
                    <div style='margin-top:4px;'><span style='background: #f5f3ff; color: #6d28d9; border: 1px solid #ddd6fe; padding: 2px 8px; border-radius: 6px; font-size: 11.5px; font-weight: 600;'>Quản lý lớp</span></div>
                </div>
            </div>""",
            unsafe_allow_html=True
        )
    st.markdown("<div style='height: 12px'></div>", unsafe_allow_html=True)

    if vai_tro == "hs":
        if "tab_hs" not in st.session_state:
            st.session_state.tab_hs = "🏠 Trang chủ"
        st.markdown("<div style='font-size:13px; font-weight:700; color:#94a3b8; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:8px; margin-left:8px;'>MENU CHÍNH</div>", unsafe_allow_html=True)
        tab = st.radio("Chức năng", theme.HS_TABS, key="tab_hs", label_visibility="collapsed")
    else:
        if "tab_gv" not in st.session_state:
            st.session_state.tab_gv = "Báo cáo lớp"
        # Migrate tab GV cũ (trước khi gộp trang) để không vỡ session đang lưu
        _TAB_GV_CU = {"Soạn bài trực quan": "Soạn bài & Học liệu",
                      "Học liệu": "Soạn bài & Học liệu",
                      "Giao bài": "Quản lý lớp",
                      "Lớp học": "Quản lý lớp"}
        if st.session_state.get("tab_gv") in _TAB_GV_CU:
            st.session_state.tab_gv = _TAB_GV_CU[st.session_state.tab_gv]
        if st.session_state.get("tab_gv") not in theme.GV_TABS:
            st.session_state.tab_gv = "Báo cáo lớp"
        st.markdown("<div style='font-size:13px; font-weight:700; color:#94a3b8; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:8px; margin-left:8px;'>QUẢN LÝ</div>", unsafe_allow_html=True)
        tab = st.radio("Chức năng", theme.GV_TABS, key="tab_gv", label_visibility="collapsed")
        
    st.markdown("<div style='min-height: 80px;'></div>", unsafe_allow_html=True)
    if st.button("⎋ Đăng xuất", use_container_width=True):
        for k in ("auth_role", "auth_sid", "tab_hs", "tab_gv", "sid",
                  "cau_hien_tai", "cau_da_hien", "kq_cuoi", "goiy_cauhoi", "bc_gv",
                  "luyen_messages", "luyen_ids", "cid", "cid_chon",
                  "_tab_hs_pending", "_tab_gv_pending", "_bai_moi",
                  "_lich_su_hs", "_tab_cuoi_hs", "_lich_su_gv", "_tab_cuoi_gv",
                  "_pf_sid", "tkb_file_da_xu_ly"):
            st.session_state.pop(k, None)
        for k in [k for k in list(st.session_state.keys()) if k.startswith("pf_")]:
            st.session_state.pop(k, None)
        st.rerun()

# ─── Main App Routing ───
if vai_tro == "hs":
    if tab == "🏠 Trang chủ":
        from ui import hs_home
        hs_home.render(sid, MON)
    elif tab == "🤖 Hỏi AI":
        from ui import hs_chat
        hs_chat.render(sid, MON)
    elif tab == "📚 Bài học":
        from ui import hs_math
        hs_math.render(sid, MON)
    elif tab == "✏ Luyện tập":
        from ui import hs_practice
        hs_practice.render(sid, MON)
    else:
        from ui import hs_profile
        hs_profile.render(sid, MON)
else:
    if tab == "Báo cáo lớp":
        from ui import gv_dashboard
        gv_dashboard.render(MON)
    elif tab == "Soạn bài & Học liệu":
        from ui import gv_soanbai
        gv_soanbai.render(MON)
    elif tab == "Quản lý lớp":
        from ui import gv_quanly
        gv_quanly.render(MON)
    else:
        from ui import gv_bank
        gv_bank.render(MON)


# Force reload
