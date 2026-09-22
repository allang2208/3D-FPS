"""Author original workshop PBR surfaces and legible maintenance-board artwork; no previews."""
from pathlib import Path
import json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonWorkshopDetail20260921')
OUT=ROOT/'Authored'; TEX=OUT/'Textures'; TEX.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(92142)
recipes={}

def surface(name,rgb,rough,metal=0,size=1024):
    small=Image.fromarray(rng.integers(95,160,(32,32),dtype=np.uint8)).resize((size,size),Image.Resampling.BICUBIC)
    macro=(np.asarray(small,dtype=float)-128)/255
    micro=rng.normal(0,1,(size,size))
    color=np.clip(np.array(rgb)[None,None,:]+macro[:,:,None]*7+micro[:,:,None]*.65,0,255).astype('uint8')
    r=np.clip(rough+macro*.04+micro*.003,0,1)
    height=micro*.0005
    if name=='Cardboard':
        stripe=np.sin(np.arange(size)*math.tau/5)[None,:]
        color=np.clip(color.astype(float)+stripe[:,:,None]*1.3,0,255).astype('uint8')
        height+=stripe*.001
    if name=='Steel':
        brushed=rng.normal(0,.8,(size,1))
        color=np.clip(color.astype(float)+brushed[:,:,None],0,255).astype('uint8')
    dy,dx=np.gradient(height)
    normal=np.dstack((-dx,-dy,np.ones_like(dx)));normal/=np.linalg.norm(normal,axis=2)[:,:,None]
    maps={}
    for ch,arr in [('BaseColor',color),('Roughness',(r*255).astype('uint8')),('Normal',((normal*.5+.5)*255).astype('uint8'))]:
        file=TEX/(name+'_'+ch+'.png');Image.fromarray(arr).save(file);maps[ch]=str(file)
    recipes[name]={'maps':maps,'metallic':metal}

for args in [('PaintRed',(94,36,31),.57,0),('RackPaint',(62,71,64),.61,0),
             ('Steel',(118,123,125),.34,.92),('Cardboard',(133,108,75),.86,0),
             ('BluePlastic',(43,64,76),.53,0),('DarkRubber',(25,28,27),.8,0),
             ('BareEdge',(89,83,73),.60,.65)]:surface(*args)

# Original vector-like diagram and handwritten equations, rasterized as an engine texture.
W,H=2304,1440
board=Image.new('RGB',(W,H),(214,221,219));d=ImageDraw.Draw(board)
hand='C:/Windows/Fonts/segoepr.ttf';bold='C:/Windows/Fonts/segoeprb.ttf'
def font(s,strong=False):return ImageFont.truetype(bold if strong else hand,s)
ink=(31,46,58);red=(133,44,35);blue=(29,63,106)
def text(x,y,s,size=45,color=ink,strong=False):d.text((x,y),s,font=font(size,strong),fill=color,stroke_width=0)
def line(points,color=ink,width=4):d.line(points,fill=color,width=width,joint='curve')
def arrow(a,b,color=blue):
    line([a,b],color);theta=math.atan2(b[1]-a[1],b[0]-a[0])
    for turn in (-.45,.45):line([b,(b[0]-20*math.cos(theta+turn),b[1]-20*math.sin(theta+turn))],color)
