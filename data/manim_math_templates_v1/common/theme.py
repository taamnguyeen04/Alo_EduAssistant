from manim import *
BG='#0B1020'; PRIMARY=BLUE_B; SECONDARY=TEAL_B; ACCENT=YELLOW; GOOD=GREEN_B; DANGER=RED_B; MUTED=GREY_B; WHITE_SOFT='#F4F7FB'
TITLE_SIZE=34; BODY_SIZE=24; SMALL_SIZE=20

def apply_theme(scene): scene.camera.background_color = BG

def title(text): return Text(text, font="Arial", font_size=TITLE_SIZE, color=WHITE_SOFT, weight="BOLD").to_edge(UP, buff=0.42)
def formula_card(mob, buff=0.22):
    box=SurroundingRectangle(mob,buff=buff,corner_radius=0.12,stroke_color=GREY_C,stroke_width=1.4,fill_color=BLACK,fill_opacity=0.20)
    return VGroup(box,mob)
def info_card(title_text, lines, width=4.6):
    t=Text(title_text,font="Arial",font_size=22,color=ACCENT,weight="BOLD")
    l=VGroup(*[Text(x,font="Arial",font_size=20,color=WHITE_SOFT) for x in lines]).arrange(DOWN,aligned_edge=LEFT,buff=0.14)
    c=VGroup(t,l).arrange(DOWN,aligned_edge=LEFT,buff=0.18)
    b=SurroundingRectangle(c,buff=0.22,corner_radius=0.12,stroke_color=GREY_C,stroke_width=1.2,fill_color=BLACK,fill_opacity=0.18)
    g=VGroup(b,c)
    if g.width>width: g.scale_to_fit_width(width)
    return g

def clamp_to_frame(mob, margin=0.35):
    xlim=config.frame_width/2-margin; ylim=config.frame_height/2-margin; dx=dy=0
    if mob.get_right()[0]>xlim: dx-=mob.get_right()[0]-xlim
    if mob.get_left()[0]<-xlim: dx+=-xlim-mob.get_left()[0]
    if mob.get_top()[1]>ylim: dy-=mob.get_top()[1]-ylim
    if mob.get_bottom()[1]<-ylim: dy+=-ylim-mob.get_bottom()[1]
    mob.shift(RIGHT*dx+UP*dy); return mob
