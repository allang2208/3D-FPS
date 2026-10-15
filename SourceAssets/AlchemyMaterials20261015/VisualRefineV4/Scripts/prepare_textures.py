"""Original 4K packaging/surface atlas; no generated third-party branding."""
from pathlib import Path
import json, numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[2]
FONT=PROJECT/'Content/UI/GunsmithWorkbench/Fonts/NotoSansSC-Regular.otf'
ASSETS={
 'BaseFluid':dict(id='alchemy_pure_base_fluid',name='高纯调配基液',mesh='SM_Alchemy_PureBaseFluid',grid=[1,2],rarity='rare',stack=5,value=60,code='BF-01'),
 'Stabilizer':dict(id='alchemy_compound_stabilizer',name='复合稳定剂',mesh='SM_Alchemy_CompoundStabilizer',grid=[1,2],rarity='rare',stack=5,value=70,code='ST-02'),
 'Catalyst':dict(id='alchemy_active_catalyst',name='活性催化晶',mesh='SM_Alchemy_ActiveCatalyst',grid=[1,1],rarity='epic',stack=3,value=160,code='AC-03'),
 'RedRoot':dict(id='alchemy_redvein_extract',name='赤脉根萃取物',mesh='SM_Alchemy_RedveinExtract',grid=[1,2],rarity='rare',stack=5,value=80,code='RR-04'),
 'BlueFungus':dict(id='alchemy_bluemarrow_crystals',name='蓝髓菌结晶',mesh='SM_Alchemy_BluemarrowCrystals',grid=[1,1],rarity='rare',stack=5,value=80,code='BM-05'),
 'Silverleaf':dict(id='alchemy_silverleaf_essence',name='银叶花精华',mesh='SM_Alchemy_SilverleafEssence',grid=[1,2],rarity='epic',stack=3,value=180,code='SL-06')}
ASSETS={k:v for k,v in ASSETS.items() if k in ('Stabilizer','Catalyst','BlueFungus')}
SURFACES={
 'plastic':((.035,.045,.05),.47,0),'rubber':((.014,.018,.021),.72,0),
 'steel':((.50,.55,.59),.24,.96),'blacksteel':((.065,.09,.10),.31,.92),
 'aluminum':((.65,.69,.71),.3,.98),'gold':((.60,.38,.14),.28,.95),
 'white':((.81,.84,.79),.53,0),'ink':((.012,.018,.021),.57,0),
 'teal':((.035,.22,.23),.42,0),'red':((.25,.012,.025),.33,0),
 'blue':((.045,.16,.34),.32,0),'green':((.08,.18,.12),.42,0),
 'crystal':((.32,.075,.49),.16,0),'bluecrystal':((.025,.20,.39),.17,0),
 'root':((.13,.025,.019),.82,0),'foam':((.035,.046,.044),.93,0)}
REGIONS={n:[i%8*512,i//8*512,i%8*512+512,i//8*512+512] for i,n in enumerate(SURFACES)}
for i,key in enumerate(ASSETS):REGIONS[key]=[(i%3)*1360,1024+(i//3)*1536,(i%3)*1360+1360,1024+(i//3)*1536+1536]
rng=np.random.default_rng(20261015)
base=Image.new('RGB',(4096,4096),(38,44,45));orm=Image.new('RGB',(4096,4096),(255,145,0));normal=Image.new('RGB',(4096,4096),(128,128,255))
def srgb(c):return np.where(c<=.0031308,c*12.92,1.055*np.power(np.clip(c,0,1),1/2.4)-.055)
for name,(c,r,m) in SURFACES.items():
 x,y,_,_=REGIONS[name];n=512;noise=rng.normal(0,1,(n,n));grain=rng.normal(0,1,(n,1));v=noise*.013+grain*(.015 if m else .003)
 col=np.clip(np.array(c)[None,None,:]*(1+v[:,:,None]),0,1)
 base.paste(Image.fromarray(np.uint8(srgb(col)*255)),(x,y))
 rough=np.clip(r+noise*.012+grain*(.018 if m else .006),0,1)
 orm.paste(Image.fromarray(np.uint8(np.dstack([np.full((n,n),255),rough*255,np.full((n,n),m*255)]))),(x,y))
 height=noise*(.10 if name=='foam' else .025)+grain*(.05 if m else .008);dy,dx=np.gradient(height)
 norm=np.dstack([-dx,-dy,np.ones((n,n))]);norm/=np.linalg.norm(norm,axis=2)[:,:,None]
 normal.paste(Image.fromarray(np.uint8((norm*.5+.5)*255)),(x,y))
def text(draw,xy,s,size,fill=(32,44,46),anchor=None):draw.text(xy,s,font=ImageFont.truetype(str(FONT),size),fill=fill,anchor=anchor)
accents=[(35,102,112),(62,102,110),(98,61,119),(133,43,53),(40,88,125),(75,111,78)]
accents={'Stabilizer':(36,94,100),'Catalyst':(83,42,111),'BlueFungus':(32,83,124)}
for key,spec in ASSETS.items():
 x,y,x1,_=REGIONS[key];w=x1-x;h=360;REGIONS[key]=[x,y,x1,y+h]
 im=Image.new('RGB',(w,h),(226,231,219));d=ImageDraw.Draw(im);accent=accents[key]
 d.rectangle((12,12,w-12,h-12),outline=accent,width=6)
 d.rectangle((24,24,205,h-24),fill=accent);text(d,(114,h/2),'CS',99,(245,246,234),'mm')
 text(d,(255,45),spec['code'],115)
 text(d,(255,205),spec['name'],77)
 text(d,(w-50,110),'SEALED',40,accent,'rm');text(d,(w-50,195),'REAGENT',40,accent,'rm')
 text(d,(w-50,279),'26-1015',37,accent,'rm')
 base.paste(im,(x,y));orm.paste(Image.new('RGB',(w,h),(255,155,0)),(x,y))
textures={}
for kind,img in [('BaseColor',base),('ORM',orm),('Normal',normal)]:
 path=ROOT/'Textures'/('T_Alchemy_'+kind+'.png');img.save(path);textures[kind]=str(path)
for spec in ASSETS.values():spec.update(material='M_Alchemy_Surface',textures=textures,size=4096)
(ROOT/'texture_manifest.json').write_text(json.dumps(dict(regions=REGIONS,assets=ASSETS,shared_atlas=True,normal_convention='OpenGL'),ensure_ascii=False,indent=2),'utf8')
print('ALCHEMY_TEXTURES_SAVED')
