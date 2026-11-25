"""Draw the stable design from village-local metres. Pass the FPSGAME root as argv[1]."""
from pathlib import Path
import ast
import json
import math
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, patheffects
from matplotlib.patches import Arc, Circle, Polygon, Rectangle

HERE = Path(__file__).resolve().parent
PROJECT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(PROJECT / "Tools/WorldGeneration/AbandonedVillage"))
from layout_geometry import plot_geometry, rotate

source = PROJECT / "SourceAssets/TemperateHillsVillage"
layout = json.loads((source / "layout.json").read_text(encoding="utf-8"))
kit = json.loads((source / "house-pieces.json").read_text(encoding="utf-8"))
drawing = HERE / "Plans"
drawing.mkdir(exist_ok=True)
font_manager.fontManager.addfont("C:/Windows/Fonts/msyh.ttc")
plt.rcParams.update({"font.family":"Microsoft YaHei", "axes.unicode_minus":False,
                     "svg.fonttype":"path", "lines.solid_capstyle":"round"})
paper, ink, muted = "#f5f1e7", "#243a35", "#52635c"
green, rust, cream, line, mill = "#226e61", "#b45f30", "#fffbec", "#9b9f8b", "#935467"
lot = [(28,32),(45,32),(45,16),(58,16),(58,44),(28,44)]
def txt(ax,x,y,s,size=10,c=ink,**kw):
    return ax.text(x,y,s,fontsize=size,color=c,**kw)
def box(ax,x,y,w,h,fc,ec=ink,lw=1,**kw):
    q=Rectangle((x,y),w,h,facecolor=fc,edgecolor=ec,linewidth=lw,**kw)
    ax.add_patch(q)
    return q
def poly(ax,pts,fc,ec=ink,lw=1,**kw):
    ax.add_patch(Polygon(pts,closed=True,facecolor=fc,edgecolor=ec,linewidth=lw,**kw))
def path(ax,pts,color,width=1,**kw):
    return ax.plot(*zip(*pts),color=color,lw=width,**kw)[0]
def span(ax,a,b,col=muted):
    ax.annotate("",xy=a,xytext=b,arrowprops={"arrowstyle":"<->","shrinkA":0,"shrinkB":0,"lw":.9,"color":col})
def arrow(ax,a,b,col):
    ax.annotate("",xy=b,xytext=a,arrowprops={"arrowstyle":"-|>","color":col,"lw":1.7,"mutation_scale":14})
def tag(ax,x,y,s,color=ink):
    txt(ax,x,y,s,8.8,c=color,ha="center",va="center",bbox={"facecolor":paper,"edgecolor":"none","pad":1.3})
def fig(title,sub):
    f=plt.figure(figsize=(14.3,9),facecolor=paper)
    f.text(.048,.925,title,fontsize=28,color=ink,weight="bold")
    f.text(.05,.881,sub,fontsize=11,color=muted)
    f.add_artist(plt.Line2D([.049,.951],[.855,.855],transform=f.transFigure,lw=1,color="#a9afa2"))
    return f
def canvas(f,pos,xl,yl):
    a=f.add_axes(pos,facecolor=paper)
    a.set(xlim=xl,ylim=yl,aspect="equal")
    a.axis("off")
    return a
def notes(f,items):
    a=f.add_axes([.735,.13,.235,.67])
    a.axis("off")
    for y,title,body,color in items:
        a.text(0,y,title,fontsize=14.5,color=color,weight="bold",va="top")
        a.text(0,y-.072,body,fontsize=10,color=ink,va="top",linespacing=1.72)
def foot(f,s):
    f.text(.05,.035,s,fontsize=8.5,color=muted)
def save(f,name):
    f.savefig(drawing/(name+".png"),dpi=158,facecolor=paper)
    plt.close(f)

