"""Component dùng chung cho UI (KPI, tag, thẻ video, hero GV)."""
import streamlit as st


def section_title(text):
    """Tiêu đề mục kiểu HS: 22px/800 (vd '📌 Việc GV giao')."""
    st.markdown(
        f"<h2 style='font-size:22px;font-weight:800;color:#0f172a;margin:4px 0 16px 0;'>{text}</h2>",
        unsafe_allow_html=True,
    )


def gv_hero(title, subtitle, chips=()):
    """Hero gradient xanh kiểu trang HS: tiêu đề + dòng phụ + chip kính mờ."""
    chip_html = "".join(
        f"<div style='background:rgba(255,255,255,0.15);padding:8px 16px;border-radius:12px;"
        f"font-weight:600;font-size:14px;backdrop-filter:blur(10px);'>{c}</div>"
        for c in chips
    )
    st.markdown(
        "<div style='background:linear-gradient(135deg,#1e3a8a 0%,#3b82f6 100%);border-radius:24px;"
        "padding:32px 36px;color:white;margin-bottom:28px;box-shadow:0 10px 30px rgba(37,99,235,0.20);'>"
        f"<h1 style='font-size:30px;font-weight:800;margin:0 0 8px 0;color:white;'>{title}</h1>"
        f"<div style='font-size:15px;color:#bfdbfe;margin-bottom:20px;'>{subtitle}</div>"
        f"<div style='display:flex;gap:12px;flex-wrap:wrap;'>{chip_html}</div></div>",
        unsafe_allow_html=True,
    )


def kpi_cards(items):
    """Thẻ KPI trắng kiểu HS: items = [(icon, value, label)]."""
    cols = st.columns(len(items))
    for col, (icon, value, label) in zip(cols, items):
        col.markdown(
            "<div style='background:white;border:1px solid #e2e8f0;border-radius:16px;"
            "padding:18px;box-shadow:0 4px 15px rgba(0,0,0,0.03);'>"
            f"<div style='font-size:22px;margin-bottom:6px;'>{icon}</div>"
            f"<div style='font-size:26px;font-weight:800;color:#0f172a;line-height:1;'>{value}</div>"
            f"<div style='font-size:12.5px;color:#64748b;font-weight:600;margin-top:6px;'>{label}</div></div>",
            unsafe_allow_html=True,
        )


def empty_state(text):
    """Hộp trống kiểu HS thay cho caption đơn."""
    st.markdown(
        f"<div style='background:white;border:1px dashed #cbd5e1;border-radius:16px;"
        f"padding:20px;text-align:center;color:#64748b;font-size:14px;'>{text}</div>",
        unsafe_allow_html=True,
    )


def kpi_row(items):
    """items: list[(label, value)] -> hiện 2-4 thẻ metric."""
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        col.metric(label, value)


def tags(ds, empty="chưa có"):
    if not ds:
        st.caption(empty)
        return
    html = " ".join(
        f"<span style='display:inline-block;background:#f1f5f9;border:1px solid #cbd5e1;"
        f"border-radius:20px;padding:3px 12px;margin:3px 2px;font-size:12.5px;"
        f"color:#334155;font-weight:500;'>{x}</span>"
        for x in ds
    )
    st.markdown(html, unsafe_allow_html=True)


def section_card(title, icon=""):
    """Context-manager style card header — gọi trước nội dung card."""
    label = f"{icon} {title}".strip()
    st.markdown(
        f"<div class='card'><h4>{label}</h4>",
        unsafe_allow_html=True,
    )


def _extract_yt_id_widget(link):
    if "youtu.be/" in link:
        return link.split("youtu.be/")[1].split("?")[0]
    import urllib.parse
    if "v=" in link:
        return urllib.parse.parse_qs(urllib.parse.urlparse(link).query).get("v", [""])[0]
    return ""

def video_card(v, key_prefix=""):
    """Thẻ video: thumbnail + tiêu đề + chapter + nút xem + ý chính."""
    yt_id = _extract_yt_id_widget(v.get("link", ""))
    thumb = f"https://img.youtube.com/vi/{yt_id}/hqdefault.jpg" if yt_id else "https://via.placeholder.com/320x180.png?text=Video"
    
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
    c_img, c_info = st.columns([1, 2.5])
    
    with c_img:
        st.html(f"<img src='{thumb}' style='width:100%; border-radius:12px; border: 1px solid #e2e8f0; object-fit: cover; aspect-ratio: 16/9;'>")
        
    with c_info:
        st.html(f"<h4 style='color:#0f172a; margin:0 0 6px 0; font-size: 15.5px; font-weight: 700;'>{v.get('title', 'Video')}</h4>")
        if v.get("chapter"):
            st.html(f"<div style='font-size:12.5px; color:#64748b; font-weight:600; margin-bottom:6px;'>{v['chapter']}</div>")
            
        bullets = "".join([f"<li style='color:#475569;font-size:13px;margin-bottom:2px;'>{y}</li>" for y in (v.get("tom_tat") or v.get("content", []))[:3]])
        if bullets:
            st.html(f"<ul style='margin-top:0; padding-left:20px; margin-bottom:12px;'>{bullets}</ul>")
        
        st.link_button("▶ Xem video trên YouTube", v["link"], key=f"{key_prefix}-link-{v.get('title','')}")


def do_kho_sao(n):
    return "★" * int(n) + "☆" * (3 - int(n))


CAU_HOI_MAU = [  # giữ để tương thích cũ (bản Toán 11)
    "sin²x + cos²x = ? Giải thích từ đường tròn lượng giác.",
    "Đạo hàm của y = x² + 3x tại x = 1 là bao nhiêu? Dẫn dắt từng bước.",
    "Đổi 120° sang radian và cho biết điểm biểu diễn ở góc phần tư nào?",
]


def cau_hoi_mau(mon="toan11"):
    """Câu hỏi mẫu theo môn (môn chưa có dữ liệu -> rỗng)."""
    from core import subjects
    return subjects.lay_mon(mon).get("cau_hoi_mau", [])
