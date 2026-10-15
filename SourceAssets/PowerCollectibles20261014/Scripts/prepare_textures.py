from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
FONT=PROJECT/'Content/UI/GunsmithWorkbench/Fonts/NotoSansSC-Regular.otf'
SURFACES={
 'plastic':((.025,.030,.034),.48,0), 'rubber':((.009,.012,.015),.78,0),
 'ceramic':((.70,.69,.61),.27,0), 'steel':((.52,.55,.58),.26,.95),
 'aluminum':((.59,.62,.65),.34,.98), 'blacksteel':((.055,.065,.075),.38,.9),
 'copper':((.57,.26,.10),.29,.97), 'gold':((.62,.41,.14),.28,.96),
 'pcb':((.022,.075,.057),.52,0), 'red':((.43,.019,.014),.48,0),
 'blue':((.018,.085,.16),.46,0), 'white':((.72,.75,.71),.53,0),
 'ink':((.008,.011,.014),.65,0), 'orange':((.71,.25,.035),.52,0),
 'teal':((.025,.13,.13),.50,0), 'screen':((.04,.15,.10),.22,0)}
REGIONS={n:[i%8*512,i//8*512,i%8*512+512,i//8*512+512] for i,n in enumerate(SURFACES)}
REGIONS.update(fuse=[0,1024,1024,3072],module=[1024,1024,3072,2048],cell=[3072,1024,4096,3584],warning=[1024,2048,3072,2560],pcb_art=[1024,2560,3072,4096],serial=[0,3072,1024,4096])
ASSETS={
 'FuseSet':dict(id='search_industrial_fuse_set',name='工业熔断器组',mesh='SM_Power_IndustrialFuseSet',grid=[1,1]),
 'PowerModule':dict(id='search_power_control_module',name='功率控制模块',mesh='SM_Power_ControlModule',grid=[2,1]),
 'StorageCell':dict(id='search_energy_storage_cell',name='密封储能电芯',mesh='SM_Power_EnergyStorageCell',grid=[1,2])}
rng=np.random.default_rng(14102026)
base=Image.new('RGB',(4096,4096),(35,40,43));orm=Image.new('RGB',(4096,4096),(255,140,0));normal=Image.new('RGB',(4096,4096),(128,128,255))
def srgb(x):return np.where(x<=.0031308,x*12.92,1.055*np.power(np.clip(x,0,1),1/2.4)-.055)
for name,(color,rough,metal) in SURFACES.items():
 x0,y0,x1,y1=REGIONS[name];n=512
 noise=rng.normal(0,1,(n,n));grain=rng.normal(0,1,(n,1))
 variation=noise*.005+(grain*.009 if metal else 0)
 c=np.clip(np.array(color)[None,None,:]*(1+variation[:,:,None]),0,1)
 base.paste(Image.fromarray(np.uint8(np.clip(srgb(c),0,1)*255)),(x0,y0))
 r=np.clip(rough+noise*.013+(grain*.025 if metal else 0),0,1)
 a=np.dstack([np.full((n,n),255),r*255,np.full((n,n),metal*255)]).astype(np.uint8)
 orm.paste(Image.fromarray(a),(x0,y0))
 height=noise*(.035 if name in ('rubber','plastic') else .012)+grain*(.055 if metal else .005)
 dy,dx=np.gradient(height);v=np.dstack([-dx,-dy,np.ones((n,n))]);v/=np.linalg.norm(v,axis=2)[:,:,None]
 normal.paste(Image.fromarray(np.uint8((v*.5+.5)*255)),(x0,y0))
def text(d,xy,s,size,color=(222,227,222),anchor=None):d.text(xy,s,font=ImageFont.truetype(str(FONT),int(size)),fill=color,anchor=anchor)
for kind in ('fuse','module','cell','warning','pcb_art','serial'):
 x0,y0,x1,y1=REGIONS[kind];w,h=x1-x0,y1-y0
 bg=(212,216,205) if kind in ('fuse','cell','serial') else (33,43,47) if kind=='module' else (208,143,40) if kind=='warning' else (26,67,56)
 im=Image.new('RGB',(w,h),bg);d=ImageDraw.Draw(im);ink=(31,40,43);pale=(220,226,221)
 if kind=='fuse':
  text(d,(w/2,h*.11),'CS',180,ink,'mm');text(d,(w/2,h*.23),'COLD STEEL',88,ink,'mm')
  text(d,(w/2,h*.40),'F-32',190,ink,'mm');text(d,(w/2,h*.55),'INDUSTRIAL',80,ink,'mm')
  text(d,(w/2,h*.65),'FUSE LINK',90,ink,'mm');text(d,(w/2,h*.77),'32A  /  500V',86,ink,'mm');text(d,(w/2,h*.91),'LOT 26-104',70,ink,'mm')
  d.line((w*.12,h*.30,w*.88,h*.30),fill=(125,133,125),width=5)
 elif kind=='module':
  text(d,(w*.06,h*.1),'CS  /  COLD STEEL',120,pale);text(d,(w*.06,h*.34),'PC-240',210,pale)
  text(d,(w*.06,h*.69),'POWER CONTROL MODULE',72,(233,168,64));text(d,(w*.06,h*.84),'SERVICE REPLACEMENT  /  REV.04',55,pale)
  for i in range(45):
   x=int(w*.71+i*9);d.rectangle((x,h*.18,x+int(rng.integers(2,7)),h*.58),fill=pale)
 elif kind=='cell':
  text(d,(w/2,h*.09),'CS / COLD STEEL',76,ink,'mm');text(d,(w/2,h*.20),'ES-160',150,ink,'mm')
  text(d,(w/2,h*.30),'SEALED',100,ink,'mm');text(d,(w/2,h*.36),'STORAGE CELL',75,ink,'mm')
  d.rounded_rectangle((w*.1,h*.43,w*.9,h*.67),radius=18,outline=(91,103,102),width=6)
  for i,line in enumerate(['ENERGY SYSTEMS','INSULATED TERMINALS','SERVICE UNIT  04','SERIAL  CS-104-2614']):text(d,(w*.16,h*(.46+i*.048)),line,43,ink)
  d.rectangle((w*.08,h*.73,w*.92,h*.81),fill=(198,135,31));text(d,(w/2,h*.77),'CAUTION  /  SEALED UNIT',44,ink,'mm')
  for i in range(55):
   x=int(w*.14+i*13);d.rectangle((x,h*.85,x+int(rng.integers(3,9)),h*.93),fill=ink)
 elif kind=='warning':
  d.polygon([(80,h*.78),(190,h*.16),(300,h*.78)],outline=ink,width=12);text(d,(190,h*.52),'!',150,ink,'mm')
  text(d,(w*.18,h*.18),'ISOLATE BEFORE SERVICE',95,ink);text(d,(w*.18,h*.56),'POWER SYSTEMS  /  AUTHORIZED MAINTENANCE',51,ink)
 elif kind=='pcb_art':
  for i in range(26):
   y=60+i*52;x=60+int(rng.integers(0,380));end=w-50-int(rng.integers(0,350))
   d.line([(x,y),(x+120,y),(x+190,y+65),(end,y+65)],fill=(53,115,80),width=6)
   for xx,yy in [(x,y),(end,y+65)]:d.ellipse((xx-10,yy-10,xx+10,yy+10),fill=(185,165,104));d.ellipse((xx-4,yy-4,xx+4,yy+4),fill=ink)
  for i in range(12):text(d,(100+i%4*470,200+i//4*420),f'R{i+1:02d}   C{i+12:02d}',26,pale)
  text(d,(w*.5,h*.91),'CS  /  CONTROL PCB  /  240-04',42,pale,'mm')
 else:
  text(d,(w/2,h*.14),'COLD STEEL',70,ink,'mm');text(d,(w/2,h*.3),'INDUSTRIAL SERVICE',48,ink,'mm')
  for i in range(31):
   x=95+i*27;d.rectangle((x,h*.45,x+int(rng.integers(4,14)),h*.7),fill=ink)
  text(d,(w/2,h*.84),'BATCH 261014  /  QC 07',44,ink,'mm')
 base.paste(im,(x0,y0));orm.paste(Image.new('RGB',(w,h),(250,145,0)),(x0,y0))
textures={}
for k,im in [('BaseColor',base),('ORM',orm),('Normal',normal)]:
 path=ROOT/'Textures'/('T_PowerCollectibles_'+k+'.png');im.save(path);textures[k]=str(path)
for a in ASSETS.values():a.update(material='M_PowerCollectibles_PBR',textures=textures,size=4096)
(ROOT/'texture_manifest.json').write_text(json.dumps(dict(regions=REGIONS,assets=ASSETS,shared_atlas=True,normal_convention='OpenGL; flip green in UE',original_markings='CS/COLD STEEL'),ensure_ascii=False,indent=2),'utf-8')
print('POWER_SURFACES_SAVED',flush=True)
