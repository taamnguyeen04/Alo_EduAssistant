from pathlib import Path
import sys, math
import numpy as np
from manim import *
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from common.config import load_params, number, boolean
from common.theme import *

class UnitCircleTemplate(MovingCameraScene):
    def construct(self):
        apply_theme(self); p=load_params()
        alpha_deg=number(p,'angle_deg',60,-720,720); alpha=math.radians(alpha_deg)
        show_numeric=boolean(p,'show_numeric',True); show_radius=boolean(p,'show_radius_label',True)
        show_summary=boolean(p,'show_final_summary',True); speed=number(p,'duration_scale',1.0,0.6,2.0)
        ttl=title('Đường tròn lượng giác'); self.play(FadeIn(ttl),run_time=.55*speed)
        center=LEFT*3.1+DOWN*.15; R=2.05
        x_axis=Line(center+LEFT*2.7,center+RIGHT*2.7,color=GREY_B,stroke_width=2)
        y_axis=Line(center+DOWN*2.55,center+UP*2.55,color=GREY_B,stroke_width=2)
        circle=Circle(radius=R,color=PRIMARY,stroke_width=4).move_to(center)
        O=MathTex('O',color=WHITE_SOFT).scale(.72).next_to(center,DL,buff=.12)
        self.play(Create(x_axis),Create(y_axis),Create(circle),FadeIn(O),run_time=1.0*speed)
        if show_radius:
            rd=Line(center,center+RIGHT*R,color=ACCENT,stroke_width=4); rt=MathTex('R=1',color=ACCENT).scale(.78).next_to(rd,UP,buff=.12)
            self.play(Create(rd),FadeIn(rt),run_time=.7*speed); self.wait(.4*speed); self.play(FadeOut(rd),FadeOut(rt),run_time=.35*speed)
        theta=ValueTracker(0.0)
        radius=always_redraw(lambda:Line(center,center+R*np.array([math.cos(theta.get_value()),math.sin(theta.get_value()),0]),color=ACCENT,stroke_width=4))
        point=always_redraw(lambda:Dot(center+R*np.array([math.cos(theta.get_value()),math.sin(theta.get_value()),0]),color=GOOD,radius=.085))
        arc=always_redraw(lambda:Arc(radius=.55,start_angle=0,angle=theta.get_value(),arc_center=center,color=ACCENT,stroke_width=4))
        Mlab=always_redraw(lambda:MathTex('M',color=GOOD).scale(.78).next_to(point,UR if math.sin(theta.get_value())>=0 else DR,buff=.1))
        self.add(radius,arc,point,Mlab)
        angle=VGroup(MathTex(r'\alpha=',color=ACCENT).scale(.76),DecimalNumber(0,num_decimal_places=0,unit=r'^\circ',color=ACCENT).scale(.76)).arrange(RIGHT,buff=.07).to_corner(UR,buff=.62)
        angle[1].add_updater(lambda m:m.set_value(math.degrees(theta.get_value())))
        self.play(FadeIn(angle[0]),run_time=.4*speed); self.add(angle[1])
        self.play(theta.animate.set_value(alpha),run_time=2.2*speed,rate_func=smooth); angle[1].clear_updaters(); self.wait(.3*speed)
        cx,sy=math.cos(alpha),math.sin(alpha); M=center+R*np.array([cx,sy,0]); fx=center+R*np.array([cx,0,0]); fy=center+R*np.array([0,sy,0])
        px=DashedLine(M,fx,color=SECONDARY,dash_length=.08); py=DashedLine(M,fy,color=SECONDARY,dash_length=.08)
        coslab=MathTex(r'\cos\alpha',color=SECONDARY).scale(.7).next_to(Line(center,fx),DOWN if sy>=0 else UP,buff=.12)
        sinlab=MathTex(r'\sin\alpha',color=SECONDARY).scale(.7).next_to(Line(center,fy),LEFT,buff=.12)
        self.play(FadeOut(angle),Create(px),Create(py),run_time=.7*speed); self.play(FadeIn(coslab),FadeIn(sinlab),run_time=.5*speed)
        anchor=RIGHT*3.35+UP*.45
        generic=MathTex(r'M(x,y)',color=WHITE_SOFT).scale(.95).move_to(anchor)
        exact=MathTex(r'M(\cos\alpha,\sin\alpha)',color=GOOD).scale(.95).move_to(anchor)
        self.play(Write(generic),run_time=.5*speed); self.play(TransformMatchingTex(generic,exact),run_time=.8*speed)
        numeric_card=None
        if show_numeric:
            num=VGroup(MathTex(r'\cos\alpha=',color=SECONDARY).scale(.68),DecimalNumber(cx,num_decimal_places=3,color=SECONDARY).scale(.68),MathTex(r'\sin\alpha=',color=SECONDARY).scale(.68),DecimalNumber(sy,num_decimal_places=3,color=SECONDARY).scale(.68)).arrange_in_grid(rows=2,cols=2,buff=(.18,.18))
            numeric_card=formula_card(num).next_to(exact,DOWN,buff=.38); clamp_to_frame(numeric_card); self.play(FadeIn(numeric_card),run_time=.5*speed)
        self.wait(.8*speed); self.play(FadeOut(coslab),FadeOut(sinlab),FadeOut(px),FadeOut(py),run_time=.4*speed)
        if show_summary:
            summary=info_card('Kết luận',['cos α = hoành độ của M','sin α = tung độ của M'],width=4.5).to_edge(RIGHT,buff=.55).shift(DOWN*1.75)
            self.play(FadeIn(summary,shift=UP*.1),run_time=.5*speed); self.wait(1.2*speed)
