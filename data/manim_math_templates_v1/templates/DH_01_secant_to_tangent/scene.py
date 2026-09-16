from pathlib import Path
import sys
import numpy as np
from manim import *
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from common.config import load_params, number, boolean, choice
from common.theme import *
from common.math_utils import FUNCTIONS

class SecantToTangentTemplate(MovingCameraScene):
    def construct(self):
        apply_theme(self); p=load_params(); key=choice(p,'function','x^2',FUNCTIONS.keys()); spec=FUNCTIONS[key]; f,df,flatex=spec['fn'],spec['df'],spec['latex']
        a=number(p,'a',1,-3,3); h0=number(p,'h_start',2,.6,3); hend=number(p,'h_end',.12,.05,.3); speed=number(p,'duration_scale',1,.6,2); zoom=boolean(p,'camera_zoom',True)
        self.play(FadeIn(title('Ý nghĩa hình học của đạo hàm')),run_time=.5*speed)
        xlo,xhi=a-3.2,a+3.2; ys=[float(f(x)) for x in np.linspace(xlo,xhi,60)]; ymin,ymax=min(ys),max(ys); pad=max(1,.15*(ymax-ymin+1e-6)); ymin-=pad; ymax+=pad
        if ymax-ymin>12: mid=float(f(a)); ymin,ymax=mid-6,mid+6
        axes=Axes(x_range=[xlo,xhi,1],y_range=[ymin,ymax,max(1,(ymax-ymin)/6)],x_length=8.1,y_length=5.1,tips=False,axis_config={'color':GREY_B,'stroke_width':1.6}).shift(LEFT*2.3+DOWN*.25)
        graph=axes.plot(lambda x:float(f(x)),x_range=[xlo,xhi],color=PRIMARY,stroke_width=4); gl=MathTex(rf'f(x)={flatex}',color=PRIMARY).scale(.72).next_to(axes,UP,buff=.12)
        self.play(Create(axes),Create(graph),FadeIn(gl),run_time=1*speed)
        fa=float(f(a)); P=Dot(axes.c2p(a,fa),color=GOOD,radius=.085); Pl=MathTex(r'P=(a,f(a))',color=GOOD).scale(.68).next_to(P,UL,buff=.13)
        self.play(FadeIn(P),FadeIn(Pl),run_time=.5*speed)
        h=ValueTracker(h0)
        Q=always_redraw(lambda:Dot(axes.c2p(a+h.get_value(),float(f(a+h.get_value()))),color=DANGER,radius=.08))
        Ql=always_redraw(lambda:MathTex('Q',color=DANGER).scale(.66).next_to(Q,UR,buff=.09))
        def slope():
            hh=h.get_value(); return (float(f(a+hh))-fa)/hh
        def secant():
            m=slope(); x1,x2=xlo+.25,xhi-.25
            return Line(axes.c2p(x1,fa+m*(x1-a)),axes.c2p(x2,fa+m*(x2-a)),color=ACCENT,stroke_width=4)
        sec=always_redraw(secant); self.add(sec,Q,Ql)
        qt=MathTex(r'\frac{f(a+h)-f(a)}{h}',color=WHITE_SOFT).scale(.78)
        hr=VGroup(MathTex('h=',color=SECONDARY).scale(.7),DecimalNumber(h0,num_decimal_places=2,color=SECONDARY).scale(.7)).arrange(RIGHT,buff=.08)
        mr=VGroup(MathTex(r'm_{PQ}=',color=ACCENT).scale(.7),DecimalNumber(slope(),num_decimal_places=3,color=ACCENT).scale(.7)).arrange(RIGHT,buff=.08)
        hr[1].add_updater(lambda m:m.set_value(h.get_value())); mr[1].add_updater(lambda m:m.set_value(slope()))
        content=VGroup(Text('Cát tuyến PQ',font="Arial",font_size=22,color=ACCENT,weight="BOLD"),qt,hr,mr).arrange(DOWN,aligned_edge=LEFT,buff=.22)
        panel=formula_card(content).to_edge(RIGHT,buff=.55).shift(UP*.1); self.play(FadeIn(panel),run_time=.5*speed)
        self.play(h.animate.set_value(hend),run_time=4.4*speed,rate_func=smooth); hr[1].clear_updaters(); mr[1].clear_updaters(); self.wait(.3*speed)
        m=float(df(a)); tangent=Line(axes.c2p(xlo+.25,fa+m*((xlo+.25)-a)),axes.c2p(xhi-.25,fa+m*((xhi-.25)-a)),color=GOOD,stroke_width=5)
        if zoom:
            self.camera.frame.save_state(); self.play(self.camera.frame.animate.scale(.78).move_to(P.get_center()),run_time=.8*speed); self.play(FadeOut(sec),Create(tangent),run_time=.7*speed); self.wait(.3*speed); self.play(Restore(self.camera.frame),run_time=.7*speed)
        else:self.play(FadeOut(sec),Create(tangent),run_time=.7*speed)
        self.play(FadeOut(Q),FadeOut(Ql),FadeOut(panel),run_time=.4*speed)
        formula=MathTex(r"f'(a)=\lim_{h\to0}\frac{f(a+h)-f(a)}{h}",color=WHITE_SOFT).scale(.86); final=formula_card(formula).to_edge(RIGHT,buff=.55).shift(DOWN*.15)
        lab=Text('Tiếp tuyến tại P',font="Arial",font_size=22,color=GOOD).next_to(final,UP,buff=.22)
        self.play(FadeIn(lab),FadeIn(final),run_time=.6*speed); self.wait(1.5*speed)
