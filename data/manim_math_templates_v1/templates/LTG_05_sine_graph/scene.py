from pathlib import Path
import sys, math
import numpy as np
from manim import *
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from common.config import load_params, integer, number, boolean
from common.theme import *

class SineFromCircleTemplate(MovingCameraScene):
    def construct(self):
        apply_theme(self); p=load_params(); cycles=integer(p,'cycles',1,1,2); speed=number(p,'duration_scale',1,.6,2)
        show_connector=boolean(p,'show_connector',True); show_marks=boolean(p,'show_phase_markers',True)
        self.play(FadeIn(title('Từ đường tròn lượng giác đến đồ thị sin')),run_time=.55*speed)
        center=LEFT*4.0+DOWN*.15; R=1.75
        circle=Circle(radius=R,color=PRIMARY,stroke_width=4).move_to(center)
        xaxis=Line(center+LEFT*2.15,center+RIGHT*2.15,color=GREY_B,stroke_width=1.8)
        yaxis=Line(center+DOWN*2.15,center+UP*2.15,color=GREY_B,stroke_width=1.8)
        xmax=cycles*2*math.pi
        axes=Axes(x_range=[0,xmax,math.pi/2],y_range=[-1.25,1.25,.5],x_length=6.7,y_length=3.6,tips=False,axis_config={'color':GREY_B,'stroke_width':1.8}).move_to(RIGHT*2.75+DOWN*.15)
        cap=MathTex(r'y=\sin\alpha',color=SECONDARY).scale(.82).next_to(axes,UP,buff=.18)
        self.play(Create(circle),Create(xaxis),Create(yaxis),Create(axes),FadeIn(cap),run_time=1*speed)
        theta=ValueTracker(0.)
        M=always_redraw(lambda:Dot(center+R*np.array([math.cos(theta.get_value()),math.sin(theta.get_value()),0]),color=GOOD,radius=.08))
        radius=always_redraw(lambda:Line(center,M.get_center(),color=ACCENT,stroke_width=3.5))
        Mlab=always_redraw(lambda:MathTex('M',color=GOOD).scale(.68).next_to(M,UR,buff=.08))
        P=always_redraw(lambda:Dot(axes.c2p(theta.get_value(),math.sin(theta.get_value())),color=DANGER,radius=.072))
        Plab=always_redraw(lambda:MathTex('P',color=DANGER).scale(.65).next_to(P,UR,buff=.08))
        trace=TracedPath(P.get_center,stroke_color=SECONDARY,stroke_width=4)
        connector=always_redraw(lambda:DashedLine(M.get_center(),P.get_center(),color=GREY_C,dash_length=.08,stroke_width=1.4,stroke_opacity=.55))
        self.add(trace,radius,M,Mlab,P,Plab)
        if show_connector: self.add(connector)
        idea=info_card('Ý tưởng',['Góc α tăng khi M quay','Tung độ của M tạo thành sin α'],width=4.5).to_edge(DOWN,buff=.32).shift(LEFT*3.4)
        self.play(FadeIn(idea),run_time=.45*speed)
        self.play(theta.animate.set_value(xmax),run_time=5.2*cycles*speed,rate_func=linear); self.wait(.35*speed)
        if show_marks:
            marks=VGroup()
            for x,tex in [(0,'0'),(math.pi/2,r'\frac{\pi}{2}'),(math.pi,r'\pi'),(3*math.pi/2,r'\frac{3\pi}{2}'),(2*math.pi,r'2\pi')]:
                if x<=xmax+1e-8: marks.add(MathTex(tex,color=MUTED).scale(.55).next_to(axes.c2p(x,0),DOWN,buff=.12))
            self.play(LaggedStart(*[FadeIn(m) for m in marks],lag_ratio=.08),run_time=.7*speed)
        self.play(FadeOut(idea),run_time=.3*speed)
        final=formula_card(VGroup(MathTex(r'\boxed{y=\sin\alpha}',color=WHITE_SOFT).scale(.78),Text('tung độ của M',font='Arial',font_size=22,color=WHITE_SOFT)).arrange(RIGHT,buff=.15)).to_edge(DOWN,buff=.36)
        self.play(FadeIn(final,shift=UP*.1),run_time=.6*speed); self.wait(1.4*speed)
