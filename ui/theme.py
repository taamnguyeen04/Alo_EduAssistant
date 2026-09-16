"""Theme + điều hướng dùng chung (chỉ CSS/trình bày, không đụng logic)."""
import streamlit as st

HS_TABS = ["🏠 Trang chủ", "🤖 Hỏi AI", "📚 Bài học", "✏ Luyện tập", "👤 Hồ sơ"]
GV_TABS = ["Báo cáo lớp", "Kho đề", "Soạn bài & Học liệu", "Quản lý lớp"]


def apply_theme():
    st.markdown("""
    <style>
    /* ───────────── Base: Modern Education SaaS ───────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', Roboto, sans-serif;
        color: #1E293B;
        font-size: 21px;
    }

    [data-testid="stAppViewContainer"] {
        background-color: #F8FAFC;
    }

    /* ═════ Ẩn toàn bộ UI mặc định của Streamlit → website độc lập ═════ */
    #MainMenu { display: none !important; visibility: hidden !important; }
    footer { display: none !important; visibility: hidden !important; }
    [data-testid="stFooter"] { display: none !important; }
    [data-testid="stToolbar"] { display: none !important; visibility: hidden !important; }
    [data-testid="stDecoration"] { display: none !important; }
    [data-testid="stStatusWidget"] { display: none !important; visibility: hidden !important; }
    .stDeployButton { display: none !important; visibility: hidden !important; }
    [data-testid="stAppDeployButton"] { display: none !important; }
    [data-testid="stHeaderActionElements"] { display: none !important; }
    /* Ẩn hẳn thanh header mặc định (chứa menu góc phải + nút Deploy) */
    [data-testid="stHeader"] { display: none !important; }
    .stApp > header { display: none !important; }
    /* Bỏ padding mặc định do header để lại */
    [data-testid="stAppViewContainer"] > .main { padding-top: 0 !important; }
    .main .block-container {
        max-width: 1100px;
        padding-top: 2rem !important;
        padding-bottom: 2.5rem !important;
    }

    h1, h2, h3, h4 { color: #1E293B; letter-spacing: -0.3px; }
    h1 { font-size: 2.5rem !important; }
    h2 { font-size: 2.0rem !important; }
    h3 { font-size: 1.6rem !important; }
    h4 { font-size: 1.35rem !important; }

    /* ───────────── Tăng cỡ chữ toàn trang (nội dung đọc chính) ───────────── */
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    [data-testid="stMarkdownContainer"] div,
    .stMarkdown p, .stMarkdown li {
        font-size: 1.3rem !important;
        line-height: 1.8 !important;
    }
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li {
        font-size: 1.35rem !important;
        line-height: 1.85 !important;
    }
    [data-testid="stExpander"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stExpander"] [data-testid="stMarkdownContainer"] li {
        font-size: 1.3rem !important;
        line-height: 1.8 !important;
    }
    [data-testid="stDataFrame"], [data-testid="stTable"], table {
        font-size: 1.25rem !important;
    }

    /* ───────────── SaaS Login brand ───────────── */
    .saas-logo { display: flex; justify-content: center; margin: 6px 0 14px 0; }
    .saas-title {
        text-align: center;
        font-size: 46px;
        font-weight: 700;
        color: #1E293B;
        letter-spacing: -0.5px;
        margin: 0;
        line-height: 1.15;
    }
    .saas-tagline {
        text-align: center;
        font-size: 21px;
        font-weight: 400;
        color: #64748B;
        margin: 8px 0 24px 0;
        line-height: 1.5;
    }
    .saas-card-title {
        font-size: 24px;
        font-weight: 700;
        color: #1E293B;
        margin: 2px 0 4px 0;
    }
    .saas-card-sub {
        font-size: 19px;
        color: #64748B;
        margin: 0 0 18px 0;
    }
    .saas-guide {
        background: #FFFFFF;
        border: 1px solid #E6ECF3;
        border-radius: 12px;
        padding: 13px 16px;
        margin-top: 14px;
        font-size: 18.5px;
        color: #475569;
        line-height: 1.8;
        box-shadow: 0 1px 3px rgba(15,23,42,0.04);
    }
    .saas-guide-head {
        display: flex;
        align-items: center;
        gap: 7px;
        font-weight: 600;
        font-size: 18.5px;
        color: #1E293B;
        margin-bottom: 4px;
    }
    .saas-support {
        text-align: center;
        font-size: 17px;
        color: #94A3B8;
        margin-top: 14px;
    }

    /* ───────────── Card container (Streamlit border container) ───────────── */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #FFFFFF;
        border: 1px solid #E6ECF3;
        border-radius: 18px;
        box-shadow: 0 10px 32px rgba(15,23,42,0.07);
    }

    /* ───────────── Labels ───────────── */
    [data-testid="stSelectbox"] label,
    [data-testid="stTextInput"] label,
    [data-testid="stRadio"] > label {
        font-size: 18.5px !important;
        font-weight: 600 !important;
        color: #334155 !important;
    }

    /* ───────────── Selectbox & TextInput ───────────── */
    [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        min-height: 56px;
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        font-size: 19.5px;
        color: #1E293B;
    }
    [data-testid="stSelectbox"] div[data-baseweb="select"]:hover > div {
        border-color: #CBD5E1;
    }
    [data-testid="stSelectbox"] div[data-baseweb="select"]:focus-within > div {
        background: #FFFFFF;
        border-color: #2563EB;
        box-shadow: 0 0 0 3px rgba(37,99,235,0.12);
    }
    [data-testid="stTextInput"] input {
        height: 56px;
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        font-size: 19.5px;
        color: #1E293B;
        padding: 0 14px;
    }
    [data-testid="stTextInput"] input:hover {
        border-color: #CBD5E1;
    }
    [data-testid="stTextInput"] input:focus {
        background: #FFFFFF;
        border-color: #2563EB;
        box-shadow: 0 0 0 3px rgba(37,99,235,0.12);
        outline: none;
    }
    [data-testid="stTextInput"] input::placeholder {
        color: #94A3B8;
    }

    /* ───────────── Radio & Sidebar Menu ───────────── */
    [data-testid="stRadio"] div[role="radiogroup"] { gap: 12px; }
    [data-testid="stRadio"] input[type="radio"] { accent-color: #2563EB; }
    [data-testid="stRadio"] label {
        font-weight: 500;
        font-size: 1.25rem;
        color: #334155;
    }

    /* Tạo style chuyên nghiệp cho menu ở Sidebar */
    /* Tạo style chuyên nghiệp cho menu ở Sidebar */
    [data-testid="stSidebar"] div[role="radiogroup"] {
        gap: 4px !important;
    }
    [data-testid="stSidebar"] label[data-baseweb="radio"] > div:first-child {
        display: none !important;
    }
    [data-testid="stSidebar"] label[data-baseweb="radio"] {
        padding: 10px 16px;
        background: transparent;
        border-radius: 8px;
        margin: 0;
        cursor: pointer;
        transition: all 0.2s ease;
        border: 1px solid transparent;
    }
    [data-testid="stSidebar"] label[data-baseweb="radio"]:hover {
        background: #f1f5f9;
    }
    [data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
    }
    [data-testid="stSidebar"] label[data-baseweb="radio"] div {
        font-size: 20px;
        color: #475569;
        margin: 0 !important;
    }
    [data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) div {
        color: #2563eb;
        font-weight: 700;
    }

    /* ───────────── Buttons ───────────── */
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
        font-size: 1.25rem;
        min-height: 56px;
        letter-spacing: 0.1px;
    }
    .stButton > button[kind="primary"] {
        width: 100%;
        min-height: 58px;
        background: #2563EB;
        border: 1px solid #2563EB;
        color: #FFFFFF;
        font-weight: 600;
        font-size: 20px;
        border-radius: 10px;
        transition: background 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .stButton > button[kind="primary"]:hover {
        background: #1D4ED8;
        border-color: #1D4ED8;
        box-shadow: 0 4px 12px rgba(37,99,235,0.28);
    }
    .stButton > button[kind="primary"]:active {
        background: #1E40AF;
        border-color: #1E40AF;
    }
    .stButton > button:not([kind="primary"]):hover {
        border-color: #94a3b8;
    }

    /* ───────────── Legacy compat (.hero / .card) ───────────── */
    .hero {
        background: #FFFFFF;
        color: #1E293B;
        border-radius: 16px;
        padding: 24px 28px;
        margin-bottom: 20px;
        border: 1px solid #E6ECF3;
        box-shadow: 0 4px 20px rgba(15,23,42,0.06);
    }
    .hero h2 { color: #1E293B; margin: 0 0 6px 0; font-size: 1.9rem; font-weight: 700; }
    .hero p { color: #64748B; margin: 0; font-size: 1.3rem; }
    .card {
        background: #ffffff;
        border: 1px solid #E6ECF3;
        border-radius: 16px;
        padding: 20px 22px;
        margin-bottom: 16px;
        box-shadow: 0 1px 4px rgba(15,23,42,0.05);
        font-size: 1.28rem;
    }
    .card h4 { margin: 0 0 10px 0; font-weight: 600; font-size: 1.3rem; color: #1e293b; }

    /* ───────────── Metrics / Sidebar / misc (trang trong) ───────────── */
    [data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 14px 16px;
    }
    [data-testid="stMetricLabel"] {
        font-size: 1.08rem; font-weight: 500; color: #64748b;
        text-transform: uppercase; letter-spacing: 0.5px;
    }
    [data-testid="stMetricValue"] { font-size: 2.15rem; font-weight: 700; color: #0f172a; }
    [data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid #e2e8f0; }
    [data-testid="stSidebar"] .block-container { padding-top: 1.2rem; }
    .side-title { font-weight: 800; font-size: 22px; color: #0f172a; margin-bottom: 2px; }
    .side-sub { color: #64748b; font-size: 17px; margin-bottom: 10px; }
    .side-badge {
        display: inline-block; background: #eff6ff; color: #1d4ed8;
        border: 1px solid #bfdbfe; border-radius: 6px;
        font-size: 16px; font-weight: 600; padding: 2px 8px; margin-bottom: 8px;
    }
    /* ───────────── Course Modules (Expanders) ───────────── */
    [data-testid="stExpander"] { 
        border: 1px solid #e2e8f0; 
        border-radius: 12px; 
        box-shadow: 0 2px 8px rgba(15,23,42,0.04);
        background: #ffffff;
        margin-bottom: 12px;
        overflow: hidden;
    }
    [data-testid="stExpander"] summary { 
        padding: 16px 20px;
        background: #f8fafc;
        border-bottom: 1px solid transparent;
        transition: background 0.2s ease;
    }
    [data-testid="stExpander"] summary:hover {
        background: #f1f5f9;
    }
    [data-testid="stExpander"] summary p {
        font-weight: 700 !important;
        font-size: 20px !important;
        color: #0f172a !important;
        margin: 0;
    }
    [data-testid="stExpander"][open] summary {
        border-bottom-color: #e2e8f0;
    }
    hr { border-color: #e2e8f0; margin: 12px 0; }
    [data-testid="stChatMessage"] { border-radius: 10px; border: 1px solid #f1f5f9; margin-bottom: 6px; font-size: 1.3rem; }
    [data-testid="stAlert"] { border-radius: 10px; font-size: 1.25rem; }
    button[data-baseweb="tab"] { font-weight: 600; font-size: 1.2rem; color: #64748b; }
    button[data-baseweb="tab"][aria-selected="true"] { color: #2563EB; }
    .stCaption, small { color: #64748b; font-size: 1.1rem; }
    [data-testid="stCaptionContainer"] { font-size: 1.15rem !important; }
    [data-testid="stChatInput"] textarea { font-size: 1.3rem !important; }

    /* ───────────── Responsive ───────────── */
    @media (max-width: 640px) {
        .saas-title { font-size: 36px; }
        .saas-tagline { font-size: 19.5px; margin-bottom: 18px; }
        .main .block-container { padding-left: 1rem !important; padding-right: 1rem !important; }
    }
    </style>
    """, unsafe_allow_html=True)


