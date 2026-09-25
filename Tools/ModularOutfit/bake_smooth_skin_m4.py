"""Bake the refined skin atlas and a physical-scale pore height/normal tile."""
import json,runpy
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/SmoothSkinV2'
runpy.run_path(str(PROJECT/'Tools/ModularOutfit/bake_original_shape_skin.py'),
    init_globals={'AUTHOR_ROOT':str(ROOT),'SMOOTH_SKIN':True})
size=1024;tile_cm=2.0;depth_cm=.0025;rng=np.random.default_rng(9242026)
height=np.zeros((size,size),np.float64)
for _ in range(6600):
    x,y=rng.uniform(0,size,2);diameter=rng.uniform(.013,.028) # 0.13--0.28 mm
    sigma=diameter/3.2/tile_cm*size;ratio=rng.uniform(.75,1.28)
    angle=rng.uniform(0,np.pi);radius=int(np.ceil(sigma*3.8))
    xx=np.arange(int(x)-radius,int(x)+radius+1);yy=np.arange(int(y)-radius,int(y)+radius+1)
    dx,dy=np.meshgrid(xx-x,yy-y)
    a=(dx*np.cos(angle)+dy*np.sin(angle))/(sigma*ratio)
    b=(-dx*np.sin(angle)+dy*np.cos(angle))/(sigma/ratio)
    pit=-rng.uniform(.00055,.00155)*np.exp(-.5*(a*a+b*b))
    height[np.ix_(yy%size,xx%size)]+=pit
height+=gaussian_filter(rng.normal(size=(size,size)),3.5,mode='wrap')*.00025
height=np.clip(height,-depth_cm,0)
dx=(np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))/(2*tile_cm/size)
dy=(np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))/(2*tile_cm/size)
normal=np.stack((-dx,-dy,np.ones_like(dx)),axis=-1)
normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
relief=1+height/depth_cm
rough=np.clip(.48+(-height/depth_cm)*.055+gaussian_filter(rng.normal(size=(size,size)),1.1,mode='wrap')*.008,.40,.58)
packed=np.stack((normal[...,0]*.5+.5,normal[...,1]*.5+.5,relief,rough),axis=-1)
Image.fromarray(np.uint8(np.clip(packed*255+.5,0,255))).save(ROOT/'T_M4OriginalShape_SkinMicro.png')
Image.fromarray(np.uint16(np.clip(relief*65535+.5,0,65535))).save(ROOT/'SkinPores_Height16_Source.png')
np.save(ROOT/'SkinPores_HeightCm.npy',height.astype(np.float32))
source=json.loads((ROOT/'M4_original.json').read_text());shape=json.loads((ROOT/'M4_bare_shape.json').read_text())
p=np.asarray(shape['positions']);uv=np.asarray(source['uv']);tri=np.asarray(source['triangles'])
skin=np.asarray(shape['triangle_materials'])==2
a,b,c=(p[tri[:,i]] for i in range(3));area=np.linalg.norm(np.cross(b-a,c-a),axis=1)*.5
duv1=uv[:,1]-uv[:,0];duv2=uv[:,2]-uv[:,0]
uvarea=np.abs(duv1[:,0]*duv2[:,1]-duv1[:,1]*duv2[:,0])*.5
atlas_cm=float(np.sqrt(area[skin].sum()/uvarea[skin].sum()))
report={'source':'Locally authored stochastic elliptical pore height field; no cloth/leather normals',
 'tile_size_cm':tile_cm,'texture_size':size,'height_range_cm':depth_cm,
 'pore_diameter_mm':[.13,.28],'atlas_cm_per_uv':atlas_cm,'tile_repeat':atlas_cm/tile_cm,
 'channels':{'R':'tangent normal X encoded','G':'tangent normal Y encoded; DirectX',
             'B':'height: flat=1','A':'roughness from same pore field'},
 'runtime':'Two bounded micro-height samples; derivative fade; no ray marching or geometry displacement',
 'preview_rendered':False,'runtime_tested':False}
(ROOT/'micro_surface.json').write_text(json.dumps(report,indent=2))
print('SMOOTH_SKIN_ATLAS_AND_PHYSICAL_PORES_BAKED')
