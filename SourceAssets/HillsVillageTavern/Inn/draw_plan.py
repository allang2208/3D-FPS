"""Measured site and floor plans, framed at the hall's surveyed doorway."""
from pathlib import Path
import json,sys,math
from PIL import Image,ImageDraw,ImageFont
from inn_geometry import WEST,EAST,FRONT,BACK,GUEST,OWNER,EAVES,ROOT
from hall_plan import sockets,GUEST_ROWS,WEST_ROOM
from suite_geometry import SUITE_X,SUITE_Y,SUITE_DOOR
DOORS=sockets(GUEST,OWNER)[:-1]+[(SUITE_Y,SUITE_DOOR,OWNER,90)]
sys.path.insert(0,str(ROOT/'Tools/WorldGeneration/AbandonedVillage'))
from layout_geometry import plot_geometry,rotate

ink='#302f29'; accent='#765338'; paper='#f4f1e9'; rule='#d7cebd';wood='#88694a';stone='#79796d';room='#e0d0b4';green='#899c75'
im=Image.new('RGB',(1480,1350),paper);d=ImageDraw.Draw(im)
def font(size):return ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',size)
def label(x,y,s,size=19,fill=ink):d.text((x,y),s,font=font(size),fill=fill,anchor='mm')
def title(x,y,s):d.text((x,y),s,font=font(27),fill=ink,anchor='lm')
title(40,42,'西侧酒馆 · 扩建平面');d.text((1440,42),'主街在图上方  /  尺寸以米计',font=font(17),anchor='rm',fill=accent)
p=json.loads((ROOT/'SourceAssets/TemperateHillsVillage/layout.json').read_text(encoding='utf8'))
kit=json.loads((ROOT/'SourceAssets/TemperateHillsVillage/house-pieces.json').read_text(encoding='utf8'))
house=next(h for h in p['houses'] if h[0]=='02')
shape=plot_geometry(house,kit[house[2]],p)
def local(pos):
    q=shape['shell_center'];x,y=rotate(pos[0]-q[0],pos[1]-q[1],-house[5]+90)
    return (100*x,100*y)
def panel(x,y,name,site=False):
    d.rounded_rectangle((x,y,x+676,y+458),12,fill='#fbfaf5',outline=rule,width=2)
    title(x+20,y+27,name)
    scale=.080 if site else .267
    ox,oy=x+338,y+(329 if site else 194)
    def xy(a,b):return (ox+a*scale,oy+b*scale)
    def rect(x0,x1,y0,y1,fill,outline=None,w=1):d.rectangle((*xy(x0,y0),*xy(x1,y1)),fill=fill,outline=outline,width=w)
    def line(pts,color,w):d.line([xy(*v) for v in pts],fill=color,width=w)
    def word(xx,yy,s,sz=17):label(*xy(xx,yy),s,sz)
    return xy,rect,line,word
xy,rect,line,word=panel(40,80,'场地与来路',True)
def lineclip(pts,color,w):
    # Clip road and lot geometry to the site drawing.
    import PIL.ImageDraw as ID
    tile=Image.new('RGBA',(652,368));tt=ID.Draw(tile)
    tt.line([(x-52,y-130) for x,y in [xy(*a) for a in pts]],fill=color,width=w,joint='curve')
    im.paste(tile,(52,130),tile)
for road in (p['roads'][0],p['roads'][3]):
    lineclip([local(a) for a in road['points']], '#d7c4a2',max(5,round(road['width']*17.5)))
stations=p['tavern']['inn']['hall_road']['stations']
for a,b in zip(stations,stations[1:]):
    lineclip([local(a),local(b)],'#bca37f',max(4,round((a[2]+b[2])*8)))
for yard in p['yard_walls']:
    for piece in yard['pieces']:
        lineclip([local(piece[1:3]),local(piece[3:5])],stone,3)
