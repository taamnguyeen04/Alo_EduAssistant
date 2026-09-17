"""Hình trực quan cho GV soạn bài (Plotly, chạy tức thì trong Streamlit).

3 preset bám Chương 1 + 9:
- duong_tron_luong_giac(goc_do): điểm M, hình chiếu sin/cos, cung góc.
- do_thi_ham_so(ham, ...): sin/cos/tan + tham số a,b,c,d (y = a·f(bx+c)+d).
- tiep_tuyen_dao_ham(bieu_thuc, a, h): đồ thị f, cát tuyến qua (a,h) và
  tiếp tuyến tại a — minh họa định nghĩa đạo hàm.

Biểu thức HS gõ được kiểm tra an toàn: chỉ số, x, +-*/^() và hàm
sin/cos/tan/exp/log/sqrt/pi. Không dùng eval() trực tiếp.
"""
import ast
import math

import numpy as np

try:
    import pandas  # noqa: F401 — như app.py: tránh plotly gặp pandas đang nạp dở
except ImportError:
    pass

_HAM_CHO_PHEP = {
    "sin": np.sin, "cos": np.cos, "tan": np.tan,
    "arcsin": np.arcsin, "arccos": np.arccos, "arctan": np.arctan,
    "exp": np.exp, "log": np.log, "sqrt": np.sqrt, "abs": np.abs,
    "pi": math.pi, "e": math.e,
}
_NODE_CHO_PHEP = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call, ast.Name,
    ast.Load, ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.Div,
    ast.Pow, ast.USub, ast.UAdd, ast.Mod,
)


