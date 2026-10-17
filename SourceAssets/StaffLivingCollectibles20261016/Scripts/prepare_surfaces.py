"""4K manufactured-surface atlas: microfinish, original labels, no photograph dependence."""
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
FONT=PROJECT/'Content/UI/GunsmithWorkbench/Fonts/NotoSansSC-Regular.otf'
ASSETS=json.loads((ROOT/'design.json').read_text('utf-8'))['assets']
SURFACES={
 'plastic':((.025,.030,.038),.43,0),'rubber':((.009,.011,.014),.76,0),
 'steel':((.48,.52,.56),.27,1),'aluminum':((.32,.36,.40),.32,1),
 'blacksteel':((.028,.035,.045),.32,.85),'gold':((.64,.39,.12),.23,.97),
 'white':((.68,.71,.71),.48,0),'ink':((.005,.006,.009),.57,0),
 'navy':((.012,.032,.065),.38,.7),'copper':((.53,.25,.085),.3,1),
 'keycap':((.015,.019,.025),.46,0),'screen':((.005,.009,.013),.16,.10),
 'leather':((.018,.022,.024),.70,0),'paper':((.73,.68,.53),.82,0),
 'glass':((.83,.91,.93),.045,0),'liquid':((.50,.25,.08),.055,0),
 'blueglass':((.008,.025,.040),.10,.25),'red':((.34,.016,.011),.45,0),
 'ceramic':((.64,.64,.61),.35,0),'edge':((.58,.62,.65),.19,1),
 'silicon':((.055,.065,.072),.67,0),'green':((.012,.12,.055),.48,0),
 'bronze':((.20,.11,.065),.29,.92),'silverfoil':((.52,.54,.56),.39,.92)}
REGIONS={k:[i%8*512,i//8*512,i%8*512+512,i//8*512+512] for i,k in enumerate(SURFACES)}
base=Image.new('RGB',(4096,4096),(20,22,27));orm=Image.new('RGB',(4096,4096),(255,140,0));normal=Image.new('RGB',(4096,4096),(128,128,255))
rng=np.random.default_rng(26101677)
def noise(cells):
 a=rng.integers(0,256,(cells,cells),dtype=np.uint8)
 return np.asarray(Image.fromarray(a).resize((512,512),Image.Resampling.BICUBIC),dtype=float)/255-.5
def srgb(a):return np.where(a<=.0031308,a*12.92,1.055*np.clip(a,0,1)**(1/2.4)-.055)
metrics={}
for key,(color,rough,metal) in SURFACES.items():
 x,y,_,_=REGIONS[key];med=noise(72);fine=noise(300);coarse=noise(8)
 var=.012*coarse+.016*med;relief=.012*fine;rm=rough+.018*med
 if metal>.6:
  bands=np.asarray(Image.fromarray(rng.integers(30,220,(300,1),dtype=np.uint8)).resize((512,512),Image.Resampling.BICUBIC),dtype=float)/255-.5
  var=.010*bands+.008*fine;relief=.018*bands+.006*fine;rm=rough+.038*bands+.009*med
 elif key=='leather':
  relief=.10*med+.035*fine;var=.07*med;rm=rough+.045*med
 elif key in ('plastic','keycap','rubber','silicon'):
  relief=.017*med+.010*fine;var=.018*med;rm=rough+.035*fine+.012*coarse
 elif key=='paper':var=.035*coarse+.015*fine;relief=.015*med+.01*fine
 elif key in ('screen','blueglass','glass'):
  relief=.001*med;var=.002*coarse;rm=rough+.004*coarse
 c=np.clip(np.array(color)[None,None,:]*(1+var[:,:,None]),0,1)
 base.paste(Image.fromarray(np.uint8(srgb(c)*255)),(x,y))
 orm.paste(Image.fromarray(np.uint8(np.dstack([np.full((512,512),255),np.clip(rm,0,1)*255,np.full((512,512),metal*255)]))),(x,y))
 dy,dx=np.gradient(relief);v=np.dstack([-dx,-dy,np.ones((512,512))]);v/=np.linalg.norm(v,axis=2)[:,:,None]
 normal.paste(Image.fromarray(np.uint8((v*.5+.5)*255)),(x,y))
 metrics[key]={'linear_base':color,'roughness':rough,'metallic':metal,'detail':'band-limited material-specific microfinish'}
def font(size):return ImageFont.truetype(str(FONT),size)
def label(key,xy,size,bg,fg,lines):
 x,y=xy;w,h=size;im=Image.new('RGB',size,bg);d=ImageDraw.Draw(im)
 d.rounded_rectangle((14,14,w-15,h-15),radius=12,outline=fg,width=2)
 for frac,text,pt in lines:d.text((w/2,h*frac),text,font=font(pt),fill=fg,anchor='mm')
 REGIONS[key]=[x,y,x+w,y+h];base.paste(im,xy);orm.paste(Image.new('RGB',size,(255,170,0)),xy)
label('Perfume',(0,2048),(768,1024),(225,213,179),(57,44,30),[(.12,'CS / ATELIER',40),(.32,'IRIS',124),(.48,'Nº 07',72),(.66,'EAU DE PARFUM',32),(.78,'PRIVATE COLLECTION',28),(.9,'50 ml / 1.7 FL.OZ.',29)])
label('Laptop',(768,2048),(1280,512),(32,38,45),(182,190,194),[(.16,'CS  /  FIELDNOTE 14',55),(.39,'BUSINESS MOBILE COMPUTER',32),(.59,'MODEL FN-14  ·  INPUT 20V 3.25A',28),(.78,'S/N CS26-1048-761  /  ASSEMBLED FOR FIELD USE',24)])
label('Player',(2048,2048),(768,768),(23,31,43),(187,201,208),[(.16,'CS / PERSONAL AUDIO',31),(.38,'POCKET 02',65),(.60,'HI-RES DIGITAL PLAYER',28),(.78,'64 GB  /  5V DC  /  SERIAL 260177',20)])
label('Camera',(2816,2048),(1280,512),(29,29,31),(192,189,175),[(.18,'CS  /  C-7 COMPACT',49),(.43,'OPTICAL INSTRUMENT / PRIVATE SERIES',28),(.69,'MODEL C7  ·  DC 5V  ·  S/N 26-001683',25),(.85,'RECYCLE ELECTRONIC EQUIPMENT',20)])
# Bright LCD text remains printed on an opaque display layer; it is not a running UI.
label('PlayerScreen',(0,3072),(768,1024),(10,19,25),(121,160,165),[(.18,'CS AUDIO',45),(.43,'—  OFFLINE  —',43),(.68,'ARCHIVE / 064',25),(.84,'PERSONAL LIBRARY',24)])
label('LensLabel',(768,3072),(1536,256),(25,28,31),(191,194,183),[(.5,'CS OPTICS   6.2–24.8 mm   1:2.0–4.9   ASPHERICAL',45)])
textures={}
for kind,im in [('BaseColor',base),('ORM',orm),('Normal',normal)]:
 p=ROOT/'Textures'/('T_StaffPrivate_'+kind+'.png');im.save(p);textures[kind]=str(p)
for spec in ASSETS.values():spec.update(material='M_Living_Surface',size=4096,textures=textures)
(ROOT/'texture_manifest.json').write_text(json.dumps(dict(regions=REGIONS,assets=ASSETS,surface_metrics=metrics,shared_atlas=True,normal_convention='OpenGL; flip green on UE import'),ensure_ascii=False,indent=2),encoding='utf-8')
print('LIVING_PBR_TEXTURES_SAVED')
