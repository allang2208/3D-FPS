"""Original facade/sign production atlases, not an upscale of the former background."""
import random,json
from PIL import Image,ImageDraw,ImageFont
from design import *
FACADES.mkdir(parents=True,exist_ok=True)
r=random.Random(SEED)
size=2048
base=Image.new('RGB',(size,size),(21,28,36));em=Image.new('RGB',(size,size))
b=ImageDraw.Draw(base);e=ImageDraw.Draw(em)
colors=[(89,170,202),(134,188,202),(205,155,95),(179,184,163),(70,113,162)]
for j in range(48):
 for i in range(32):
  x=64*i;y=round(size*j/48);yn=round(size*(j+1)/48)
  panel=r.randint(18,28)
  b.rectangle((x+1,y+1,x+62,yn-2),fill=(panel,panel+7,panel+14))
  b.rectangle((x+6,y+5,x+57,yn-7),fill=(7,13,21))
  b.line((x+32,y+5,x+32,yn-7),fill=(31,37,44),width=2)
  b.line((x,y+2,x+64,y+2),fill=(39,44,50),width=2)
  occupied=r.random()<(.52 if j%8<5 else .25)
  if occupied:
   col=r.choice(colors);gain=r.uniform(.28,.85)
   for l,h in [(7,30),(34,56)]:
    if r.random()<.13:continue
    e.rectangle((x+l,y+6,x+h,yn-8),fill=tuple(int(c*gain) for c in col))
    # Shutters, partitions and blinds retain visible architectural structure.
    if r.random()<.34:
     for yy in range(y+9,yn-8,6):e.line((x+l,yy,x+h,yy),fill=tuple(int(c*gain*.3) for c in col),width=1)
base.save(FACADES/'T_BayFacade_BC.png');em.save(FACADES/'T_BayFacade_E.png')
atlas=Image.new('RGB',(2048,2048),(2,4,9));d=ImageDraw.Draw(atlas)
font_path='C:/Windows/Fonts/msyh.ttc'
font=ImageFont.truetype(font_path,90);small=ImageFont.truetype(font_path,30)
names=[('星港','ESTUARY DISTRICT'),('NEXUS','NEURAL SYSTEMS'),('海湾','BAY TERMINAL'),('ORBIT','AFTER HOURS'),
       ('霓界','NIGHT MARKET'),('KAIRO','BIOSYNTHETICS'),('云际','CLOUD NETWORK'),('DOCK 09','CARGO EXCHANGE'),
       ('潮汐','TIDAL ENERGY'),('NOVA','RESIDENCES'),('航路','TRAFFIC CONTROL'),('HARBOR','EAST QUAY'),
       ('极光','AURORA LABS'),('AXIOM','DATA CENTRE'),('新岸','NEW SHORE'),('SECTOR 7','FREEPORT')]
for k,(title,caption) in enumerate(names):
 x=(k%4)*512;y=(k//4)*512;c=tuple(int(v*220) for v in PALETTE[k%4])
 d.rectangle((x+24,y+24,x+488,y+488),outline=c,width=6)
 d.line((x+48,y+69,x+170,y+69),fill=c,width=8)
 bounds=d.textbbox((0,0),title,font=font);scale=min(1,420/max(1,bounds[2]-bounds[0]))
 f=ImageFont.truetype(font_path,int(90*scale));w=d.textlength(title,font=f)
 d.text((x+(512-w)/2,y+174),title,font=f,fill=c)
 w=d.textlength(caption,font=small);d.text((x+(512-w)/2,y+316),caption,font=small,fill=tuple(int(v*.65) for v in c))
 for n in range(12):d.rectangle((x+56+n*33,y+411,x+71+n*33,y+419),fill=c if n%4 else (12,20,30))
atlas.save(FACADES/'T_BaySigns_E.png')
(ROOT/'texture-source.json').write_text(json.dumps({'size':size,'facade_grid':[32,48],
 'seed':SEED,'original_procedural_atlases':True,'former_image_used':False,'font':font_path},indent=2),encoding='utf8')
print('BAY_TEXTURES_AUTHORED')
