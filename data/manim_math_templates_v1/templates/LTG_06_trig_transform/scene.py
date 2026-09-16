from pathlib import Path
import sys, math
import numpy as np
from manim import *
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from common.config import load_params, number
from common.theme import *
from common.math_utils import clean_num

def latex_num(v):
    if abs(v-math.pi)<1e-4:return r'\pi'
    if abs(v-math.pi/2)<1e-4:return r'\frac{\pi}{2}'
    if abs(v-math.pi/4)<1e-4:return r'\frac{\pi}{4}'
    if abs(v+math.pi/4)<1e-4:return r'-\frac{\pi}{4}'
    return clean_num(v,2)

class TrigTransformTemplate(Scene):
    def construct(self):
        apply_theme(self); p=load_params(); a=number(p,'a',2,-4,4); b=number(p,'b',2,-4,4)
        if abs(b)<.15:b=1.0
        c=number(p,'c',math.pi/4,-2*math.pi,2*math.pi); d=number(p,'d',1,-3,3); speed=number(p,'duration_scale',1,.6,2)
        self.play(FadeIn(title('Biến đổi đồ thị hàm số lượng giác')),run_time=.5*speed)
        axes=Axes(x_range=[-2*math.pi,2*math.pi,math.pi/2],y_range=[-5,5,1],x_length=11.2,y_length=5,tips=False,axis_config={'color':GREY_B,'stroke_width':1.6}).shift(DOWN*.25)
        self.play(Create(axes),run_time=.7*speed)
        def graph(A=1,B=1,C=0,D=0,color=PRIMARY):return axes.plot(lambda x:A*np.sin(B*x+C)+D,x_range=[-2*math.pi,2*math.pi],color=color,stroke_width=4)
        def form(A=1,B=1,C=0,D=0):
            if (A,B,C,D)==(1,1,0,0):s=r'y=\sin x'
            elif B==1 and C==0 and D==0:s=rf'y={latex_num(A)}\sin x'
            elif C==0 and D==0:s=rf'y={latex_num(A)}\sin({latex_num(B)}x)'
            elif D==0:s=rf'y={latex_num(A)}\sin({latex_num(B)}x{"+" if C>=0 else ""}{latex_num(C)})'
            else:s=rf'y={latex_num(A)}\sin({latex_num(B)}x{"+" if C>=0 else ""}{latex_num(C)}){"+" if D>=0 else ""}{latex_num(D)}'
            return MathTex(s,color=WHITE_SOFT).scale(.82).to_corner(UL,buff=.58).shift(DOWN*.38)
        g=graph(); ft=form(); self.play(Create(g),Write(ft),run_time=.9*speed); self.wait(.3*speed)
        g2=graph(a,1,0,0,ACCENT); f2=form(a,1,0,0); card=info_card('Tham số a',[f'Biên độ = |a| = {abs(a):.2g}','Kéo giãn/nén theo Oy'],4.2).to_corner(DR,buff=.5)
        self.play(ReplacementTransform(g,g2),TransformMatchingTex(ft,f2),FadeIn(card),run_time=1*speed); g,ft=g2,f2; self.wait(.6*speed); self.play(FadeOut(card),run_time=.3*speed)
        g3=graph(a,b,0,0,SECONDARY); f3=form(a,b,0,0); T=2*math.pi/abs(b); card=info_card('Tham số b',[f'Chu kỳ T ≈ {T:.2f}','|b| lớn → co theo Ox'],4.3).to_corner(DR,buff=.5)
        self.play(ReplacementTransform(g,g3),TransformMatchingTex(ft,f3),FadeIn(card),run_time=1*speed); g,ft=g3,f3; self.wait(.6*speed); self.play(FadeOut(card),run_time=.3*speed)
        g4=graph(a,b,c,0,GOOD); f4=form(a,b,c,0); shift=-c/b; card=info_card('Tham số c',[f'Dịch ngang = -c/b ≈ {shift:.2f}','Dấu dịch phụ thuộc cả b và c'],4.5).to_corner(DR,buff=.5)
        self.play(ReplacementTransform(g,g4),TransformMatchingTex(ft,f4),FadeIn(card),run_time=1*speed); g,ft=g4,f4; self.wait(.6*speed); self.play(FadeOut(card),run_time=.3*speed)
        g5=graph(a,b,c,d,DANGER); f5=form(a,b,c,d); mid=DashedLine(axes.c2p(-2*math.pi,d),axes.c2p(2*math.pi,d),color=MUTED,stroke_width=2); card=info_card('Tham số d',[f'Dịch dọc {d:+.2g}',f'Đường trung bình y = {d:.2g}'],4.2).to_corner(DR,buff=.5)
        self.play(ReplacementTransform(g,g5),TransformMatchingTex(ft,f5),Create(mid),FadeIn(card),run_time=1*speed); self.wait(.7*speed); self.play(FadeOut(card),run_time=.3*speed)
        summary=info_card('Bốn vai trò',['a → biên độ','b → chu kỳ','c → dịch ngang','d → dịch dọc'],4.4).to_corner(DR,buff=.5)
        self.play(FadeIn(summary,shift=UP*.1),run_time=.5*speed); self.wait(1.3*speed)
