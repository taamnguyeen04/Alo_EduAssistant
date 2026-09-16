# Manim Math Template Pack v1

Bộ **5 template Manim production-oriented** cho luồng:

`Mô tả giáo viên → AI chọn template → điền slot → render Manim`

## Template có sẵn

1. **LTG_01_unit_circle** — Đường tròn lượng giác, M(cos α, sin α)
2. **LTG_05_sine_graph** — Từ chuyển động tròn đến đồ thị y = sin α
3. **LTG_06_trig_transform** — Biến đổi y = a sin(bx+c)+d
4. **DH_01_secant_to_tangent** — Cát tuyến → tiếp tuyến, định nghĩa đạo hàm
5. **DH_07_extrema** — Cực trị, tiếp tuyến và dấu của f'

## Cấu trúc mỗi template

- `manifest.json`: dùng khi nào, slot nào AI được phép điền.
- `storyboard.json`: flow sư phạm cố định theo từng beat.
- `rules.json`: guardrail chống chồng chữ / quá tải thị giác.
- `examples.json`: ví dụ prompt → params.
- `scene.py`: Manim scene hoàn chỉnh, đọc params qua biến môi trường `MANIM_TEMPLATE_JSON`.

AI nên **chọn template + điền slot**, không viết lại `scene.py`.

## Nguyên tắc thiết kế đã áp dụng

- Một ý chính mỗi beat.
- Khoảng 3–5 nhãn có ý nghĩa trong một beat.
- Tách rõ vùng title / diagram / formula.
- Annotation tạm được `FadeOut` trước khi kết luận mới xuất hiện.
- Ưu tiên `TransformMatchingTex` / `ReplacementTransform` thay vì spawn text mới.
- Dùng `ValueTracker`, `always_redraw`, `TracedPath`, `MovingCameraScene` ở nơi phù hợp.

## Yêu cầu môi trường

- Python 3.10+
- Manim Community
- FFmpeg
- LaTeX distribution (khuyến nghị/bắt buộc với các scene dùng `MathTex`)

## Validate pack

```bash
python scripts/validate_pack.py
```

## Render thử

### Góc 60° trên đường tròn lượng giác

```bash
python scripts/render_template.py LTG_01_unit_circle --params "{\"angle_deg\":60,\"show_numeric\":true}" --quality l
```

### Từ đường tròn đến đồ thị sin

```bash
python scripts/render_template.py LTG_05_sine_graph --params "{\"cycles\":1}" --quality l
```

### y = 2 sin(2x + π/4) + 1

```bash
python scripts/render_template.py LTG_06_trig_transform --params "{\"a\":2,\"b\":2,\"c\":0.7853981634,\"d\":1}" --quality l
```

### Đạo hàm x² tại x=1

```bash
python scripts/render_template.py DH_01_secant_to_tangent --params "{\"function\":\"x^2\",\"a\":1,\"h_start\":2}" --quality l
```

### Cực trị y=x³−3x

```bash
python scripts/render_template.py DH_07_extrema --params "{\"function\":\"x^3-3x\"}" --quality l
```

## Luồng tích hợp khuyến nghị

```text
Prompt giáo viên
   ↓
Template Matcher (LLM)
   ↓
template_id + confidence + params
   ↓
confidence >= 0.65 ?
   ├─ Có → validate params → render template
   └─ Không → composite/freeform fallback
```

`ai_prompts/template_matcher_system.txt` và `template_adapter_system.txt` đã có sẵn contract cho AI.

## Production notes

1. Không cho LLM sửa trực tiếp template đã duyệt.
2. Validate slot theo `manifest.json` trước render.
3. Cache theo `(template_id, version, params, quality)`.
4. Render trong worker/container riêng.
5. Bước tiếp theo nên thêm **frame-vision QA**: trích 4–6 frame để kiểm tra overlap, crop, nội dung sai hoặc quá dày.
6. Khi sửa code scene, tăng `version` trong manifest để cache không dùng lại video cũ.

## Template nên bổ sung tiếp

- LTG_03_identity_sin2_cos2
- LTG_04_special_angles
- LTG_07_tangent_asymptotes
- LTG_08_trig_equation_circle
- DH_02_difference_quotient
- DH_04_derivative_sin
- DH_05_product_rule
- DH_06_chain_rule
- DH_10_second_derivative_concavity