# Faint dry-wipe remnants appear below the active writing, never obscure equations.
ghost=Image.new('RGB',(W,H),(0,0,0));gd=ImageDraw.Draw(ghost)
gd.text((150,520),'pressure loss / previous run',font=font(55),fill=(24,24,24))
g=ghost.convert('L').filter(ImageFilter.GaussianBlur(8));wash=Image.new('RGB',(W,H),(132,143,141));board.paste(wash,(0,0),g);d=ImageDraw.Draw(board)
text(95,55,'M-04  /  PUMP & DRIVE',72,strong=True)
text(1675,90,'SERVICE BAY 02',31,blue)
line([(96,170),(2110,178)],blue,5)
text(100,210,'FLOW',42,blue,True)
text(115,284,'Q = A v',60)
text(112,374,'A = pi D² / 4',53)
text(112,466,'D = 50 mm',46)
text(112,548,'Q = 3.6 m³/h = 0.001 m³/s',42)
text(110,640,'v = 0.51 m/s',53)
d.ellipse((75,620,635,726),outline=blue,width=4)
text(850,213,'LIFT / POWER',42,blue,True)
text(848,291,'P_h = rho g Q H',55)
text(847,385,'rho = 1000 kg/m³',43)
text(846,465,'H = 12 m  =>  P_h ~ 118 W',43)
text(848,551,'eta = 0.62',47)
text(847,635,'P_in = P_h / eta ~ 190 W',46)
line([(840,730),(2055,730)],ink,3)
text(845,774,'P = T w     w = 2 pi n / 60',43)
text(845,852,'n = 1450 rpm  =>  w ~ 152 rad/s',36)
text(845,927,'T = 1.25 N m  =>  P ~ 190 W',39)
line([(795,215),(777,1025)],blue,2)
# Tank, suction path, pump, check valve and discharge: plausible workshop sketch.
text(103,805,'SUCTION → DISCHARGE',33,blue)
line([(125,930),(125,1120),(365,1120),(365,930)],ink,4)
for yy in (1030,1044):line([(137,yy),(351,yy+3)],blue,3)
arrow((365,1068),(470,1068));d.ellipse((470,1012,580,1124),outline=ink,width=5)
arrow((492,1100),(556,1035));line([(580,1068),(670,1068),(670,943)],ink,4)
line([(640,985),(699,985),(670,948),(640,985)],blue,3)
arrow((670,945),(670,890));text(480,1141,'M-04',28)
text(864,1092,'CHECK SEAL  /  LOG VIBRATION',39,red,True)
text(864,1171,'Isolate → inspect → restart',39,red)
text(123,1285,'07:30     A. / maintenance',30,blue)
text(1615,1304,'READING @ LOAD',27,ink)
path=TEX/'Whiteboard_BaseColor.png';board.resize((2048,2048),Image.Resampling.LANCZOS).save(path)
Image.new('L',(2048,2048),112).save(TEX/'Whiteboard_Roughness.png')
recipes['Whiteboard']={'maps':{'BaseColor':str(path),'Roughness':str(TEX/'Whiteboard_Roughness.png')},'metallic':0}

# 4 x 4 atlas: labels have their own UV islands and remain text, not random noise.
atlas=Image.new('RGB',(2048,1024),(177,173,154));ad=ImageDraw.Draw(atlas)
names=[('M-04','FIELD SERVICE'),('01 / SOCKETS','6 - 24 mm'),('02 / FASTENERS','M8 / M10 / M12'),('03 / HAND TOOLS','RETURN AFTER USE'),
       ('SEALS','DN 50 / SPARES'),('BEARINGS','6204 / 6205'),('M8 - M12','BOLTS + WASHERS'),('ELECTRICAL','FUSES / 24 V'),
       ('FILTER','M-04 / REPLACEMENT'),('GASKET KIT','KEEP DRY'),('RACK B-02','MAX 60 kg / SHELF'),('MAINTENANCE','INSPECTED 21 / 09'),
       ('GREASE','NLGI 2'),('CLEAN PARTS','M-04 / INLET'),('USED PARTS','TAG BEFORE RETURN'),('DO NOT DISCARD','SERVICE RECORDS')]
for i,(title,sub) in enumerate(names):
    x=(i%4)*512;y=(i//4)*256
    ad.rounded_rectangle((x+13,y+18,x+499,y+238),radius=5,fill=(192,188,166),outline=(86,86,73),width=3)
    ad.rectangle((x+27,y+34,x+485,y+57),fill=(63,75,74))
    ad.text((x+32,y+83),title,font=ImageFont.truetype('C:/Windows/Fonts/consolab.ttf',34),fill=(38,45,44))
    ad.text((x+33,y+157),sub,font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',23),fill=(55,61,57))
    for k in range(32):
        xx=x+34+k*5;ad.line([(xx,y+209),(xx,y+228)],fill=(44,50,45),width=1+k%2)
atlas.save(TEX/'Labels_BaseColor.png')
recipes['Labels']={'maps':{'BaseColor':str(TEX/'Labels_BaseColor.png')},'metallic':0,'roughness':.77}
(OUT/'material-manifest.json').write_text(json.dumps(recipes,indent=2),encoding='utf-8')
print('WORKSHOP_SURFACES_AUTHORED',len(recipes),'NO_RENDER')