def site_plan():
    f=fig("东门马厩 · 总平面","丘陵村庄    /    东门内侧 · 面包房东南    /    村庄局部坐标，以米计")
    a=canvas(f,[.032,.085,.684,.745],(8,69),(54,-2))
    for x in range(10,70,5):
        path(a,[(x,-1),(x,52)],"#e3e2d5",.45)
        if x%10==0: txt(a,x,-.6,str(x),7,c=muted,ha="center")
    for y in range(0,55,5):
        path(a,[(9,y),(68,y)],"#e3e2d5",.45)
        if y%10==0: txt(a,8.7,y,str(y),7,c=muted,ha="right",va="center")
    def width_m(m):
        return (a.get_position().width*f.get_figwidth()*72/(a.get_xlim()[1]-a.get_xlim()[0]))*m
    for road in layout["roads"]:
        pts=road["points"]
        path(a,pts,"#b5ac93",width_m(road["width"]+.22))
        path(a,pts,"#dbd0b5",width_m(road["width"]))
    for h in layout["houses"]:
        if h[0] not in {"05","06","09"}: continue
        sh=plot_geometry(h,kit[h[2]],layout)
        x,y=sh["center"]
        if h[0]=="05":
            a.add_patch(Circle((22.858,23.807),3.1,facecolor="#c4baa4",edgecolor="#787968",lw=1.2))
        else:
            hw,hd=sh["half"]
            offsets=[rotate(i,j,sh["angle"]) for i,j in [(-hw,-hd),(hw,-hd),(hw,hd),(-hw,hd)]]
            poly(a,[(x+i,y+j) for i,j in offsets],"#cbc2aa","#868674",1)
    tag(a,33,15,"06  面包房");tag(a,21.6,23.8,"05  磨坊");tag(a,11.8,39,"09  枪店")
    path(a,[(65,-2),(65,1)],"#777d72",width_m(1.55))
    path(a,[(65,9),(65,44),(59,50),(9,50)],"#777d72",width_m(1.55))
    for y in [-.2,10.25]: box(a,62.85,y-.8,3.2,1.6,"#a5a797","#737c70",.9)
    tag(a,63,5,"东门");tag(a,35,5.9,"穿村主街");tag(a,43,50,"南城墙")
    # The four paths are the actual installed mill traffic recipe, in the tower frame.
    tree=ast.parse((PROJECT/"SourceAssets/HillsVillageWindmill/Millyard/author_traffic_mask.py").read_text(encoding="utf-8"))
    for call in [n for n in tree.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call)
                 and isinstance(n.value.func,ast.Name) and n.value.func.id=="tread"]:
        points=ast.literal_eval(call.value.args[0])
        for (x1,y1,w1),(x2,y2,w2) in zip(points,points[1:]):
            q1=rotate(x1/100,y1/100,6);q2=rotate(x2/100,y2/100,6)
            path(a,[(22.8576+q1[0],23.8067+q1[1]),(22.8576+q2[0],23.8067+q2[1])],mill,
                 max(.7,width_m((w1+w2)/100)),alpha=.59)
    tag(a,20.2,36.9,"磨坊卸粮道",mill)
    poly(a,lot,"#e6e6c7","#81926e",1.8)
    # Clearances are represented as bands with a directional centre line overlaid.
    cart=[(59,5),(56.9,5.3),(55,6.3),(53.7,8.1),(52.7,10.7),(52.5,13.1),(52.5,16),
          (52.5,19),(52.6,25),(52.8,30.7),(52.8,34.9)]
    horse=[(51.4,5.05),(49.3,6.3),(47.7,8.2),(46.5,10.8),(46.25,13.5),(46.25,16),
           (46.25,30.7),(45,32.65),(43,33.6),(35.2,33.6)]
    for pts,c,w in [(cart,"#e3bc91",4),(horse,"#a9c7af",2.2)]:
        path(a,pts,c,width_m(w))
    a.add_patch(Circle((52.65,24.4),4.5,facecolor="#efd0a7",edgecolor=rust,lw=1.2,ls="--"))
    for pts,c in [(cart,rust),(horse,green)]:
        path(a,pts,c,1.8)
        arrow(a,pts[4],pts[5],c)
    arrow(a,horse[-2],horse[-1],green);arrow(a,(52.8,31.8),(52.8,34.7),rust)
    tag(a,52.6,24.3,"Ø 9 m",rust)
    box(a,33,35.5,22,8,"#c79d6d",ink,1.3)
    for j in range(5):
        x=33+4.4*j
        if j: path(a,[(x,35.5),(x,43.5)],"#85694c",.85)
        txt(a,x+2.2,39.4,["马栏","马栏","马栏","马栏","草料"][j],7.4,ha="center",va="center")
    for j in range(4):
        x=33+4.4*j+2.2
        path(a,[(x-.75,35.5),(x+.75,35.5)],cream,2.5)
    path(a,[(50.9,35.5),(54.8,35.5)],cream,2.5)
    box(a,29.25,35.35,.78,2.05,"#8c9f9a",ink,.75)
    for y in (39.1,42.25):box(a,29.1,y,2.6,.30,"#997b54",ink,.75)
    tag(a,30,45.7,"饮水 / 拴马");tag(a,44.5,46,"马房 22 × 8 m")
    for x1,x2 in [(45,45.12),(47.38,50.2),(54.8,58)]:
        path(a,[(x1,16),(x2,16)],"#475a47",1.9)
    for x in [50.2,54.8]:
        path(a,[(x,16),(x,18.25)],"#77583f",1.7)
    tag(a,40,23.5,"东侧院径");tag(a,28.2,30.25,"磨坊后径",muted)
    path(a,[(59,41.5),(62,41.5)],muted,.7);txt(a,60.5,43.4,"东墙侧",7,c=muted,ha="center")
    arrow(a,(12,9),(12,4.2),ink);txt(a,12,3.1,"北",9,ha="center")
    path(a,[(12,47),(17,47)],ink,2);txt(a,14.5,46.3,"5 m",8,ha="center")
    notes(f,[(1,"L 形用地 · 568 m²","南翼 30 × 12 m，前院 13 × 16 m。\n马房占 176 m²，建筑南侧至墙线\n约 6.5 m，留作巡墙和维护。",ink),
             (.74,"草料车进出","东门连接路引出 4 m 支路。\n院门净宽 4.6 m，院内预留直径\n9 m 回转区，东端开间卸草料。",rust),
             (.48,"牵马进出","车门西侧另设 2.2 m 牵马口，\n沿前院西边到四个马栏。饮水槽\n和拴马横木集中在马房西端。",green),
             (.22,"磨坊作业面","紫色为磨坊地面配方中的车辙\n和作业带。马厩两条新路都从\n东门进，不借磨坊院径。",mill)])
    foot(f,"底图取自村庄 layout.json、磨坊院地磨耗配方和已保存的风车方位。门楼符号示意；回转圈为设计预留。")
    save(f,"01-东门马厩总平面")

