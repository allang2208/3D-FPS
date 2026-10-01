"""Original printable industrial labels and dial markings; source textures, no render."""
import json,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];OUT=Path(globals().get('EXPORT_OUT',ROOT/'Authored'));OUT.mkdir(parents=True,exist_ok=True)
im=Image.new('RGB',(2048,2048),(175,176,159));d=ImageDraw.Draw(im)
font='C:/Windows/Fonts/msyh.ttc'
def f(size):return ImageFont.truetype(font,size)
def centre(text,x,y,size,color=(30,38,36)):
    d.text((x,y),text,font=f(size),fill=color,anchor='mm')
rects={}
labels=[('Main','烟气净化站','FLUE GAS TREATMENT / FG-01','停用设施 · 设备检修通道'),
    ('Entry','焚化处理厅','INCINERATION / INLET','烟气处理系统 · 禁止开启阀门'),
    ('Exit','设施通道','FACILITY ACCESS / EXIT','保持通道畅通'),
    ('Platform','检修平台','MAINTENANCE GALLERY','注意高差 · 请走楼梯'),
    ('Tower1','一级洗涤塔','ST-01 / QUENCH SCRUBBER','设备停用 · 高温 / 腐蚀风险'),
    ('Tower2','二级净化塔','ST-02 / POLISHING SCRUBBER','检修前确认管路隔离'),
    ('Filter','滤袋除尘器','BF-01 / BAG FILTER','残留粉尘 · 佩戴呼吸防护'),
    ('Fan','引风机组','ID-01 / INDUCED DRAFT','旋转机械 · 禁止擅自通电')]
for i,(key,title,sub,small) in enumerate(labels):
    x=(i%2)*1024;y=(i//2)*320;rect=(x+8,y+8,x+1016,y+312);rects[key]=rect
    d.rectangle(rect,fill=(196,198,177),outline=(44,60,56),width=12)
    d.rectangle((x+22,y+225,x+1001,y+296),fill=(177,146,51))
    centre(title,x+512,y+83,66);centre(sub,x+512,y+170,30);centre(small,x+512,y+260,32)
for key,cx,cy,unit,limit in [('Pressure',256,1560,'kPa',400),('Temperature',768,1560,'°C',300)]:
    rects[key]=(cx-226,cy-226,cx+226,cy+226)
    d.ellipse((cx-222,cy-222,cx+222,cy+222),fill=(193,190,163),outline=(54,54,45),width=7)
    for i in range(51):
        a=math.radians(135+i*5.4);r0=165 if i%5==0 else 180;r1=196
        d.line((cx+r0*math.cos(a),cy+r0*math.sin(a),cx+r1*math.cos(a),cy+r1*math.sin(a)),fill=(42,42,32),width=4 if i%5==0 else 2)
        if i%10==0:centre(str(int(i/50*limit)),cx+140*math.cos(a),cy+140*math.sin(a),24)
    centre(unit,cx,cy+67,36);centre('CLASS 1.6',cx,cy+103,17)
rects['Stripe']=(1050,1340,2020,1540)
d.rectangle(rects['Stripe'],fill=(167,134,39))
for x in range(850,2150,140):d.polygon([(x,1340),(x+68,1340),(x+220,1540),(x+152,1540)],fill=(30,33,30))
rects['Serial']=(1050,1580,2020,1880)
d.rectangle(rects['Serial'],fill=(182,181,161),outline=(40,45,40),width=9)
for j,t in enumerate(['FACILITY ENGINEERING / FG SERIES','ASSET No.  8704-016 / REV. 03','DESIGN PRESSURE  0.4 MPa','ISOLATE / DRAIN / LOCK OUT']):centre(t,1535,1618+j*69,30)
for i,(key,title,sub) in enumerate([('Inlet','入口压力','INLET PRESSURE'),('Flow','塔内温度','GAS TEMPERATURE'),
    ('FanStart','风机启动','FAN START'),('FanStop','风机停止','FAN STOP'),('Auto','手动 / 自动','HAND - OFF - AUTO'),
    ('Reset','故障复位','RESET'),('Drain','排污阀','DRAIN'),('Supply','循环供液','CIRCULATION')]):
    x=i*256;rects[key]=(x+4,1894,x+252,2038)
    d.rectangle(rects[key],fill=(191,192,174),outline=(39,47,40),width=4)
    centre(title,x+128,1942,28);centre(sub,x+128,1994,18)
im.save(OUT/'T_FlueGas_Labels_BaseColor.png')
(OUT/'atlas.json').write_text(json.dumps(dict(size=[2048,2048],rects=rects),indent=2),encoding='utf-8')
print('FLUE_GAS_LABEL_TEXTURE_WRITTEN')
