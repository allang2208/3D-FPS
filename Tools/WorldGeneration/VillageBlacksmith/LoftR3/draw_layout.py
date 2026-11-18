"""Author the two-floor layout sheet from the model's centimetre coordinates (not a game capture)."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from design import *
ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/LoftR3'
im=Image.new('RGB',(1760,1080),'#eeeae1');d=ImageDraw.Draw(im)
def font(n,bold=False):return ImageFont.truetype('C:/Windows/Fonts/msyh'+('bd' if bold else '')+'.ttc',n)
def text(p,s,n=23,color='#26372f',anchor='mm',bold=False):d.text(p,s,font=font(n,bold),fill=color,anchor=anchor)
text((70,65),'村口铁匠铺 · 修复后布局',36,anchor='lm',bold=True)
text((70,114),'占地 +25%  /  原窗墙复用  /  半开放锻造区  /  二楼居住',23,anchor='lm',color='#647066')
scale=.66;cy=555
for floor,cx in ((0,440),(1,1320)):
    def p(x,y):return (cx+x*scale,cy-y*scale)
    def box(x,y,w,h,fill,outline=None,width=1):
        a=p(x-w/2,y+h/2);b=p(x+w/2,y-h/2);d.rectangle([a,b],fill=fill,outline=outline,width=width)
    def line(a,b,color,width):d.line([p(*a),p(*b)],fill=color,width=width)
    def label(x,y,s,n=19,col='#26372f'):text(p(x,y),s,n,col)
    text((cx,190),'一楼 · 半开放工坊' if not floor else '二楼 · 铁匠居所',28,bold=True)
    box(0,0,805,805,'#d8c6a7','#b8a684',2)
    for xx in range(-390,391,30):line((xx,-390),(xx,390),'#c5b492',1)
    wall='#68716a';window='#98b5b2'
    line((-389,389),(389,389),wall,22);line((389,-389),(389,389),wall,22)
    line((-389,0 if not floor else -389),(-389,389),wall,22)
    if floor:
        line((-389,-389),(389,-389),wall,22)
        for xx in (-199,203):line((xx-61,-389),(xx+61,-389),window,14)
        line((389,140),(389,262),window,14)
        box((OPENING[0]+OPENING[1])/2,(OPENING[2]+OPENING[3])/2,OPENING[1]-OPENING[0],OPENING[3]-OPENING[2],'#ede8de','#7e785f',3)
        box(BED[0],BED[1],145,220,'#9e917b','#665b49',3)
        box(BED[0],BED[1]+72,121,50,'#e3dcca')
        label(BED[0],BED[1]-30,'床铺')
        box(0,250,145,70,'#b49b74','#6f634d',2);label(0,250,'书桌',17)
        box(240,-300,70,55,'#a38b69');label(240,-300,'储物',16)
        label(105,-145,'二楼活动区')
        label(-220,338,'楼梯洞口 / 护栏',17)
        label(-157,-145,'上楼出口',17)
    else:
        for xx in (-365,0,365):box(xx,-389,34,34,wall)
        box(STATION[0],STATION[1],240,180,'#a2a494','#777c70',2)
        box(STATION[0],STATION[1],180,120,'#5e6965');label(STATION[0],STATION[1],'铁砧 / 淬火台',17,'#f8f2df')
        box(HEARTH[0],HEARTH[1],154,112,'#73766b');label(*HEARTH[:2],'炉膛',18,'#fff9eb')
        box(200,390,50,144,'#4d5650')
        box(CHIMNEY[0],CHIMNEY[1],136,130,'#898f82','#535f54',2)
        box(CHIMNEY[0],CHIMNEY[1],44,44,'#343e36');label(50,482,'外置烟囱',18)
        box(315,180,62,164,'#9d8a6a');label(315,180,'料\n架',17)
        box(-15,-270,145,70,'#b49b74','#6f634d',2);label(-15,-270,'接待桌',17)
        box(300,-300,62,62,'#a38b69');box(300,-210,49,49,'#827c68')
        box(0,-427,720,72,'#b7b6a3','#8d9382',1)
        label(0,-480,'前侧入口与柱廊',20)
        label(-460,-190,'侧\n面\n敞\n开',19)
        label(35,182,'操作通道',17)
    # Same 20 tread coordinates as the source mesh; the upper drawing shows the open well.
    for flight in range(2):
        x=STAIR['first_x'] if flight==0 else STAIR['second_x'];direction=1 if flight==0 else -1
        start=STAIR['start_y'] if flight==0 else STAIR['turn_y']
        for j in range(10):box(x,start+direction*(j+.5)*28,110,27,'#bd9d6b','#816e50',1)
        line((x,start+direction*30),(x,start+direction*240),'#435e52',3)
        yy=start+direction*240;line((x-10,yy-direction*15),(x,yy),'#435e52',3);line((x+10,yy-direction*15),(x,yy),'#435e52',3)
    box(-221,240,238,120,'#bda379','#7d6d53',2);label(-221,240,'折返平台',18)
    label(-286,-135,'上',17)
    text((cx,920),'805 cm',23,color='#66705e')
    d.line([(cx-265,888),(cx+265,888)],fill='#8c9486',width=2)
    for x in (cx-265,cx+265):d.line([(x,882),(x,894)],fill='#8c9486',width=2)
d.line([(880,165),(880,945)],fill='#cecfc4',width=2)
text((70,1008),'层高 360 cm    楼梯宽 110 cm    步高 / 踏面 18 / 28 cm    默认残破，任务修复后启用',23,anchor='lm')
text((70,1050),'制作布局图：对应模型坐标；不是引擎截图，未进行游戏测试。',18,anchor='lm',color='#7b8176')
im.save(OUT/'layout-r3.png')
print('LOFT_R3_LAYOUT_SHEET_AUTHORED')
