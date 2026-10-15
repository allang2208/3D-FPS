"""Material-specific, band-limited industrial PBR surfaces and proportioned labels."""
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent;PROJECT=ROOT.parents[2]
FONT=PROJECT/'Content/UI/GunsmithWorkbench/Fonts/NotoSansSC-Regular.otf'
ASSETS=json.loads((BASE/'texture_manifest.json').read_text('utf-8'))['assets']
SURFACES={
 'plastic':((.018,.023,.026),.60,0),'rubber':((.012,.014,.015),.82,0),
 'ceramic':((.43,.405,.355),.84,0),'steel':((.44,.48,.51),.36,.97),
 'aluminum':((.54,.57,.59),.40,.98),'blacksteel':((.035,.044,.047),.58,.80),
 'copper':((.48,.23,.105),.38,.96),'gold':((.50,.33,.12),.38,.95),
 'fiber':((.39,.345,.255),.94,0),'red':((.18,.012,.009),.86,0),
 'blue':((.018,.065,.085),.61,0),'white':((.61,.62,.58),.73,0),
 'ink':((.012,.014,.016),.75,0),'orange':((.42,.13,.018),.62,0),
 'paper':((.49,.45,.35),.94,0),'canvas':((.048,.066,.060),.94,0),
 'ceramic_alt':((.39,.37,.33),.86,0),'ceramic_core':((.32,.315,.275),.87,0),
 'castmetal':((.43,.46,.48),.53,.96),'adhesive':((.14,.10,.06),.76,0),
 'wax':((.19,.013,.008),.51,0),'paper_light':((.59,.55,.44),.92,0),
 'zinc':((.36,.39,.40),.47,.97),'edge':((.38,.40,.40),.42,.93)}
