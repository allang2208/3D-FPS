"""Dimensioned design sheet. Coordinates match the shell and east-gate settlement, in centimetres."""
from pathlib import Path
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont

root=Path(__file__).resolve().parent
im=Image.new("RGB",(1540,960),"#f2efe8")
d=ImageDraw.Draw(im)
ink="#253430";muted="#5b6861";edge="#ccc7b9";rust="#9d502e";wood="#ad8661";stone="#888b81";green="#526346"
@lru_cache()
def font(size,bold=False):
    return ImageFont.truetype("C:/Windows/Fonts/"+("msyhbd.ttc" if bold else "msyh.ttc"),size)
def label(x,y,t,size=19,c=ink,bold=False,anchor=None):
    d.text((x,y),t,font=font(size,bold),fill=c,anchor=anchor)
def line(a,b,fill=ink,w=2):
    d.line((a,b),fill=fill,width=w)
def box(a,b,fill,outline=None,width=1):
    d.rectangle((min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1])),fill=fill,outline=outline,width=width)
label(54,39,"守备机械  /  东门机械工坊",40,bold=True)
label(56,106,"村庄防御第四级     ·     修复城墙  →  升级高墙  →  防御工事  →  守备机械",20,muted)
line((56,164),(1484,164),edge)
label(58,189,"马厩对街与进场路线",25,bold=True)
label(792,189,"工坊平面",25,bold=True)
def site(x,y):
    return (79+x*.095,401+y*.095)
def plotbox(transform,x0,y0,x1,y1,fill,outline=None,width=1):
    box(transform(x0,y0),transform(x1,y1),fill,outline,width)
plotbox(site,0,-1670,6650,4520,"#e5e5d7")
# Only the local east street is shown. North is up in the village map.
plotbox(site,0,-1670,4200,340,"#d8dacd")
line(site(4200,-1670),site(4200,340),stone,5)
line(site(4200,340),site(2400,340),stone,5)
label(*site(1700,-750),"教堂院地",17,muted,False,"mm")
road=[(0,636),(400,750),(1500,800),(2800,800),(3900,820),(4200,620),(4500,500),(6500,500)]
d.line([site(*p) for p in road],fill="#bea686",width=40,joint="curve")
d.line([site(*p) for p in road],fill="#dec9a9",width=35,joint="curve")
label(*site(2800,800),"东门大路",15,ink,False,"mm")
for a,b in ((-1660,100),(900,4400)):line(site(6500,a),site(6500,b),stone,5)
label(*site(6395,490),"东门",15,ink,True,"mm")
# Same local coordinates as the streamed village, its stable and the workshop.
plotbox(site,4948,-1130,5552,40,wood,rust,3)
plotbox(site,5110,40,5390,290,"#c2a783",rust)
label(*site(4990,-1380),"机械工坊",18,rust,True,"mm")
plotbox(site,3270,3550,5550,4350,"#b3a58e",stone,3)
label(*site(4410,3960),"东门马厩",18,ink,True,"mm")
d.line([site(4500,1600),site(4500,3090),site(3350,3435),site(3250,3550)],fill=wood,width=3)
d.line([site(5500,1600),site(5780,1600),site(5780,3260)],fill=wood,width=3)
track=[(5900,500),(5690,530),(5500,630),(5370,810),(5270,1070),(5250,1310),(5250,1600),(5265,2440)]
d.line([site(*p) for p in track],fill="#cbb998",width=13,joint="curve")
d.line([site(5250,-10),site(5250,300)],fill=rust,width=3)
label(*site(4280,2360),"马厩前院",16,muted,False,"mm")
label(*site(850,-1410),"北 ↑",16,ink,True,"mm")
label(68,845,"从马厩车门向北过街，经石铺路肩直达工坊。",18,muted)
line((757,194),(757,838),edge)
def room(x,y):
    return (1000+.425*x,565-.425*y)
plotbox(room,-302,-585,302,585,"#dbc8ac",ink,7)
plotbox(room,-116,-570,116,570,"#d9d8ce")
for y in range(-515,570,65):
    line(room(-116,y),room(116,y),"#c1c2b6",1)
for x in (-1,1):
    for yy in (-385,0,385):
        d.line([room(x*300,yy-95),room(x*300,yy+95)],fill="#eff5f1",width=6)
        d.line([room(x*300,yy-95),room(x*300,yy+95)],fill="#89a1a2",width=2)
plotbox(room,-118,-593,118,-568,"#d9d8ce")
plotbox(room,-256,-37,-168,227,wood,ink,2)
plotbox(room,177,-188,256,-20,wood,ink,2)
plotbox(room,182,148,266,501,"#a78f75",ink,2)
plotbox(room,-251,244,-171,549,wood,ink,2)
plotbox(room,12,523,144,538,wood,ink,1)
plotbox(room,-262,-411,-185,-266,"#b49d83",ink,2)
plotbox(room,148,-504,258,-319,wood,ink,2)
plotbox(room,172,36,236,121,wood,ink,1)
rx,ry=room(-200,-173)
for r in (5,7,10):d.ellipse((rx-r,ry-r,rx+r,ry+r),outline=wood,width=2)
x0,y0=room(-105,95)
d.ellipse((x0-6,y0-6,x0+6,y0+6),fill=rust)
for y in (535,587,638,689,740):
    line((1000,y),(1000,y+20),rust,3)
d.polygon([(1000,520),(994,535),(1006,535)],fill=rust)
def callout(p,index,tx,ty,title,detail):
    x,y=room(*p);d.ellipse((x-9,y-9,x+9,y+9),fill=ink)
    label(x,y-1,str(index),12,"white",True,"mm")
    label(tx,ty,str(index)+"   "+title,20,ink,True)
    label(tx,ty+32,detail,15,muted)
callout((-201,101),1,1170,340,"升级装配桌","桌面与玩家站位已分开预留")
callout((223,-105),2,1170,426,"检修台","绞盘、铁件盘与常用工具")
callout((221,300),3,1170,512,"零件架","长料在上，铁料与木销分层")
callout((-211,405),4,1170,598,"后部装配位","支架、缆鼓与待修轮毂")
callout((-221,-340),5,1170,684,"收料与下料","短料、盘绳与收料轴架")
callout((204,76),6,1170,765,"地面零件盘","销轴与垫圈归入低木盘")
a,b=room(-302,641),room(302,641);line(a,b,muted)
for x,y in (a,b):line((x,y-5),(x,y+5),muted)
label(1000,267,"6.04 m",17,muted,False,"mm")
label(1000,845,"双扇装载门  ·  净宽约 2.1 m",16,muted,False,"mm")
line((56,887),(1484,887),edge)
label(58,905,"屋身  6.04 × 11.70 m      /      石材承重墙裙、橡木排架、板岩双坡屋顶",18,muted)
im.save(root/"Workshop-Plan.png")