rect(WEST,EAST,FRONT,BACK,room,wood,3)
rect(WEST-600,EAST-600,FRONT-2000,423-2000,None,'#a99d88')
word(0,165,'新酒馆');word(-650,-1980,'原址',13)
rect(-675,-10,-846,-818,wood)
for c in (-557,-350,-143):rect(c-65,c+65,-1090,-860,'#d6bb88')
word(-343,-1195,'三马位',13)
word(435,-855,'门前通道',13)
word(-2000,-1510,'木工坊',14)
lineclip([local(point[:2]) for point in p['tavern_forecourt']['trail']], '#b39b7b', 6)
label(377,517,'主街直达正门，西侧泥径通向院巷与马位。',16)
for col,row,level,name,note in [(762,80,1,'一层 · 厅堂与后厨','四组餐桌在前厅；经后柜台及传菜窗供应热食。'),
                           (40,558,2,'二层 · 四间客房','四扇房门朝房内开；中廊经西侧回廊通向后平台。'),
                           (762,558,3,'三层 · 店主起居','楼梯进入起居厅；后侧带门卧室内设衣柜、壁镜和梳洗桌。')]:
    xy,rect,line,word=panel(col,row,name)
    rect(WEST,EAST,FRONT,BACK,'#eee7d8',wood,5)
    if level==1:
        rect(321,EAST-16,-65,338,'#d6ccb9',wood,2)
        rect(93,EAST-16,338,BACK-16,'#d6ccb9',wood,2)
        word(478,115,'灶台',14);word(390,621,'备餐 · 洗涤',14)
        rect(145,309,289,366,'#a3764b',wood,2)
        rect(-238,58,428,488,'#b69372');word(-90,453,'柜台',13)
        for xx,yy in [(-302,-202),(-300,131),(367,-251),(124,102)]:
            rect(xx-59,xx+59,yy-35,yy+35,'#c3a481')
        word(24,-115,'厅堂')
    if level==2:
        for i,(y,yaw,split,xs) in enumerate(GUEST_ROWS):
            lo,hi=(FRONT+10,y) if i==0 else (y,BACK-13)
            for j,(a,bnd) in enumerate([(WEST_ROOM,split),(split,EAST-10)]):
                rect(a,bnd,lo,hi,room,wood,2);word((a+bnd)/2,(lo+hi)/2,'客房 '+str(1+j+i*2))
        word(128,200,'中央过道',15)
    if level==3:
        rect(SUITE_X,EAST-16,SUITE_Y,BACK-15,room,wood,2);word(406,404,'卧室')
        word(-174,-325,'书桌',14);word(281,-63,'餐桌与靠背长椅',13);word(225,574,'梳洗台与镜',12)
        rect(422,558,546,758,'#ac9478',wood,1);word(490,650,'床',13);word(-93,151,'起居厅',17)
        word(-300,755,'储物柜',13);word(150,691,'衣柜',12)
    rect(-697,-537,-40,551,'#dccab0',wood,2)
    for i in range(21):line([(-697,-40+i*29),(-537,-40+i*29)],'#987851',1)
    line([(-617,8),(-617,510)],accent,3)
    a,b=xy(-617,525);d.polygon([(a,b),(a-5,b-9),(a+5,b-9)],fill=accent)
    if level==1:word(-100,732,'酒架与酒桶',14)
    if level>1:word(-430,670,'平台',14)
    for y,x,z,yaw in DOORS:
        if (level,z) in ((2,GUEST),(3,OWNER)):line([(x-50,y),(x+50,y)],'#faf8ed',5)
    if level==1:line([(-62,FRONT),(62,FRONT)],'#faf8ed',5)
    label(col+338,row+437,note,16)
d.rounded_rectangle((40,1035,1438,1324),12,fill='#fbfaf5',outline=rule,width=2)
title(61,1070,'临街立面')
ox,oy,k=521,1301,.156
def elev(x,z):return (ox+x*k,oy-z*k)
def face(a,b,lo,hi,color):d.rectangle((*elev(a,hi),*elev(b,lo)),fill=color)
face(WEST,EAST,0,334,'#9e9686')
for z in range(20,320,24):
    d.line([elev(WEST,z),elev(EAST,z)],fill='#8d887a')
    for x in range(WEST+((z//24)%2)*35,EAST,70):d.line([elev(x,z),elev(x,z+24)],fill='#8d887a')
face(-62,62,0,210,'#443a2e')
for x in (-480,442):face(x-50,x+50,107,224,'#524c3e')
for low,hi,windows in [(GUEST,OWNER,[-520,-138,320,525]),(OWNER,EAVES,[-512,-175,214,494])]:
    face(WEST,EAST,low,hi,'#9e9686')
    for z in range(low+17,hi-8,25):d.line([elev(WEST,z),elev(EAST,z)],fill='#8d887a')
    for z in (low+4,hi-6):face(WEST,EAST,z-6,z+6,wood)
    for x in windows:
        face(x-51,x+51,low+92,low+218,'#656052')
        for xx in (x-59,x+59):face(xx-4,xx+4,low,hi,wood)
    for x in (WEST,-330,64,EAST-6):face(x,x+7,low,hi,wood)
face(WEST-34,EAST+34,EAVES,EAVES+327,'#65615a')
for z in range(EAVES+14,EAVES+318,26):
    d.line([elev(WEST-34,z),elev(EAST+34,z)],fill='#77746d')
face(551,610,1225,1395,'#8b8273')
label(254,1211,'原石墙基座',16);label(766,1170,'石板双坡屋面',16)
label(1085,1149,'沿用原灶台位置，烟道穿过两层楼板。',18)
label(1085,1190,'二、三层内外墙直接沿用一楼餐厅原生石墙。',18)
label(1085,1231,'三处马位设在前院西侧，可从东侧直接步行入厅。',17)
im.save(Path(__file__).with_name('酒馆扩建平面.png'))
