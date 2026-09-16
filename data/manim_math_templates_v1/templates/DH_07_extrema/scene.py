from pathlib import Path
import sys
from manim import *
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from common.config import load_params, number, boolean, choice
from common.theme import *
from common.math_utils import EXTREMA_FUNCTIONS

class ExtremaTemplate(MovingCameraScene):
    def construct(self):
        apply_theme(self); p=load_params(); key=choice(p,'function','x^3-3x',EXTREMA_FUNCTIONS.keys()); spec=EXTREMA_FUNCTIONS[key]
        f,df,flatex=spec['fn'],spec['df'],spec['latex']; xlo,xhi=spec['x_range']; ylo,yhi=spec['y_range']; critical=spec['critical']
        speed=number(p,'duration_scale',1,.6,2); show_chart=boolean(p,'show_sign_chart',True); show_slope=boolean(p,'show_slope_value',True)
        self.play(FadeIn(title('Cực trị và dấu của đạo hàm')),run_time=.5*speed)
        axes=Axes(x_range=[xlo,xhi,(xhi-xlo)/4],y_range=[ylo,yhi,(yhi-ylo)/6],x_length=8.4,y_length=4.9,tips=False,axis_config={'color':GREY_B,'stroke_width':1.6}).shift(LEFT*2.1+DOWN*.15)
        graph=axes.plot(lambda x:float(f(x)),x_range=[xlo,xhi],color=PRIMARY,stroke_width=4); fl=MathTex(rf'f(x)={flatex}',color=PRIMARY).scale(.72).next_to(axes,UP,buff=.12)
        self.play(Create(axes),Create(graph),FadeIn(fl),run_time=.95*speed)
        t=ValueTracker(xlo+.15*(xhi-xlo))
        point=always_redraw(lambda:Dot(axes.c2p(t.get_value(),float(f(t.get_value()))),color=GOOD,radius=.08))
        def tanline():
            x=t.get_value(); y=float(f(x)); m=float(df(x)); span=.85
            return Line(axes.c2p(x-span,y-m*span),axes.c2p(x+span,y+m*span),color=ACCENT,stroke_width=4)
        tangent=always_redraw(tanline); self.add(tangent,point)
        slope_panel=VGroup(MathTex(r"f'(x)=",color=ACCENT).scale(.72),DecimalNumber(float(df(t.get_value())),num_decimal_places=2,color=ACCENT).scale(.72)).arrange(RIGHT,buff=.08).to_corner(UR,buff=.62)
        slope_panel[1].add_updater(lambda m:m.set_value(float(df(t.get_value()))))
        if show_slope:self.play(FadeIn(slope_panel),run_time=.4*speed)
        for xc,kind in sorted(critical,key=lambda z:z[0]):
            self.play(t.animate.set_value(xc),run_time=1.6*speed,rate_func=smooth); self.wait(.25*speed)
            yc=float(f(xc)); halo=Circle(radius=.18,color=GOOD,stroke_width=3).move_to(axes.c2p(xc,yc)); label_text='Cực đại' if kind=='max' else 'Cực tiểu'
            lab=VGroup(Text(label_text,font="Arial",font_size=22,color=GOOD,weight="BOLD"),MathTex(r"f'(x)=0",color=WHITE_SOFT).scale(.66)).arrange(DOWN,buff=.1).next_to(axes.c2p(xc,yc),UP if kind=='max' else DOWN,buff=.28); clamp_to_frame(lab)
            self.play(Create(halo),FadeIn(lab),run_time=.5*speed); self.wait(.55*speed); self.play(FadeOut(lab),FadeOut(halo),run_time=.3*speed)
        self.play(t.animate.set_value(xhi-.15*(xhi-xlo)),run_time=1.3*speed,rate_func=smooth); slope_panel[1].clear_updaters(); self.wait(.3*speed)
        if show_chart and key=='x^3-3x':
            chart=VGroup(Text("Dấu của f'",font="Arial",font_size=22,color=WHITE_SOFT,weight="BOLD"),VGroup(MathTex(r"x<-1:\;f'(x)>0",color=GOOD).scale(.66),MathTex(r"-1<x<1:\;f'(x)<0",color=DANGER).scale(.66),MathTex(r"x>1:\;f'(x)>0",color=GOOD).scale(.66)).arrange(DOWN,aligned_edge=LEFT,buff=.14)).arrange(DOWN,aligned_edge=LEFT,buff=.18)
            card=formula_card(chart).to_edge(RIGHT,buff=.45).shift(DOWN*.45); self.play(FadeIn(card),run_time=.5*speed); self.wait(.75*speed)
        elif show_chart:
            chart=VGroup(Text('Quy tắc quan sát',font="Arial",font_size=22,color=WHITE_SOFT,weight="BOLD"),VGroup(MathTex(r"f'>0\Rightarrow f",color=GOOD).scale(.66),Text('tăng',font="Arial",font_size=20,color=GOOD)).arrange(RIGHT,buff=.12),VGroup(MathTex(r"f'<0\Rightarrow f",color=DANGER).scale(.66),Text('giảm',font="Arial",font_size=20,color=DANGER)).arrange(RIGHT,buff=.12)).arrange(DOWN,aligned_edge=LEFT,buff=.16)
            card=formula_card(chart).to_edge(RIGHT,buff=.45).shift(DOWN*.45); self.play(FadeIn(card),run_time=.5*speed)
        conclusion=info_card('Kết luận',["Cực trị thường xuất hiện tại f'(x)=0","Quan trọng hơn: xét sự đổi dấu của f'"],4.6).to_edge(RIGHT,buff=.45).shift(UP*1.6)
        self.play(FadeIn(conclusion),run_time=.5*speed); self.wait(1.4*speed)
