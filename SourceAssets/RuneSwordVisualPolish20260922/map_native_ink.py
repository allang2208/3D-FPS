"""Map source-atlas ink to the real blade/guard surface for root correction."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
P=Path(__file__).resolve().parent
SRC=P.parent/'RuneSword20260913/Original/Meshy_AI_Azure_Starblade_0913123202_texture_fbx/Meshy_AI_Azure_Starblade_0913123202_texture.png'
rgb=np.asarray(Image.open(SRC).convert('RGB'),dtype=np.float32)/255
h,w=rgb.shape[:2]
d=np.load(P/'blade_guard_uv.npz')
r,g,b=np.moveaxis(rgb,-1,0);chroma=np.minimum(g-r,b-r)
old=np.asarray(Image.open(P/'Before/native_ink_mask.png'),dtype=np.float32)/255
rows=[];maps={}
for part in ['blade','guard']:
    cover=np.zeros((h,w),bool); xyz=np.zeros((h,w,3),np.float32)
    for uv,pos in zip(d[part+'_uv'],d[part+'_position']):
        q=np.stack((uv[:,0]*w-.5,(1-uv[:,1])*h-.5),axis=1)
        x0,y0=np.maximum(np.floor(q.min(0)).astype(int),0)
        x1,y1=np.minimum(np.ceil(q.max(0)).astype(int),(w-1,h-1))
        if x1<x0 or y1<y0:continue
        a,bb,c=q;den=(bb[1]-c[1])*(a[0]-c[0])+(c[0]-bb[0])*(a[1]-c[1])
        if abs(den)<1e-8:continue
        yy,xx=np.mgrid[y0:y1+1,x0:x1+1]
        wa=((bb[1]-c[1])*(xx-c[0])+(c[0]-bb[0])*(yy-c[1]))/den
        wb=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den;wc=1-wa-wb
        inside=(wa>=-1e-5)&(wb>=-1e-5)&(wc>=-1e-5)
        patch=xyz[y0:y1+1,x0:x1+1];sample=wa[...,None]*pos[0]+wb[...,None]*pos[1]+wc[...,None]*pos[2]
        patch[inside]=sample[inside];cover[y0:y1+1,x0:x1+1]|=inside
    maps[part+'_coverage']=cover;maps[part+'_xyz']=xyz
    for lo,hi in [(-.04,.04),(.04,.08),(.08,.125),(.125,.16),(.16,.22),(.22,.82)]:
        region=cover&(xyz[:,:,2]>=lo)&(xyz[:,:,2]<hi)
        candidate=region&(chroma>.028)&(b>g*.88)
        selected=candidate&(old>.25)
        missing=candidate&(old<.1)
        rows.append(dict(part=part,z=[lo,hi],cyan=int(candidate.sum()),old_selected=int(selected.sum()),missing=int(missing.sum()),missing_chroma_max=float(chroma[missing].max()) if missing.any() else 0))
    # Orthographic source-color point maps reveal central root glyphs on both faces.
    for face in [-1,1]:
        valid=cover&(xyz[:,:,2]<.24)&(xyz[:,:,2]>-.04)&(xyz[:,:,1]*face>0)
        canvas=np.full((1000,850,3),28,np.uint8)
        py=((.24-xyz[:,:,2])/.28*999).astype(int);px=((xyz[:,:,0]+.119)/.238*849).astype(int)
        valid&=(px>=0)&(px<850)&(py>=0)&(py<1000)
        for dy in range(-1,2):
            for dx in range(-1,2):
                canvas[np.clip(py[valid]+dy,0,999),np.clip(px[valid]+dx,0,849)]=(rgb[valid]*255).astype(np.uint8)
        Image.fromarray(canvas).save(P/(part+'_root_'+str(face)+'.png'))
np.savez_compressed(P/'surface_mapping.npz',**maps)
(P/'root_diagnosis.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print(json.dumps(rows,indent=2))
