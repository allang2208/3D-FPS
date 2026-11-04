"""Transfer existing crystal PBR into native rune-sword UV0; no renders/tests.

Rasterization here is an asset bake. Donor leather/bronze is excluded by its
source base color; both crystal faces retain their own source UV samples.
"""
from pathlib import Path
import json
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

P=Path(__file__).resolve().parent
OUT=P/'Textures';OUT.mkdir(exist_ok=True)
SIZE=2048

def unit(v):
    return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-9)

def raster(uv,positions,extra=None):
    count=3+(0 if extra is None else extra.shape[-1])
    data=np.zeros((SIZE,SIZE,count),np.float32)
    cover=np.zeros((SIZE,SIZE),bool)
    for i,(tex,pos) in enumerate(zip(uv,positions)):
        q=np.stack((tex[:,0]*SIZE-.5,(1-tex[:,1])*SIZE-.5),axis=1)
        x0,y0=np.maximum(np.floor(q.min(0)).astype(int),0)
        x1,y1=np.minimum(np.ceil(q.max(0)).astype(int),SIZE-1)
        if x0>x1 or y0>y1:continue
        a,b,c=q
        den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<1e-8:continue
        yy,xx=np.mgrid[y0:y1+1,x0:x1+1]
        wa=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
        wb=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den
        weights=np.stack((wa,wb,1-wa-wb),axis=-1)
        inside=(weights>=-1e-5).all(axis=-1)
        values=pos if extra is None else np.concatenate((pos,extra[i]),axis=-1)
        patch=data[y0:y1+1,x0:x1+1]
        patch[inside]=(weights@values)[inside]
        cover[y0:y1+1,x0:x1+1]|=inside
    return cover,data

donor=np.load(P/'donor.npz')
extra=np.concatenate((donor['normal'],donor['tangent'],donor['sign'][...,None]),axis=-1)
cover,donor_map=raster(donor['uv'],donor['position'],extra)
source=next((P.parent/'MeshyMelee20260915/Original').rglob('*_texture.png'))
images={}
for key,suffix in [('BaseColor',''),('Normal','_normal'),('Metallic','_metallic'),('Roughness','_roughness')]:
    path=source.with_name(source.stem+suffix+'.png')
    images[key]=np.asarray(Image.open(path).convert('RGB').resize((SIZE,SIZE),Image.Resampling.LANCZOS),np.float32)/255
rgb=images['BaseColor']
crystal=cover&(donor_map[:,:,2]>.12)&(donor_map[:,:,2]<.78)&(rgb[:,:,1]>rgb[:,:,0]+.10)&(rgb[:,:,2]>rgb[:,:,0]+.10)
target=np.load(P.parent/'RuneSwordVisualPolish20260922/blade_guard_uv.npz')
result={k:np.zeros((SIZE,SIZE,3),np.float32) for k in images}
result['Normal'][:]=(.5,.5,1.)
all_cover=np.zeros((SIZE,SIZE),bool)
for part in ['blade','guard']:
    uv=target[part+'_uv'];pos=target[part+'_position']
    edge1=pos[:,1]-pos[:,0];edge2=pos[:,2]-pos[:,0]
    duv1=uv[:,1]-uv[:,0];duv2=uv[:,2]-uv[:,0]
    det=duv1[:,0]*duv2[:,1]-duv1[:,1]*duv2[:,0]
    valid=np.abs(det)>1e-12
    uv=uv[valid];pos=pos[valid];edge1=edge1[valid];edge2=edge2[valid]
    duv1=duv1[valid];duv2=duv2[valid];det=det[valid,None]
    tang=unit((edge1*duv2[:,1,None]-edge2*duv1[:,1,None])/det)
    bitan=unit((edge2*duv1[:,0,None]-edge1*duv2[:,0,None])/det)
    frames=np.repeat(np.concatenate((tang,bitan),axis=-1)[:,None,:],3,axis=1)
    used,tmap=raster(uv,pos,frames)
    if part=='guard':used&=(tmap[:,:,2]>=.04)&(np.abs(tmap[:,:,0])<=.052)
    for side in [-1,1]:
        src=crystal&(donor_map[:,:,1]*side>=0)
        points=donor_map[src,:3]
        tree=cKDTree(points[:,[0,2]]*np.array([1.,.5]))
        dst=used&(tmap[:,:,1]*side>=0)
        xyz=tmap[dst,:3]
        # Map the full native carrier continuously to crystal-only donor metal.
        query=np.stack((xyz[:,0],.14+np.clip((xyz[:,2]-.04)/.772,0,1)*.62),axis=-1)
        _,idx=tree.query(query*np.array([1.,.5]),workers=4)
        for key in ['BaseColor','Metallic','Roughness']:
            result[key][dst]=images[key][src][idx]
        dn=unit(donor_map[src,3:6][idx]);dt=unit(donor_map[src,6:9][idx])
        db=np.cross(dn,dt)*donor_map[src,9:10][idx]
        # Meshy normals are OpenGL. Convert authored detail through object space
        # into the destination tangent frame; UE import flips green once.
        n=images['Normal'][src][idx]*2-1
        detail=dt*n[:,0,None]+db*n[:,1,None]
        tt=unit(tmap[dst,3:6]);tb=unit(tmap[dst,6:9])
        converted=unit(np.stack((np.sum(detail*tt,axis=-1),np.sum(detail*tb,axis=-1),n[:,2]),axis=-1))
        result['Normal'][dst]=converted*.5+.5
    all_cover|=used
    print('FROST_TRANSFER_BAKED',part,int(used.sum()),flush=True)
distance,nearest=ndi.distance_transform_edt(~all_cover,return_indices=True)
pad=(~all_cover)&(distance<=16)
for key,data in result.items():
    data[pad]=data[nearest[0][pad],nearest[1][pad]]
    Image.fromarray(np.uint8(np.clip(data,0,1)*255+.5)).save(OUT/('T_RuneSword_Frost_'+key+'.png'))
(P/'transfer-receipt.json').write_text(json.dumps({
    'source_base_color':str(source),'donor_mesh':'SM_FrostSword_Blade_factory',
    'target_uv_source':str(P.parent/'RuneSwordVisualPolish20260922/blade_guard_uv.npz'),
    'size':SIZE,'padding':16,'outputs':list(result),
    'source_material':'M_FrostCrystalSword_SeamlessBronze',
    'scope':'crystal blade surface only; bronze/leather excluded',
    'rendered':False,'gameplay_tested':False
},indent=2)+'\n',encoding='utf8')
