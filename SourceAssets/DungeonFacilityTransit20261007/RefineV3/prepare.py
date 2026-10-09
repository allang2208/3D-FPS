"""Shared near-view PPE fabric maps and proportional package labels."""
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent;PARENT=ROOT.parent;BASE='/Game/Dungeons/FacilityTransit20261007/RefineV3'
for p in ('Authored/Textures','Receipts'):(ROOT/p).mkdir(parents=True,exist_ok=True)
roles=json.loads((PARENT/'RefineV2/materials.json').read_text('utf8'))
roles['PPEFabric']=dict(existing_ue_path=BASE+'/Materials/M_FT3_PPEFabric',basecolor_linear=[.24,.22,.16],roughness=.82,metallic=0,uv_meters=.24)
roles['PPELabels']=dict(existing_ue_path=BASE+'/Materials/M_FT3_PPELabels',basecolor_linear=[.7,.68,.55],roughness=.70,metallic=0,uv_meters=1)
(ROOT/'materials.json').write_text(json.dumps(roles,indent=2),encoding='utf8')
n=1024;y,x=np.mgrid[:n,:n]/n;rng=np.random.default_rng(71008)
warp=np.sin(x*np.pi*256);weft=np.sin(y*np.pi*256);alternate=np.sin((x+y)*np.pi*128)
height=(warp*.38+weft*.38+alternate*.11)*.00009
tone=np.clip(.88+warp*.035+weft*.035+rng.normal(0,.014,(n,n)),0,1)
rough=np.clip(.82+.05*warp*weft+rng.normal(0,.008,(n,n)),0,1)
dy,dx=np.gradient(height,.24/n);norm=np.stack([-dx,-dy,np.ones_like(x)],axis=-1);norm/=np.linalg.norm(norm,axis=-1,keepdims=True);norm[...,1]*=-1
for key,v in [('Fabric_Tone',tone),('Fabric_Roughness',rough)]:Image.fromarray((v*255).astype('uint8')).save(ROOT/'Authored/Textures'/('T_FT3_'+key+'.png'))
Image.fromarray(((norm*.5+.5)*255).astype('uint8')).save(ROOT/'Authored/Textures/T_FT3_Fabric_NormalDX.png')
im=Image.new('RGB',(1024,512),(192,189,160));d=ImageDraw.Draw(im)
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',n)
for i,(cn,en) in enumerate([('防护套装','PROTECTION KIT / 01'),('过滤元件','FILTER CARTRIDGE / P3')]):
    oy=i*256;d.rectangle((14,oy+14,1009,oy+241),outline=(50,64,52),width=5);d.text((40,oy+30),cn,font=font(76),fill=(33,48,38));d.text((42,oy+149),en,font=font(44),fill=(43,57,45))
    for j in range(39):
        bx=790+j*4;d.rectangle((bx,oy+44,bx+1+(j%3==0),oy+116),fill=(35,46,38))
im.save(ROOT/'Authored/Textures/T_FT3_PPELabels.png')
print('FACILITY_V3_MATERIAL_SOURCES_SAVED')
