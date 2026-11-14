"""Draw the construction layout using one scale and the subject's UE centimetres."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import gzip, json, math
import numpy as np

ROOT=Path(__file__).resolve().parent
SRC=ROOT.parent
points=json.loads((ROOT/'design-points.json').read_text('utf8'))
W,H=2048,1330
img=Image.new('RGB',(W,H),'#eeece4')
d=ImageDraw.Draw(img)
def font(size,bold=False):
    return ImageFont.truetype('C:/Windows/Fonts/'+('msyhbd.ttc' if bold else 'msyh.ttc'),size)
def txt(x,y,s,size=18,color='#263631',bold=False):
    d.text((x,y),s,fill=color,font=font(size,bold))
def pos(x,y):
    return (round(67+(x-1800)*.193),round(177+(750-y)*.193))
def poly(world,fill,outline=None):
    d.polygon([pos(*p) for p in world],fill=fill,outline=outline)
def rect(x0,y0,x1,y1,fill,outline=None):
    poly([(x0,y0),(x0,y1),(x1,y1),(x1,y0)],fill,outline)
def line(points,color,width=2):
    d.line([pos(*p) for p in points],fill=color,width=width,joint='curve')
def dash(points,color,period=22,width=4):
    for a,b in zip(points,points[1:]):
        a,b=np.array(pos(*a)),np.array(pos(*b))
        v=b-a; length=np.linalg.norm(v)
        for t in range(0,int(length),period):
            d.line([tuple(a+v*t/length),tuple(a+v*min(t+period*.53,length)/length)],fill=color,width=width)
def footprint(folder,pattern,origin,fill):
    path=next(folder.glob(pattern))
    with gzip.open(path,'rt') as f:g=json.load(f)
    v=np.array(g['vertices']); tri=v[np.array(g['indices']).reshape(-1,3)]
    if 'Walls' in pattern: tri=tri[tri[:,:,2].max(axis=1)<120]
    normals=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
    for face in tri[np.abs(normals[:,2])>4.]:
        poly([(p[0]+origin[0],p[1]+origin[1]) for p in face],fill)
ink='#253b35'; rust='#9f4a31'; route='#14755e'; floor='#ddd9c9'; walls='#657169'; dock='#b7ac92'
d.rectangle((0,0,W,128),fill=ink)
txt(61,20,'货运仓库  /  废弃车站',43,'#fff9e7',True)
txt(66,83,'场景布置施工图     ·     原地图坐标平面投影     /     世界 +X 向右，+Y 向上',20,'#c4d5c9')
txt(1670,36,'环境美术     02 / 02',26,'#f3e8d7',True)
txt(1670,80,'2026.11.12     /     设计稿',18,'#c4d5c9')
for x in range(2000,11601,500):line([(x,650),(x,-3400)],'#dcded3',1)
for y in range(-3300,601,500):line([(1850,y),(11600,y)],'#dcded3',1)
old=SRC/'FreightWarehouseWeathering20261110/Geometry'
rack=SRC/'FreightWarehouseEntranceSample20261111/Geometry'
station=SRC/'FreightStationUnifiedPatina20261111/Geometry'
footprint(old,'SM_CargoWarehouse_Floors*',(3760,-900),floor)
footprint(old,'SM_CargoWarehouse_Dock_*.gz',(3760,-900),dock)
footprint(old,'SM_CargoWarehouse_StairTreads*',(3760,-900),'#bfbaa8')
footprint(old,'SM_CargoWarehouse_Walls*',(3760,-900),walls)
footprint(rack,'SM_CargoWarehouse_RackDecks*',(3760,-900),'#93846e')
data=json.loads((station.parent/'inputs.json').read_text('utf8'))
for a in data['actors']:
    x,y,z=a['center'];ex,ey,ez=a['extent']
    if ((a['label'].startswith('StationLine_AbandonedCargoWarehouse') or a['label'].startswith('WarehouseEntrance_')) and
        x-ex>=2240 and x+ex<=5280 and 15<ex<150 and 15<ey<150 and 12<ez<230 and z<400):
        rect(x-ex,y-ey,x+ex,y+ey,'#ba9973','#827762')
rect(5460,-1562,5860,-1238,floor,walls)
footprint(station,'SM_Station_Floors*',(7760,-1400),floor)
footprint(station,'SM_Station_Walls*',(7760,-1400),walls)
rect(7210,-1925,11560,-875,'#787e77','#656c64')
for cy in (-1135,-1665):
    for x in range(7750,11549,75):rect(x,cy-95,x+15,cy+95,'#68716b')
    for y in (cy-72,cy+72):line([(7740,y),(11545,y)],'#c5cabb',2)
for y in (-1963,-837):line([(7210,y),(10957,y)],'#b39542',3)
for cy in (-35,-2765):
    rect(9085,cy-255,9985,cy+255,'#c4c7b8',walls)
    for x in range(9085,9986,30):line([(x,cy-255),(x,cy+255)],'#92998e',1)
rect(9985,-3020,10525,220,'#bac1b4',walls)
for yy in range(-3000,220,68):line([(9986,yy),(10523,yy+68)],'#9fa99a',1)
rect(7310,-550,8310,150,'#c0b39b',walls)
line([(7575,-550),(8045,-550)],'#dbecea',4)
for x0,x1 in [(7370,7490),(8070,8290)]:line([(x0,-550),(x1,-550)],floor,3)
rect(8379,-341,8477,-279,'#996047',ink)
# Existing route incl. warehouse dogleg and station side access; secondary approach to cart and bridge.
main=[(1850,0),(3760,0),(3760,-1400),(6760,-1400),(6760,-2200),(8185,-2200),(8185,-3335)]
dash(main,route,19,4)
branch=[(6760,-1400),(6760,-740),(8600,-740),(8780,-570),(8780,-35),(10035,-35)]
dash(branch,'#6d8b77',13,3)
def label(x,y,s):
    a,b=pos(x,y);box=d.textbbox((a,b),s,font=font(17,True));d.rectangle((box[0]-5,box[1]-3,box[2]+5,box[3]+4),fill='#edeae0');txt(a,b,s,17,ink,True)
label(3400,-690,'货运仓库');label(3360,-2120,'装卸台');label(6600,-2750,'站厅');label(7360,-55,'调度维修间')
label(9060,-1430,'双线轨坑');label(10120,-930,'天桥');label(5270,-975,'连接通道')
for row,offset in zip(points,[(-50,-42),(37,44),(5,52),(-46,23),(51,-31),(62,41)]):
    number,name,xy,*_=row;x,y=pos(*xy);cx,cy=x+offset[0],y+offset[1]
    d.line([(x,y),(cx,cy)],fill=rust,width=3)
    d.ellipse((x-4,y-4,x+4,y+4),fill=rust)
    d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=rust,outline='#f8eddd',width=2)
    d.text((cx,cy-1),number,font=font(16,True),fill='white',anchor='mm')
txt(98,913,'5 m',19,ink,True)
p,q=pos(1950,-2980),pos(2450,-2980)
d.line([p,q],fill=ink,width=4)
for x,y in [p,q]:d.line([(x,y-5),(x,y+5)],fill=ink,width=2)
txt(218,913,'深绿虚线  原主通道      浅绿虚线  维修间与天桥支路      锈红圆点  本轮布景位置',19,ink)
d.line([(64,975),(1984,975)],fill='#aaab99',width=2)
for i,(n,title,xy,a,b) in enumerate(points):
    x=65+(i%3)*646; y=995+(i//3)*143
    txt(x,y,n,28,rust,True);txt(x+55,y,title,25,ink,True)
    txt(x+55,y+42,a,18);txt(x+55,y+70,b,18)
txt(68,1288,'图示范围包括仓库与相邻车站。上层天桥以投影表示。编号对应地图内同名布景点。',16,'#54685d')
img.save(ROOT/'02-layout.png',optimize=True)
