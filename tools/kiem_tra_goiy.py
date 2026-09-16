import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import grading

# 1. Nhận diện đúng case trong ảnh
assert grading.la_xin_goi_y("tôi không biết câu này hãy hướng dẫn tôi")
assert grading.la_xin_goi_y("chỉ em với, em chịu rồi")
assert grading.la_xin_goi_y("gợi ý cho em đi")
# 2. Có nội dung toán -> vẫn chấm bình thường (kể cả kèm lời nhờ)
assert not grading.la_xin_goi_y("sin(pi/6)=1/2, còn lại không biết làm sao")
assert not grading.la_xin_goi_y("x=2")
assert not grading.la_xin_goi_y("tôi không biết " + "x" * 400)  # quá dài -> chấm
assert not grading.la_xin_goi_y("")
print("PASS nhan-dien-goi-y")

# 3. Chế độ gợi ý: mock LLM, kiểm tra không chấm sai + không lưu attempt
import core.grading as g
g.llm.chat = lambda msgs: ("Em thử nhớ xem $\\sin^2x+\\cos^2x$ bằng bao nhiêu nào?"
                           if "Goi" not in str(msgs) else "gợi ý đây")
cau = {"id": "B1-TEST", "bai": "B1", "de": "Chứng minh đẳng thức",
       "dap_an": "1", "buoc_giai": ["điểm (cos x, sin x) thuộc đường tròn đơn vị"],
       "loi_hay_gap": []}
kq = grading.goi_y_buoc_dau("test_hs_goiy", cau)
assert kq["che_do"] == "goi_y" and "```" not in kq["goi_y"], kq
assert not os.path.exists("data/attempts/test_hs_goiy_B1-TEST.json"), "lưu attempt oan"
print("PASS che-do-goi-y:", kq["goi_y"][:60])
print("THAT BAI: khong")