def _kiem_tra_an_toan(bieu_thuc):
    # Duyệt cây AST: node/tên hàm nào ngoài danh sách cho phép thì chặn ngay.
    try:
        tree = ast.parse(bieu_thuc, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"Biểu thức sai cú pháp: {e}")
    for node in ast.walk(tree):
        if not isinstance(node, _NODE_CHO_PHEP):
            raise ValueError(f"Ký hiệu không cho phép: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id not in (*_HAM_CHO_PHEP, "x"):
            raise ValueError(f"Tên không cho phép: {node.id}")
        if isinstance(node, ast.Call) and not isinstance(node.func, ast.Name):
            raise ValueError("Chỉ gọi hàm dạng tên(...)")
    return tree


def tinh_gia_tri(bieu_thuc, x):
    """Tính f(x), x là số hoặc mảng numpy. Ném ValueError nếu biểu thức bẩn."""
    # Chấp nhận ^ viết tay của HS rồi mới kiểm tra an toàn trước khi eval.
    tree = _kiem_tra_an_toan(bieu_thuc.replace("^", "**"))
    code = compile(tree, "<bieu-thuc>", "eval")
    return eval(code, {"__builtins__": {}}, {**_HAM_CHO_PHEP, "x": x})  # noqa: S307


def _khung_chung(tieu_de, x_label="x", y_label="y"):
    import plotly.graph_objects as go
    fig = go.Figure()
    fig.update_layout(title=tieu_de, xaxis_title=x_label, yaxis_title=y_label,
                      showlegend=True, height=480,
                      xaxis={"zeroline": True}, yaxis={"zeroline": True})
    return fig


def duong_tron_luong_giac(goc_do=30):
    """Đường tròn đơn vị + điểm M(góc) + hình chiếu sin/cos."""
    import plotly.graph_objects as go
    goc = math.radians(goc_do)
    x, y = math.cos(goc), math.sin(goc)
    t = np.linspace(0, 2 * math.pi, 200)
    fig = _khung_chung(f"Đường tròn lượng giác — góc {goc_do}°")
    fig.add_trace(go.Scatter(x=np.cos(t).tolist(), y=np.sin(t).tolist(),
                             mode="lines", name="x²+y²=1"))
    fig.add_trace(go.Scatter(x=[0, x], y=[0, y], mode="lines+markers", name=f"tia Ox→OM ({goc_do}°)"))
    fig.add_trace(go.Scatter(x=[x, x], y=[0, y], mode="lines",
                             line={"dash": "dash", "color": "red"}, name=f"sin = {y:.3f}"))
    fig.add_trace(go.Scatter(x=[0, x], y=[y, y], mode="lines",
                             line={"dash": "dash", "color": "blue"}, name=f"cos = {x:.3f}"))
    fig.add_trace(go.Scatter(x=[x], y=[y], mode="markers",
                             marker={"size": 10, "color": "green"}, name="M"))
    fig.update_layout(xaxis={"range": [-1.3, 1.3]}, yaxis={"range": [-1.3, 1.3]})
    return fig


_HAM_LG = {"sin": np.sin, "cos": np.cos, "tan": np.tan, "cot": lambda x: 1 / np.tan(x)}


def do_thi_ham_so(ham="sin", a=1.0, b=1.0, c=0.0, d=0.0, so_ky=2):
    """y = a·f(bx+c)+d trên [-so_ki·π, so_ki·π]. Tan/cot tự cắt điểm gián đoạn."""
    # Tan/cot vọt vô cùng ở điểm gián đoạn nên cắt ngọn để đồ thị không xấu.
    import plotly.graph_objects as go
    f = _HAM_LG[ham]
    xs = np.linspace(-so_ky * math.pi, so_ky * math.pi, 1200)
    with np.errstate(divide="ignore", invalid="ignore"):
        ys = a * f(b * xs + c) + d
    if ham in ("tan", "cot"):
        ys = np.where(np.abs(ys) > 12, np.nan, ys)
    fig = _khung_chung(f"y = {a}·{ham}({b}x+{c})+{d}")
    fig.add_trace(go.Scatter(x=np.asarray(xs).tolist(), y=np.asarray(ys).tolist(),
                             mode="lines", name=f"y = {a}·{ham}({b}x+{c})+{d}"))
    fig.update_layout(xaxis={"range": [-so_ky * math.pi, so_ky * math.pi]})
    return fig


def tiep_tuyen_dao_ham(bieu_thuc="x**2", a=1.0, h=1.0, bien=2.0):
    """f + cát tuyến qua x=a và x=a+h + tiếp tuyến tại a (đạo hàm = giới hạn)."""
    import plotly.graph_objects as go
    xs = np.linspace(a - bien, a + bien, 400)
    with np.errstate(divide="ignore", invalid="ignore"):
        ys = np.asarray(tinh_gia_tri(bieu_thuc, xs), dtype=float)
    fa = float(np.asarray(tinh_gia_tri(bieu_thuc, np.array([a])), dtype=float)[0])
    fah = float(np.asarray(tinh_gia_tri(bieu_thuc, np.array([a + h])), dtype=float)[0])
    hs_cat_tuyen = (fah - fa) / h if h else float("nan")
    # Đạo hàm số bằng sai phân trung tâm
    e = 1e-6
    fp = float(np.asarray(tinh_gia_tri(bieu_thuc, np.array([a + e])), dtype=float)[0])
    fm = float(np.asarray(tinh_gia_tri(bieu_thuc, np.array([a - e])), dtype=float)[0])
    f_dao_ham = (fp - fm) / (2 * e)
    fig = _khung_chung(f"Tiếp tuyến của y = {bieu_thuc} tại x = {a}")
    fig.add_trace(go.Scatter(x=np.asarray(xs).tolist(), y=np.asarray(ys).tolist(),
                             mode="lines", name=f"y = {bieu_thuc}"))
    fig.add_trace(go.Scatter(x=[a, a + h], y=[fa, fah], mode="lines+markers",
                             line={"dash": "dash", "color": "orange"},
                             name=f"cát tuyến (h={h}, dốc≈{hs_cat_tuyen:.3f})"))
    xt = np.linspace(a - bien, a + bien, 100).tolist()
    fig.add_trace(go.Scatter(x=xt, y=(fa + f_dao_ham * (np.asarray(xt) - a)).tolist(), mode="lines",
                             line={"color": "red"},
                             name=f"tiếp tuyến (f'({a})≈{f_dao_ham:.3f})"))
    fig.add_trace(go.Scatter(x=[a], y=[fa], mode="markers",
                             marker={"size": 10, "color": "green"}, name="điểm tiếp xúc"))
    return fig, {"f(a)": round(fa, 4), "he_so_cat_tuyen": round(hs_cat_tuyen, 4) if h else None,
                 "f_dao_ham": round(f_dao_ham, 4)}
