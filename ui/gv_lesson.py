"""GV soạn bài trực quan: chỉnh tham số -> xem hình ngay -> lưu preset dùng lại."""
import os
import streamlit as st
from core import store, subjects, visuals, curriculum
from visuals import render as manim_render
from ui.theme import page_header

LESSON_DIR = os.path.join("data", "lessons")


def _ds_bai_luu():
    if not os.path.isdir(LESSON_DIR):
        return []
    ds = []
    for ten in sorted(os.listdir(LESSON_DIR), reverse=True):
        if ten.endswith(".json"):
            d = store.doc_json(os.path.join(LESSON_DIR, ten), {})
            if d:
                ds.append((ten, d))
    return ds


def render(mon="toan11"):
    cfg = subjects.lay_mon(mon)
    page_header(f"Soạn bài trực quan ({cfg['ten']})",
                "Kéo thanh trượt để minh họa trên lớp — lưu preset để dùng lại, không cần vẽ lại")
    loai = st.radio("Hình minh họa", ["Đồ thị hàm số lượng giác (Chương 1)",
                                       "Tiếp tuyến & đạo hàm (Chương 9)"],
                    horizontal=True)
    ds_bai = [v["title"] for v in curriculum.load_videos(mon)]
    kieu_mac_dinh = {"Đồ thị": "do_thi"}.get(loai.split()[0], "tiep_tuyen")
    bai_goi_y = manim_render.PRESETS[kieu_mac_dinh]["bai"]
    bai = st.selectbox("Gắn vào Bài (HS sẽ thấy video ở bài này)",
                       ds_bai, index=ds_bai.index(bai_goi_y) if bai_goi_y in ds_bai else 0)
    preset = {"mon": mon, "bai": bai}
    try:
        if loai.startswith("Đồ thị"):
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                ham = st.selectbox("Hàm", ["sin", "cos", "tan", "cot"])
            with c2:
                a = st.number_input("a", value=1.0, step=0.5)
            with c3:
                b = st.number_input("b", value=1.0, step=0.5)
            with c4:
                c = st.number_input("c", value=0.0, step=0.5)
            with c5:
                d = st.number_input("d", value=0.0, step=0.5)
            preset.update({"kieu": "do_thi", "ham": ham, "a": a, "b": b, "c": c, "d": d})
            st.plotly_chart(visuals.do_thi_ham_so(ham, a, b, c, d), use_container_width=True)
            st.caption("Dùng khi dạy Bài 3: tăng a xem biên độ, tăng b xem chu kì co lại.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                bt = st.text_input("f(x) =", "x**2",
                                   help="Chỉ số, x, +-*/^() và sin/cos/tan/exp/log/sqrt/pi")
            with c2:
                a = st.number_input("Điểm a", value=1.0, step=0.5)
            h = st.slider("h (cát tuyến → tiếp tuyến khi h → 0)", 0.1, 2.0, 1.0, 0.1)
            preset.update({"kieu": "tiep_tuyen", "bieu_thuc": bt, "a": a, "h": h})
            fig, so = visuals.tiep_tuyen_dao_ham(bt, a, h)
            st.plotly_chart(fig, use_container_width=True)
            st.info(f"f({a}) = {so['f(a)']} • hệ số cát tuyến ≈ {so['he_so_cat_tuyen']} • f'({a}) ≈ {so['f_dao_ham']}")
            st.caption("Dùng khi dạy Bài 31: kéo h nhỏ dần để HS thấy cát tuyến tiến về tiếp tuyến.")
    except ValueError as e:
        st.error(str(e))
        return

    st.divider()
    with st.expander("🎬 Render video Manim từ hình này (chiếu lớp, lưu cho HS xem)", expanded=False):
        st.caption("Preset đã khóa code — GV chỉ chỉnh số. Render lần đầu vài phút, lần sau lấy cache ngay.")
        kieu_manim = {"Đồ thị": "do_thi"}.get(loai.split()[0], "tiep_tuyen")
        c1, c2 = st.columns(2)
        with c1:
            quality = st.radio("Chất lượng", ["l", "m", "h"], horizontal=True,
                               help="l = 480p render nhanh; m = 720p; h = 1080p đẹp để chiếu lớp",
                               key="manim-quality")
        with c2:
            st.caption(f"Preset: **{kieu_manim}** → {manim_render.PRESETS[kieu_manim]['scene']}")
        manim_params = {k: v for k, v in preset.items()
                        if k in ("func", "ham", "a", "b", "c", "d",
                                 "expr", "bieu_thuc", "h0", "h")}
        # Chuẩn hóa tên param UI -> param Manim
        manim_params = {"func": preset.get("ham", preset.get("func", "sin")),
                        "a": preset.get("a", 1), "b": preset.get("b", 1),
                        "c": preset.get("c", 0), "d": preset.get("d", 0),
                        "expr": preset.get("bieu_thuc", preset.get("expr", "x**2")),
                        "h0": preset.get("h", preset.get("h0", 2.0))}
        if st.button("🎥 Render video", type="primary", key="manim-render"):
            with st.spinner("Đang render Manim (lần đầu vài phút, có cache cho lần sau)..."):
                try:
                    ket_qua = manim_render.render(kieu_manim, manim_params, quality=quality)
                except ValueError as e:
                    st.error(str(e))
                    ket_qua = None
            if ket_qua:
                if ket_qua["mp4"]:
                    st.session_state["manim_last"] = {"kieu": kieu_manim, "params": manim_params,
                                                      "mp4": ket_qua["mp4"]}
                    st.success("Render xong." + (" (lấy từ cache)" if ket_qua["cached"] else ""))
                    st.video(ket_qua["mp4"])
                else:
                    st.error(ket_qua["log"])
        last = st.session_state.get("manim_last")
        if last and last.get("mp4") and os.path.exists(last["mp4"]):
            st.caption(f"Video mới nhất: `{os.path.basename(last['mp4'])}` — bấm Lưu preset bên dưới để gắn vào bài.")

    st.divider()
    st.markdown("### ✨ AI dựng học liệu từ mô tả")
    st.caption("GV tả ý tưởng bằng tiếng Việt → AI lập storyboard → viết code Manim → "
               "AI khác chấm điểm → render thử → lỗi thì tự sửa tối đa 2 vòng. "
               "Xuất được video MP4 hoặc hình PNG. GV luôn được xem code trước khi lưu.")
    mo_ta = st.text_area("Mô tả video muốn làm",
                         placeholder="VD: Vẽ đồ thị y = sin x, cho chấm chạy từ -pi đến pi, "
                                     "hiện tọa độ chạy theo, nền tối chữ trắng",
                         height=90, key="ai-mo-ta")
    c1, c2, c3 = st.columns(3)
    with c1:
        quality_ai = st.radio("Chất lượng", ["l", "m", "h"], horizontal=True, key="ai-quality")
    with c2:
        loai_ai = st.radio("Xuất ra", ["Video MP4", "Hình PNG"], horizontal=True, key="ai-output")
    with c3:
        st.caption(f"Bài gắn kèm: **{bai}** (chọn ở trên)")
    bo_template = st.checkbox("Bỏ qua template, bắt AI sinh tự do (tốn token, chậm hơn)",
                              value=False, key="ai-bo-template",
                              help="Mặc định: mô tả nào khớp template có sẵn thì dùng luôn "
                                   "cho nhanh và ổn định. Chỉ bật khi muốn test pipeline "
                                   "AI storyboard → code → audit → render.")
    if st.button("✨ AI dựng học liệu", type="primary", key="ai-dung"):
        if not mo_ta.strip():
            st.error("GV nhập mô tả đã.")
        else:
            from core import manim_ai
            with st.spinner("AI đang lập storyboard → viết code → chấm điểm → render (vài phút)..."):
                try:
                    if loai_ai == "Hình PNG":
                        kq_ai = manim_ai.sinh_hinh_tu_mo_ta(mo_ta.strip(), bai=bai, mon=mon,
                                                           quality=quality_ai)
                    else:
                        kq_ai = manim_ai.sinh_video_tu_mo_ta(mo_ta.strip(), bai=bai, mon=mon,
                                                             quality=quality_ai,
                                                             dung_template=(not bo_template))
                except Exception as e:
                    st.error(str(e))
                    kq_ai = None
            if kq_ai:
                out_file = kq_ai.get("png") if loai_ai == "Hình PNG" else kq_ai.get("mp4")
                if out_file:
                    st.session_state["ai_last"] = {"mo_ta": mo_ta.strip(), "bai": bai,
                                                   "loai": loai_ai,
                                                   "code": kq_ai.get("code", ""),
                                                   "mp4": kq_ai.get("mp4", ""),
                                                   "png": kq_ai.get("png", ""),
                                                   "plan": kq_ai.get("plan"),
                                                   "audit": kq_ai.get("audit"),
                                                   "previews": kq_ai.get("previews", [])}
                    st.success("Xong." + (" (lấy từ cache)" if kq_ai.get("cached") else ""))
                    if loai_ai == "Hình PNG":
                        st.image(out_file)
                    else:
                        st.video(out_file)
                        for anh in kq_ai.get("previews", []) or []:
                            if os.path.exists(anh):
                                st.image(anh)
                else:
                    st.error(kq_ai["log"])
                    if kq_ai.get("code"):
                        with st.expander("Xem code AI đã viết (để biết vì sao hỏng)"):
                            st.code(kq_ai["code"], language="python")
    last_ai = st.session_state.get("ai_last")
    if last_ai and (last_ai.get("mp4") or last_ai.get("png")) and os.path.exists(
            last_ai.get("mp4") or last_ai.get("png")):
        if last_ai.get("plan"):
            with st.expander("Xem storyboard AI đã lập"):
                st.json(last_ai["plan"])
        if last_ai.get("audit"):
            with st.expander("Xem điểm AI chấm code"):
                st.json(last_ai["audit"])
        with st.expander("Xem code của học liệu này"):
            st.code(last_ai.get("code", ""), language="python")
        ten_ai = st.text_input("Tên preset", placeholder="VD: AI - góc quay 90 độ", key="ai-ten")
        if st.button("💾 Lưu học liệu AI này", key="ai-luu"):
            if not ten_ai.strip():
                st.error("Đặt tên preset đã.")
            else:
                safe = "".join(c if c.isalnum() else "_" for c in ten_ai.strip())[:40] or "ai_video"
                du_lieu_ai = {"ten": ten_ai.strip(), "mon": mon, "bai": last_ai["bai"],
                              "kieu": "ai_tu_do", "mo_ta": last_ai["mo_ta"],
                              "code": last_ai.get("code", ""),
                              "plan": last_ai.get("plan"),
                              "audit": last_ai.get("audit")}
                if last_ai.get("mp4"):
                    du_lieu_ai["video_mp4"] = last_ai["mp4"]
                if last_ai.get("png"):
                    du_lieu_ai["hinh_png"] = last_ai["png"]
                store.ghi_json(os.path.join(LESSON_DIR, f"{safe}.json"), du_lieu_ai)
                st.success("Đã lưu (kèm code + học liệu). HS sẽ thấy ở bài học.")
                st.rerun()

    st.divider()
    st.markdown("**Preset đã lưu**")
    ten = st.text_input("Tên preset", placeholder="VD: Bài 1 - góc 30 độ")
    if st.button("💾 Lưu hình này", type="primary"):
        if not ten.strip():
            st.error("Đặt tên preset đã.")
        else:
            safe = "".join(c if c.isalnum() else "_" for c in ten.strip())[:40] or "preset"
            du_lieu = {"ten": ten.strip(), **preset}
            last = st.session_state.get("manim_last")
            if (last and last.get("kieu") == kieu_manim and last.get("params") == manim_params
                    and os.path.exists(last.get("mp4", ""))):
                du_lieu["video_mp4"] = last["mp4"]
            elif last and last.get("kieu") == kieu_manim:
                st.warning("Tham số đã đổi sau lần render — bấm Render lại rồi hãy lưu.")
            store.ghi_json(os.path.join(LESSON_DIR, f"{safe}.json"), du_lieu)
            st.success("Đã lưu." + (" (kèm video Manim)" if du_lieu.get("video_mp4") else ""))
            st.rerun()
    for fname, d in _ds_bai_luu():
        if d.get("mon", "toan11") != mon:
            continue
        with st.expander(f"📌 {d.get('ten', fname)} ({d.get('kieu', '')})"):
            st.json({k: v for k, v in d.items()
                     if k not in ("ten", "video_mp4", "hinh_png", "code", "plan", "audit")})
            if d.get("plan"):
                with st.expander("Xem storyboard"):
                    st.json(d["plan"])
            if d.get("code"):
                with st.expander("Xem code"):
                    st.code(d["code"], language="python")
            if d.get("video_mp4") and os.path.exists(d["video_mp4"]):
                st.video(d["video_mp4"])
            if d.get("hinh_png") and os.path.exists(d["hinh_png"]):
                st.image(d["hinh_png"])
            if st.button("Xóa", key=f"xoa-lesson-{fname}"):
                os.remove(os.path.join(LESSON_DIR, fname))
                st.rerun()
