"""Original industrial surfaces and markings; no external trademarks or source images."""
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
FONT=PROJECT/'Content/UI/GunsmithWorkbench/Fonts/NotoSansSC-Regular.otf'
SURFACES={
 'plastic':((.025,.033,.039),.48,0),'rubber':((.012,.015,.018),.78,0),
 'ceramic':((.64,.60,.48),.64,0),'steel':((.48,.52,.55),.30,.97),
 'aluminum':((.60,.63,.66),.36,.98),'blacksteel':((.05,.065,.07),.38,.92),
 'copper':((.53,.25,.12),.30,.96),'gold':((.55,.36,.13),.36,.95),
 'fiber':((.54,.49,.36),.90,0),'red':((.32,.015,.012),.64,0),
 'blue':((.025,.09,.13),.51,0),'white':((.73,.74,.69),.65,0),
 'ink':((.012,.014,.016),.67,0),'orange':((.55,.18,.025),.58,0),
 'paper':((.58,.54,.43),.86,0),'canvas':((.09,.12,.115),.91,0)}
REGIONS={n:[i%8*512,i//8*512,i%8*512+512,i//8*512+512] for i,n in enumerate(SURFACES)}
ASSETS={
 'RespiratorFilter':dict(id='search_sealed_respirator_filter',name='密封呼吸滤罐',mesh='SM_Incineration_RespiratorFilter',grid=[1,1],rarity='rare',value=450),
 'CeramicModule':dict(id='search_refractory_ceramic_module',name='耐火陶瓷组件',mesh='SM_Incineration_CeramicModule',grid=[2,1],rarity='rare',value=620),
 'Thermocouple':dict(id='search_high_temperature_thermocouple',name='高温热电偶',mesh='SM_Incineration_Thermocouple',grid=[2,1],rarity='rare',value=850),
 'IndustrialFilter':dict(id='search_industrial_filter_cartridge',name='工业过滤芯',mesh='SM_Incineration_IndustrialFilter',grid=[1,2],rarity='rare',value=780),
 'IncidentArchive':dict(id='search_sealed_incineration_archive',name='封存焚化事故档案',mesh='SM_Incineration_IncidentArchive',grid=[2,2],rarity='epic',value=1900),
 'CatalyticCore':dict(id='search_flue_gas_catalytic_core',name='烟气净化催化芯',mesh='SM_Incineration_CatalyticCore',grid=[2,2],rarity='epic',value=2400)}
rng=np.random.default_rng(26101566)
base=Image.new('RGB',(4096,4096),(50,55,58));orm=Image.new('RGB',(4096,4096),(255,155,0));normal=Image.new('RGB',(4096,4096),(128,128,255))
def srgb(x):return np.where(x<=.0031308,x*12.92,1.055*np.power(np.clip(x,0,1),1/2.4)-.055)
for name,(color,rough,metal) in SURFACES.items():
 x,y,_,_=REGIONS[name];n=512;noise=rng.normal(0,1,(n,n));grain=rng.normal(0,1,(n,1))
 pattern=noise*.009+grain*(.017 if metal else .005)
 if name in ('canvas','fiber'):
  yy,xx=np.mgrid[:n,:n];pattern+=.05*np.sin(xx*2.2)*np.sin(yy*1.8)
 c=np.clip(np.array(color)[None,None,:]*(1+pattern[:,:,None]),0,1)
 base.paste(Image.fromarray(np.uint8(srgb(c)*255)),(x,y))
 r=np.clip(rough+noise*.015+grain*.01,0,1)
 orm.paste(Image.fromarray(np.dstack([np.full((n,n),255),r*255,np.full((n,n),metal*255)]).astype(np.uint8)),(x,y))
 height=pattern*(3 if name in ('ceramic','fiber','canvas') else .45)
 dy,dx=np.gradient(height);v=np.dstack([-dx,-dy,np.ones((n,n))]);v/=np.linalg.norm(v,axis=2)[:,:,None]
 normal.paste(Image.fromarray(np.uint8((v*.5+.5)*255)),(x,y))
labels=[('RespiratorFilter','RF-08','SEALED FILTER','密封呼吸滤罐'),('CeramicModule','RC-17','REFRACTORY INSERT','耐火陶瓷组件'),('Thermocouple','TC-34','TEMPERATURE PROBE','高温热电偶'),('IndustrialFilter','FC-28','FILTER CARTRIDGE','工业过滤芯'),('IncidentArchive','ARCHIVE  /  066','INCINERATION INCIDENT','封存焚化事故档案'),('CatalyticCore','CC-22','FLUE GAS CATALYST','烟气净化催化芯')]
for i,(key,code,title,chinese) in enumerate(labels):
 x=(i%3)*1280;y=1024+(i//3)*1280;w=1280;h=1280
 REGIONS[key]=[x,y,x+w,y+h]
 im=Image.new('RGB',(w,h),(204,202,184) if key!='IncidentArchive' else (171,179,166));d=ImageDraw.Draw(im)
 def text(pos,s,size,fill=(27,36,39),anchor='mm'):d.text(pos,s,font=ImageFont.truetype(str(FONT),size),fill=fill,anchor=anchor)
 d.rectangle((28,28,w-28,h-28),outline=(58,70,70),width=7)
 text((w/2,120),'CS  /  COLD STEEL',75);d.line((80,210,w-80,210),fill=(62,72,70),width=5)
 text((w/2,320),code,104);text((w/2,490),title,60);text((w/2,620),chinese,75)
 d.rectangle((85,750,w-85,860),fill=(141,61,34) if key=='IncidentArchive' else (46,64,68))
 text((w/2,800),'SEALED RECORD' if key=='IncidentArchive' else 'INCINERATION FACILITY',51,(233,229,212))
 for j in range(65):
  xx=110+j*16;d.rectangle((xx,940,xx+int(rng.integers(3,10)),1090),fill=(35,43,43))
 text((w/2,1170),'CS - 26 - 1015   /   SERVICE STOCK',39)
 base.paste(im,(x,y));orm.paste(Image.new('RGB',(w,h),(255,185,0)),(x,y))
textures={}
for k,im in [('BaseColor',base),('ORM',orm),('Normal',normal)]:
 p=ROOT/'Textures'/('T_IncinerationCollectibles_'+k+'.png');im.save(p);textures[k]=str(p)
for a in ASSETS.values():a.update(material='M_IncinerationCollectibles_PBR',textures=textures,size=4096)
(ROOT/'texture_manifest.json').write_text(json.dumps(dict(regions=REGIONS,assets=ASSETS,shared_atlas=True,normal_convention='OpenGL; UE flip green',original_markings='CS/COLD STEEL'),ensure_ascii=False,indent=2),encoding='utf-8')
print('INCINERATION_TEXTURES_SAVED')