REGIONS={n:[i%8*512,i//8*512,i%8*512+512,i//8*512+512] for i,n in enumerate(SURFACES)}
rng=np.random.default_rng(261015667)
base=Image.new('RGB',(4096,4096),(60,63,62));orm=Image.new('RGB',(4096,4096),(255,170,0));normal=Image.new('RGB',(4096,4096),(128,128,255))
def srgb(v):return np.where(v<=.0031308,v*12.92,1.055*np.power(np.clip(v,0,1),1/2.4)-.055)
def noise(cells):
 a=rng.uniform(0,255,(cells,cells)).astype(np.uint8)
 return np.asarray(Image.fromarray(a).resize((512,512),Image.Resampling.BICUBIC),dtype=float)/255-.5
stats={}
for name,(color,rough,metal) in SURFACES.items():
 x,y,_,_=REGIONS[name];n=512;yy,xx=np.mgrid[:n,:n]
 coarse=noise(9);medium=noise(60);fine=noise(220)
 variation=.025*coarse+.014*medium;relief=.035*medium;roughmap=rough+.025*medium
 if name.startswith('ceramic'):
  dots=Image.new('L',(n,n),0);draw=ImageDraw.Draw(dots)
  for _ in range(1150):
   cx,cy=rng.uniform(0,n,2);r=rng.uniform(.45,2.3)
   draw.ellipse((cx-r,cy-r*.75,cx+r,cy+r*.75),fill=int(rng.uniform(35,180)))
  pores=np.asarray(dots.filter(ImageFilter.GaussianBlur(.65)),dtype=float)/255
  variation=.15*coarse+.13*medium+.035*fine-.16*pores
  relief=.20*medium+.05*fine-.55*pores;roughmap=rough+.09*medium+.04*pores
 elif name in ('steel','aluminum','blacksteel','zinc','edge','copper','gold'):
  bands=np.asarray(Image.fromarray(rng.uniform(30,220,(180,1)).astype(np.uint8)).resize((512,512),Image.Resampling.BICUBIC),dtype=float)/255-.5
  variation=.018*coarse+.018*bands+.012*fine
  relief=.025*bands+.008*fine;roughmap=rough+.025*bands+.015*coarse
 elif name=='castmetal':
  variation=.028*coarse+.020*fine;relief=.035*fine+.010*medium;roughmap=rough+.035*fine
 elif name=='fiber':
  variation=.045*medium+.025*fine;relief=.025*fine+.010*medium;roughmap=rough+.018*fine
 elif name in ('canvas','red'):
  warp=np.sin(xx*1.08)*np.sin(yy*.78)
  variation=.040*coarse+.025*medium+.012*warp;relief=.035*warp+.015*fine;roughmap=rough+.018*medium
 elif name.startswith('paper'):
  variation=.12*coarse+.04*medium;relief=.10*medium;roughmap=rough+.025*coarse
 elif name in ('blue','plastic','orange'):
  variation=.045*medium+.025*coarse;relief=.09*medium;roughmap=rough+.045*medium
 c=np.clip(np.array(color)[None,None,:]*(1+variation[:,:,None]),0,1)
 base.paste(Image.fromarray(np.uint8(srgb(c)*255)),(x,y))
 orm.paste(Image.fromarray(np.dstack([np.full((n,n),255),np.clip(roughmap,0,1)*255,np.full((n,n),metal*255)]).astype(np.uint8)),(x,y))
 dy,dx=np.gradient(relief);v=np.dstack([-dx,-dy,np.ones((n,n))]);v/=np.linalg.norm(v,axis=2)[:,:,None]
 normal.paste(Image.fromarray(np.uint8((v*.5+.5)*255)),(x,y))
 stats[name]=dict(linear_base=color,roughness_mean=float(np.mean(roughmap)),metallic=metal,normal_z_mean=float(v[:,:,2].mean()))
labels=[('RespiratorFilter','RF-08','SEALED FILTER','密封呼吸滤罐',1112,1024),('CeramicModule','RC-17','REFRACTORY','耐火陶瓷组件',1280,296),('Thermocouple','TC-34','TEMPERATURE PROBE','高温热电偶',1024,1024),('IndustrialFilter','FC-28','FILTER CARTRIDGE','工业过滤芯',626,1024),('IncidentArchive','ARCHIVE / 066','INCINERATION INCIDENT','封存焚化事故档案',1024,1024),('CatalyticCore','CC-22','FLUE GAS CATALYST','烟气净化催化芯',1024,1024)]
for i,(key,code,title,chinese,w,h) in enumerate(labels):
 x=(i%3)*1280;y=2048+(i//3)*1024;REGIONS[key]=[x,y,x+w,y+h]
 im=Image.new('RGB',(w,h),(196,194,174) if key!='IncidentArchive' else (179,173,146));d=ImageDraw.Draw(im)
 def text(pos,s,size,fill=(28,35,35),anchor='mm'):d.text(pos,s,font=ImageFont.truetype(str(FONT),max(12,int(size))),fill=fill,anchor=anchor)
 d.rectangle((18,18,w-18,h-18),outline=(74,78,67),width=3)
 if key=='CeramicModule':
  d.line((w*.28,36,w*.28,h-36),fill=(60,70,66),width=3)
  text((w*.15,h*.34),'CS',85);text((w*.15,h*.70),code,48)
  text((w*.64,h*.34),chinese,62);text((w*.64,h*.69),'REFRACTORY / LOT 26-1015',36)
 elif key=='IncidentArchive':
  text((w/2,110),'CS / 焚化处理记录室',54);d.line((65,185,w-65,185),fill=(57,63,55),width=4)
  text((w/2,265),chinese,65);text((w/2,350),code,57)
  for j,label in enumerate(['区域 / 焚化处理厅','类别 / 设备异常与交接记录','状态 / 原始记录封存','编号 / CS-066-261015']):
   text((100,450+j*90),label,34,anchor='lm');d.line((95,490+j*90,w-95,490+j*90),fill=(110,112,96),width=2)
  d.rectangle((200,845,824,945),outline=(121,39,24),width=5);text((w/2,895),'封存 / SEALED',52,(121,39,24))
 else:
  f=min(w/1024,1.)
  text((w/2,h*.12),'CS / COLD STEEL',58*f);d.line((w*.08,h*.22,w*.92,h*.22),fill=(65,72,64),width=3)
  text((w/2,h*.33),code,100*f);text((w/2,h*.46),title,43*f);text((w/2,h*.56),chinese,65*f)
  d.rectangle((w*.08,h*.67,w*.92,h*.76),fill=(42,56,57));text((w/2,h*.715),'SERVICE STOCK',45*f,(224,222,205))
  for j in range(49):
   xx=int(w*(.12+j*.0155));d.rectangle((xx,h*.81,xx+max(2,int(w*.003)),h*.90),fill=(33,41,40))
  text((w/2,h*.955),'CS-26-1015 / QC',35*f)
 base.paste(im,(x,y));orm.paste(Image.new('RGB',(w,h),(255,200,0)),(x,y))
textures={}
for kind,im in [('BaseColor',base),('ORM',orm),('Normal',normal)]:
 p=ROOT/'Textures'/('T_IncinerationRefine_'+kind+'.png');im.save(p);textures[kind]=str(p)
for row in ASSETS.values():row.update(material='M_IncinerationCollectibles_DetailV2',textures=textures,size=4096)
(ROOT/'texture_manifest.json').write_text(json.dumps(dict(regions=REGIONS,assets=ASSETS,shared_atlas=True,normal_convention='OpenGL; UE flip green',surface_metrics=stats,label_aspects='Authored per physical label, no square-image squashing'),ensure_ascii=False,indent=2),encoding='utf-8')
print('DETAIL_TEXTURES_SAVED')
