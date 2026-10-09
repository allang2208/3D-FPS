"""Portal-only PBR/detail authoring; retain existing room and sign identities."""
from pathlib import Path
import json,shutil,math
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
ROOT=Path(__file__).resolve().parent;PARENT=ROOT.parent;BASE='/Game/Dungeons/FacilityTransit20261007/RefineV2'
for p in ('Authored/Textures','Receipts','Snapshots'):(ROOT/p).mkdir(parents=True,exist_ok=True)
for file in ('manifest.json','Config/layout.json','Config/materials.json','author.py'):
 dest=ROOT/'Snapshots'/Path(file).name
 if not dest.exists():shutil.copy2(PARENT/file,dest)
def write(p,v):(ROOT/p).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8')
# Matched, periodic micro-surfaces. The maps are original synthesized material data.
rng=np.random.default_rng(610071);N=1024
def smooth(scale):
 a=rng.random((scale,scale));a=np.pad(a,((0,1),(0,1)),mode='wrap')
 return np.asarray(Image.fromarray(a.astype('float32'),mode='F').resize((N+N//scale,N+N//scale),Image.Resampling.BICUBIC))[:N,:N]
def surface(name,height,shade,rough):
 dx=(np.roll(height,-1,1)-np.roll(height,1,1));dy=(np.roll(height,-1,0)-np.roll(height,1,0));normal=np.stack((-dx,dy,np.ones_like(dx)),axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
 for suffix,data in [('NormalDX',((normal*.5+.5)*255).astype('uint8')),('Roughness',np.clip(rough*255,0,255).astype('uint8')),('Tone',np.clip(shade*255,0,255).astype('uint8'))]:
  Image.fromarray(data).save(ROOT/'Authored/Textures'/('T_FT2_'+name+'_'+suffix+'.png'))
fine=smooth(400);mid=smooth(120);broad=smooth(14)
surface('Paint',fine*.11+mid*.055,.82+.14*broad+.025*fine,.49+.16*broad+.035*fine)
lines=rng.random((N,1));brushed=np.repeat(lines,N,axis=1)*.055+smooth(320)*.012
surface('Steel',brushed,.75+.17*np.repeat(smooth(70).mean(axis=1)[:,None],N,axis=1),.29+.12*broad+.05*fine)
surface('Rubber',smooth(280)*.16+mid*.09,.72+.22*broad,.77+.12*broad)
surface('Ceramic',fine*.025+mid*.012,.91+.055*broad,.23+.055*broad)
roles=json.loads((PARENT/'Config/materials.json').read_text('utf8'))
colors={'FR':[55,74,82],'MD':[115,143,137],'TR':[115,62,35],'ST':[91,86,61],'EC':[66,95,68],'PW':[153,121,44],
 'Graphite':[39,44,45],'Ivory':[181,181,168],'Gasket':[28,30,28],'Brushed':[147,157,158],'Porcelain':[204,199,178],
 'SafetyRed':[138,36,28],'SafetyYellow':[172,137,50]}
def linear(v):
 s=v/255;return s/12.92 if s<=.04045 else ((s+.055)/1.055)**2.4
for name,c in colors.items():
 family='Rubber' if name=='Gasket' else 'Steel' if name=='Brushed' else 'Ceramic' if name=='Porcelain' else 'Paint'
 roles[name]=dict(basecolor_linear=[linear(v) for v in c],roughness=.5,metallic=.88 if family=='Steel' else 0.04 if family=='Paint' else 0.,uv_meters=.40 if family!='Steel' else .65,family=family,new_authored=True,existing_ue_path=BASE+'/Materials/M_FT2_'+name)
roles['TechLabels']=dict(basecolor_linear=[.2,.2,.2],roughness=.7,metallic=.1,uv_meters=1,new_authored=True,existing_ue_path=BASE+'/Materials/M_FT2_TechLabels')
for k in ('Steel','Rubber','Dark','White','Red','Yellow','Ceramic'):
 roles[k]=dict(roles[dict(Steel='Brushed',Rubber='Gasket',Dark='Graphite',White='Ivory',Red='SafetyRed',Yellow='SafetyYellow',Ceramic='Porcelain')[k]])
write('materials.json',roles)
im=Image.new('RGB',(2048,2048),(25,29,28));d=ImageDraw.Draw(im);rects={}
F=lambda n:ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',n)
cards=[('switch','三相隔离开关','QS-03  /  400 V  /  630 A'),('danger','高压危险','AUTHORIZED ELECTRICAL STAFF ONLY'),('load','通道限载标识','BAY 03  /  PERSONNEL ACCESS'),('filter','高效空气过滤','H13 FILTER  /  SERVICE PANEL'),('wash','手部清洁','PRESS DISPENSER / KEEP DRY'),('hot','高温排风管','EXHAUST  /  INSULATION JACKET'),('ppe','进入前佩戴防护','THERMAL AREA  /  PPE REQUIRED'),('keys','员工钥匙与信件','STAFF MAIL / KEY RETURN'),('supply','供水  →','SUPPLY  /  DN 80'),('return','回水  ←','RETURN  /  DN 50'),('valve','循环水总阀','V-201  /  CLOSE CLOCKWISE'),('serial','设施运维资产','ASSET 02-071 / INSPECT EACH SHIFT')]
for i,(key,cn,en) in enumerate(cards):
 x=16+(i%2)*1024;y=16+(i//2)*256;w=992;h=224;rects[key]=[x,y,x+w,y+h]
 d.rounded_rectangle((x,y,x+w-1,y+h-1),radius=12,fill=(190,191,172),outline=(68,78,71),width=7)
 d.text((x+34,y+21),cn,font=F(52),fill=(37,49,43));d.text((x+36,y+112),en,font=F(27),fill=(47,57,49))
 for j in range(28):
  bx=x+40+j*9;d.rectangle((bx,y+176,bx+int(rng.integers(2,6)),y+201),fill=(58,66,58))
 d.text((x+600,y+163),'FT / '+str(i+1).zfill(3),font=F(24),fill=(65,75,64))
# Readable gauge dial and switch positions each use a separate square face.
for key,x in [('gauge',16),('switchdial',544),('flow',1072)]:
 y=1568;s=480;rects[key]=[x,y,x+s,y+s]
 d.ellipse((x+3,y+3,x+s-3,y+s-3),fill=(201,202,182),outline=(57,68,62),width=6)
 if key=='gauge':
  for i in range(61):
   a=math.radians(-135+i*4.5);r=196;r2=173 if i%10==0 else 183
   d.line((x+240+math.sin(a)*r,y+240-math.cos(a)*r,x+240+math.sin(a)*r2,y+240-math.cos(a)*r2),fill=(42,50,45),width=3 if i%10==0 else 2)
   if i%10==0:d.text((x+223+math.sin(a)*145,y+221-math.cos(a)*145),str(i//10),font=F(26),fill=(38,51,44))
  d.text((x+192,y+295),'bar',font=F(27),fill=(41,53,45));d.text((x+139,y+337),'CW / V-201',font=F(20),fill=(41,53,45))
 elif key=='switchdial':
  d.text((x+170,y+52),'I / ON',font=F(36),fill=(39,57,47));d.text((x+137,y+365),'O / OFF',font=F(36),fill=(39,57,47))
 else:
  d.text((x+110,y+80),'L / min',font=F(32),fill=(39,57,47))
  for i in range(7):d.text((x+110,y+142+i*40),str(60-i*10),font=F(26),fill=(39,57,47));d.line((x+210,y+156+i*40,x+305,y+156+i*40),fill=(39,57,47),width=3)
im.save(ROOT/'Authored/Textures/T_FT2_EquipmentLabels.png');write('atlas.json',dict(size=list(im.size),rects=rects))
# Retain every original actor identity and location; only the six PPE cabinet yaws change.
cfg=json.loads((PARENT/'Config/layout.json').read_text('utf8'))
for p in cfg['containers']:
 if p['id'].startswith('PPE'):p['yaw_deg']=180
cfg['revision']='20261007-portal-refine-v2';cfg['active_refinement']=str(ROOT)
(PARENT/'Config/layout.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf8')
print('PORTAL_PBR_AND_PPE_LAYOUT_SAVED')