def building():
    f=fig("南墙马房 · 平面与立面","五开间木构    /    四栏一库    /    马房外轮廓 22.0 × 8.0 m")
    a=canvas(f,[.049,.43,.65,.40],(-2,25.3),(11.8,-2.05))
    box(a,0,0,22,8,"#eadfc6",ink,1.7)
    box(a,.18,5.38,21.64,2.43,"#dbe7d7","none")
    for i in range(5):
        x=4.4*i
        if i: path(a,[(x,.22),(x,5.17)],ink,1.9)
        if i<4:
            box(a,x+.12,.2,4.16,4.95,"#e3cb9f","none")
            path(a,[(x+.18,5.19),(x+1.34,5.19)],ink,1.2)
            path(a,[(x+2.84,5.19),(x+4.22,5.19)],ink,1.2)
            path(a,[(x+1.45,0),(x+2.95,0)],paper,3.3)
            path(a,[(x+1.45,0),(x+1.45,1.46)],"#926746",1.1)
            a.add_patch(Arc((x+1.45,0),2.92,2.92,theta1=0,theta2=90,color="#a88b69",lw=.65,ls="--"))
            txt(a,x+2.2,2.9,"马栏 "+str(i+1),10,ha="center")
        else:
            box(a,x+.12,.2,4.16,4.95,"#efcca3","none")
            path(a,[(x+.34,0),(x+4.06,0)],paper,3.3)
            txt(a,x+2.2,3.0,"卸草料",10,ha="center")
    tag(a,11,6.62,"后勤通廊   2.4 m 净宽",green)
    for i in range(6):
        x=max(.1,min(21.9,4.4*i))
        for y in [.15,7.85]:box(a,x-.10,y-.10,.20,.20,ink,ink,.5)
    span(a,(0,9.05),(22,9.05));tag(a,11,9.05,"22.0 m")
    span(a,(23.1,0),(23.1,8));tag(a,23.05,4.0,"8.0 m")
    txt(a,0,-.9,"北面 · 马栏朝院",9,c=green)
    txt(a,22,-.9,"东端 · 卸料",9,c=rust,ha="right")
    b=canvas(f,[.052,.13,.642,.238],(-1,31),(-.65,6.6))
    # From the north looking south, the east feed bay appears on the left.
    box(b,0,0,22,3,"#e6d7b7",ink)
    box(b,0,2.95,22,2.35,"#717971",ink)
    for y in [3.25,3.6,3.95,4.3,4.65,5.0]:
        path(b,[(0,y),(22,y)],"#a2a798",.55)
    for i in range(5):
        x=i*4.4
        if i==0:box(b,x+.28,0,3.84,2.77,"#756651",ink,.8)
        else:
            box(b,x+1.45,0,1.50,2.38,"#786a54",ink,.65)
            box(b,x+1.47,.035,1.46,1.25,"#a18059",ink,.75)
        box(b,x+.02,0,.19,3.05,"#795f42",ink,.6)
    box(b,21.8,0,.2,3.05,"#795f42",ink,.6)
    poly(b,[(23.4,3),(27.4,5.3),(31.4,3)],"#aa916c",ink)
    box(b,23.4,0,8,3,"#e4d5b7",ink)
    path(b,[(23.4,3),(31.4,3)],ink,1.5);path(b,[(27.4,3),(27.4,5.25)],ink,1.3)
    txt(b,0,5.82,"北立面   ·   面向马房，东在左",8.8,c=muted)
    txt(b,24.0,5.82,"山墙   ·   跨度 8 m",8.8,c=muted)
    notes(f,[(1,"马栏与后勤","沿南墙东西向排布，开间轴距\n4.4 m。四间马栏朝院开门，\n东端一间直接接收草料。",ink),
              (.72,"门洞与结构","栏门洞口净宽 1.50 m、高 2.38 m。\n马栏半门顶高约 1.28 m；屋檐高\n3.0 m，屋脊高 5.3 m。",ink),
              (.44,"地坪与材料","室内外交界平接，前院夯土，\n栏内铺垫草。做旧橡木、浅色灰泥\n毛石基脚与深灰板岩统一全院。",ink),
              (.16,"设施位置","活动门五金朝人行侧收平。\n饮水、拴马在西端，东端留给卸料。",green)])
    foot(f,"图纸标注为本轮设计尺寸。单扇半门按 1.46 × 1.25 m 设计；院门和栏间隔断见组件三视图。")
    save(f,"02-马房平立面")
site_plan()
building()
