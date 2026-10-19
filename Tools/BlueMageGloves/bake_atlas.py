"""Bake physical surface fields into the two existing native glove UV atlases."""
import json,sys
from pathlib import Path
import numpy as np
from scipy.ndimage import distance_transform_edt
from PIL import Image
sys.path.insert(0,str(Path(__file__).parent));from surface_fields import evaluate
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageGloves20261019'

def image(path,value):Image.fromarray(np.uint8(np.clip(value,0,1)*255+.5)).save(path)

for name,size in [('M4',4096),('Body',2048)]:
    data=json.loads((R/'Sources'/(name+'.json')).read_text());source=np.load(R/'Fields'/(name+'.npz'));points=source['canonical'];fields=source['fields'];uv=np.array(data['uv']);faces=np.array(data['triangles'])
    atlas=np.zeros((size,size,8),np.float32);metric=np.zeros((size,size,3),np.float32);mask=np.zeros((size,size),bool)
    for fi,tri in enumerate(faces):
        tex=uv[fi];a,b,c=tex*size-.5;ab=b-a;ac=c-a;den=ab[0]*ac[1]-ab[1]*ac[0]
        if abs(den)<1.e-8:continue
        lo=np.maximum(np.floor(np.minimum(np.minimum(a,b),c)).astype(int),0);hi=np.minimum(np.ceil(np.maximum(np.maximum(a,b),c)).astype(int)+1,size)
        if np.any(hi<=lo):continue
        yy,xx=np.mgrid[lo[1]:hi[1],lo[0]:hi[0]];dx=xx-a[0];dy=yy-a[1];s=(dx*ac[1]-dy*ac[0])/den;t=(ab[0]*dy-ab[1]*dx)/den;inside=(s>=-1e-5)&(t>=-1e-5)&(s+t<=1.00001)
        if not inside.any():continue
        xs,ys=xx[inside],yy[inside];weights=np.c_[1-s[inside]-t[inside],s[inside],t[inside]]
        atlas[ys,xs]=weights@fields[tri]
        e1,e2=points[tri[1]]-points[tri[0]],points[tri[2]]-points[tri[0]];du,dv=tex[1]-tex[0],tex[2]-tex[0];det=du[0]*dv[1]-du[1]*dv[0]
        u=(e1*dv[1]-e2*du[1])/det;v=(-e1*dv[0]+e2*du[0])/det;length=max(np.linalg.norm(u),1.e-7);projection=np.dot(v,u/length);orth=max(np.linalg.norm(v-u/length*projection),1.e-7)
        metric[ys,xs]=[length,projection,orth];mask[ys,xs]=True
    root=R/'Textures'/name;root.mkdir(parents=True,exist_ok=True)
    h=np.zeros((size,size),np.float32);color=np.zeros((size,size,3),np.float32);orm=np.zeros_like(color);fuzz=np.zeros_like(h)
    for start in range(0,size,128):
        end=min(start+128,size);f=evaluate(atlas[start:end]);h[start:end]=f['height'];color[start:end]=f['color'];orm[start:end,:,0]=f['ao'];orm[start:end,:,1]=f['rough'];fuzz[start:end]=f['fuzz']
    del atlas
    nearest=distance_transform_edt(~mask,return_distances=False,return_indices=True);iy,ix=nearest
    for a in (h,color,orm,fuzz,metric):a[~mask]=a[iy[~mask],ix[~mask]]
    # UV V increases downward in the saved image. Tangent +Y is image -V.
    dhdv,dhdu=np.gradient(h,1/size,1/size);su=dhdu/np.maximum(metric[:,:,0],1.e-5);sv=(dhdv-su*metric[:,:,1])/np.maximum(metric[:,:,2],1.e-5)
    normal=np.stack([-su,sv,np.ones_like(su)],-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    normal=normal*.5+.5;normal[~mask]=normal[iy[~mask],ix[~mask]]
    safety=np.clip((distance_transform_edt(mask)-3)/17,0,1);relief=np.stack([np.clip(.5+h/.06,0,1),fuzz,safety],-1)
    for channel,a in [('BaseColor',color),('Normal',normal),('ORM',orm),('Relief',relief)]:image(root/('T_BlueMageGloves_'+name+'_'+channel+'.png'),a)
    np.save(root/'physical_height_cm.npy',h);print('MAGE_GLOVE_ATLAS_BAKED',name,size,flush=True)
(R/'surface_source.json').write_text(json.dumps(dict(bake='Analytic woven and embroidered physical height fields rasterized in original native UVs; metric-derived tangent normals; same fields build high meshes',normal_convention='OpenGL; UE flips green',relief_depth_cm=.06,atlas_sizes={'M4':4096,'Body':2048},new_runtime_texture_slots=0,runtime_tested=False),indent=2),encoding='utf-8')
