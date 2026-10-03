"""Original woven cloth, linoleum and bilingual signs; no preview rendering."""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored';OUT.mkdir(parents=True,exist_ok=True)
n=1024
y,x=np.mgrid[0:n,0:n].astype(np.float32)/n
warp=np.cos(x*np.pi*2*128);weft=np.cos(y*np.pi*2*128)
weave=.55*warp+.45*weft+.25*warp*weft
age=(np.sin(x*np.pi*2*3+.8)*np.sin(y*np.pi*2*2)+1)*.5
cloth=np.empty((n,n,3),dtype=np.float32)
for i,c in enumerate((160,153,131)):cloth[:,:,i]=c+weave*7-age*8
Image.fromarray(np.uint8(np.clip(cloth,0,255))).save(OUT/'T_Staff_Fabric_BaseColor.png')
dx=-.55*np.sin(x*np.pi*2*128);dy=-.45*np.sin(y*np.pi*2*128)
normal=np.stack((-dx*.10,-dy*.10,np.ones_like(dx)),axis=2)
normal/=np.sqrt(np.sum(normal*normal,axis=2))[:,:,None]
Image.fromarray(np.uint8(np.clip((normal*.5+.5)*255,0,255))).save(OUT/'T_Staff_Fabric_Normal.png')
orm=np.stack((np.full_like(x,255),220+weave*10,np.zeros_like(x)),axis=2)
Image.fromarray(np.uint8(np.clip(orm,0,255))).save(OUT/'T_Staff_Fabric_ORM.png')
stone=np.sin(x*np.pi*2*19)*np.sin(y*np.pi*2*17)+.35*np.cos((x+y)*np.pi*2*43)
linoleum=np.stack([c+stone*4+age*3 for c in (88,99,88)],axis=2)
Image.fromarray(np.uint8(np.clip(linoleum,0,255))).save(OUT/'T_Staff_Linoleum_BaseColor.png')

atlas=Image.new('RGB',(2048,2048),(179,177,159));draw=ImageDraw.Draw(atlas);rects={}
font='C:/Windows/Fonts/msyh.ttc'
labels=[('Dormitory','生活宿舍区','STAFF DORMITORY'),('Changing','员工更衣区','CHANGING / DRY AREA'),
 ('Showers','员工淋浴区','SHOWERS / WET AREA'),('Recreation','员工活动区','STAFF RECREATION'),
 ('Meals','茶水与用餐区','MEALS / REFRESHMENTS'),('Quiet','休息区','QUIET LOUNGE'),
 ('ToChanging','更衣淋浴区 →','CHANGING / SHOWERS'),('Exit','出口 →','ONWARD ACCESS')]
for i in range(6):labels.append(('Room'+str(101+i),'宿舍 '+str(101+i),'STAFF ROOM '+str(101+i)))
for i in range(6):labels.append(('Shower'+str(1+i),'淋浴 '+str(1+i),'SHOWER '+str(1+i)))
for i,(title,sub) in enumerate((('值班安排','STAFF ROSTER'),('生活区管理','RESIDENT INFORMATION'),('卫生要求','HYGIENE NOTICE'),('活动时间','RECREATION SCHEDULE'))):
 labels.append(('Notice'+str(i),title,sub))
for i,(key,title,sub) in enumerate(labels):
 col=i%4;row=i//4;x0=col*512;y0=row*320
 rect=(x0+5,y0+5,x0+507,y0+313);rects[key]=rect
 draw.rectangle(rect,fill=(186,190,170),outline=(44,59,47),width=5)
 draw.rectangle((x0+16,y0+17,x0+496,y0+56),fill=(55,79,69))
 draw.text((x0+256,y0+135),title,font=ImageFont.truetype(font,40 if len(title)>7 else 48),fill=(27,42,33),anchor='mm')
 draw.text((x0+256,y0+212),sub,font=ImageFont.truetype(font,21),fill=(42,55,46),anchor='mm')
 draw.line((x0+25,y0+259,x0+487,y0+259),fill=(105,117,96),width=3)
 if key.startswith('Notice'):
  for j in range(3):draw.line((x0+43,y0+272+j*9,x0+432-j*27,y0+272+j*9),fill=(106,115,96),width=2)
atlas.save(OUT/'T_Staff_Labels_BaseColor.png')
(OUT/'atlas.json').write_text(json.dumps(dict(size=[2048,2048],rects=rects),ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'surface-manifest.json').write_text(json.dumps(dict(original_procedural_textures=True,
 font='Microsoft YaHei rasterized from local Windows font; no font binary distributed',tests_run=False,rendered=False,
 materials={
 'Fabric':dict(basecolor='T_Staff_Fabric_BaseColor',normal='T_Staff_Fabric_Normal',orm='T_Staff_Fabric_ORM',tint=[1,1,1]),
 'SofaFabric':dict(basecolor='T_Staff_Fabric_BaseColor',normal='T_Staff_Fabric_Normal',orm='T_Staff_Fabric_ORM',tint=[.44,.52,.46]),
 'Felt':dict(basecolor='T_Staff_Fabric_BaseColor',normal='T_Staff_Fabric_Normal',orm='T_Staff_Fabric_ORM',tint=[.20,.46,.31]),
 'Linoleum':dict(basecolor='T_Staff_Linoleum_BaseColor',roughness=.70,metallic=0),
 'Ceramic':dict(color=[.57,.60,.52],roughness=.29,metallic=0),
 'OlivePaint':dict(color=[.15,.23,.18],roughness=.54,metallic=.35),
 'Mirror':dict(color=[.70,.74,.73],roughness=.075,metallic=1),
 'Screen':dict(color=[.013,.024,.023],roughness=.15,metallic=.22),
 'LampGlass':dict(color=[.62,.66,.59],roughness=.48,metallic=0,emissive=[1.15,1.12,.98]),
 'Labels':dict(basecolor='T_Staff_Labels_BaseColor',roughness=.74,metallic=.05)}),ensure_ascii=False,indent=2),encoding='utf-8')
print('STAFF_LIVING_SURFACES_AUTHORED')