def goto(tab):
    """Nhảy tab HS từ bất kỳ trang nào (dùng với st.rerun ở nơi gọi).

    Không gán trực tiếp key widget (Streamlit cấm sau khi widget đã hiện),
    mà để app.py áp dụng vào ĐẦU lượt chạy sau.
    Tab lạ (không có trong HS_TABS) sẽ bị bỏ qua để khỏi rớt về Trang chủ.
    """
    if tab not in HS_TABS:
        return
    st.session_state["_tab_hs_pending"] = tab


def chon_bai_va_di(sid, bai, tab):
    """Đổi Bài hiện tại + nhảy tab, không gây lệch với selectbox header.

    Ghi DB ngay, đồng thời đặt cờ `_bai_moi` để app.py đồng bộ
    `header_bai` TRƯỚC khi widget header được tạo (tránh extra rerun
    revert Bài + nháy về tab khác). Nơi gọi nhớ `st.rerun()` sau đó.
    """
    from core import store
    hs = store.doc_hs(sid)
    if bai and bai != hs.get("bai_hien_tai"):
        hs["bai_hien_tai"] = bai
        store.luu_hs(sid, hs)
        st.session_state["_bai_moi"] = bai
    goto(tab)


def page_header(tieu_de, phu_de=""):
    phu = f"<p style='margin:6px 0 0 0;color:#64748b;font-size:1.25rem;'>{phu_de}</p>" if phu_de else ""
    st.markdown(
        f"""<div style='border-left:4px solid #2563EB;padding-left:16px;margin:8px 0 20px 0;'>
        <h2 style='margin:0;font-size:1.95rem;font-weight:800;color:#0f172a;letter-spacing:-0.4px;'>{tieu_de}</h2>
        {phu}</div>""",
        unsafe_allow_html=True,
    )
