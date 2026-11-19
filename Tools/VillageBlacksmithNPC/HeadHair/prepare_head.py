"""Fit the commissioned original face to Jason R4 and join it to its real body border."""
from pathlib import Path
import gzip
from io import BytesIO
import json
import math
import struct
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

PROJECT=Path(__file__).resolve().parents[3]
ROOT=PROJECT/'SourceAssets/VillageBlacksmithNPC20261118'
OUT=ROOT/'HeadHair'
TEX=OUT/'Textures'
BASE=PROJECT/'SourceAssets/JasonStrong20261117'
COMBINED=ROOT/'Meshy/CombinedR1/head.glb'
SOURCE=COMBINED if COMBINED.exists() else ROOT/'Meshy/head.glb'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def unit(v):
    return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-10)

def transfer(weights):
    dst={}
    for index,weight in weights:
        bone=body_indices[index]
        dst[bone]=dst.get(bone,0)+weight
    return dst

def interpolate(a,b,t):
    c={k:(1-t)*v for k,v in a.items()}
    for k,v in b.items():c[k]=c.get(k,0)+v*t
    pairs=sorted(c.items(),key=lambda p:-p[1])[:8]
    s=sum(v for k,v in pairs)
    return {k:v/s for k,v in pairs if v/s>.00001}

def crop(p,n,uv,w,f,cut,keep_above):
    """Clip intersected triangles without reprojecting any original face UVs or normals."""
    inside=p[:,2]>=cut if keep_above else p[:,2]<=cut
    keep=inside[f].all(axis=1)
    orig=np.flatnonzero(inside)
    reindex=np.full(len(inside),-1,np.int64);reindex[orig]=np.arange(len(orig))
    op=p[orig].tolist();on=n[orig].tolist();ou=uv[orig].tolist();ow=[w[i] for i in orig]
    of=reindex[f[keep]].tolist();cross={};edges=[]
    def on_plane(i,j):
        k=tuple(sorted((int(i),int(j))))
        if k not in cross:
            t=(cut-p[i,2])/(p[j,2]-p[i,2])
            q=p[i]*(1-t)+p[j]*t;q[2]=cut
            cross[k]=len(op);op.append(q.tolist());on.append(unit(n[i]*(1-t)+n[j]*t).tolist())
            ou.append((uv[i]*(1-t)+uv[j]*t).tolist())
            ow.append(interpolate(w[i],w[j],t))
        return cross[k]
    for tri in f[inside[f].any(axis=1)&~keep]:
        polygon=[];edge=[]
        for a,b in zip(tri,np.roll(tri,-1)):
            if inside[a]:polygon.append(int(reindex[a]))
            if inside[a]!=inside[b]:
                q=on_plane(a,b);polygon.append(q);edge.append(q)
        if len(edge)==2:edges+=edge
        of.extend([[polygon[0],polygon[i],polygon[i+1]] for i in range(1,len(polygon)-1)])
    return np.array(op),np.array(on),np.array(ou),ow,np.array(of),edges

def ring(points,ids,center):
    # UV seam duplicates share a geometric vertex, and produce only one contour point.
    unique={tuple(np.round(points[i],4)):i for i in ids}
    ix=np.fromiter(unique.values(),int)
    angles=np.arctan2(points[ix,1]-center[1],points[ix,0]-center[0])
    order=np.argsort(angles);return angles[order],ix[order]

def extract_original_textures():
    with SOURCE.open('rb') as stream:
        stream.seek(12);size=struct.unpack('<I',stream.read(4))[0];stream.seek(20)
        gltf=json.loads(stream.read(size));base=28+size
        mat=gltf['materials'][0];pbr=mat['pbrMetallicRoughness']
        maps=[('BC',pbr['baseColorTexture']),('N',mat.get('normalTexture')),('R',pbr.get('metallicRoughnessTexture'))]
        for suffix,texture in maps:
            if texture is None:continue
            image_id=gltf['textures'][texture['index']]['source']
            view=gltf['bufferViews'][gltf['images'][image_id]['bufferView']]
            stream.seek(base+view.get('byteOffset',0))
            image=Image.open(BytesIO(stream.read(view['byteLength']))).convert('RGB')
            if suffix=='R':image=image.getchannel('G')
            image.save(TEX/f'T_Smith_Face_{suffix}.png')

def nape_rise(p):
    if SOURCE!=COMBINED:return np.zeros(len(p))
    front=np.clip((p[:,1]+1.2)/7.4,0,1)
    return 4.02*(1-front*front*(3-2*front))

def neck_section(points,normals,uv,weights,faces,cut,above):
    # Both sides of the join follow the higher nape. Keep the lower beard under the chin.
    warped=points.copy()
    warped[:,2]-=nape_rise(points)
    p,n,u,w,f,ring_ids=crop(warped,normals,uv,weights,faces,cut,above)
    p[:,2]+=nape_rise(p)
    return p,n,u,w,f,ring_ids

def sample_nose(raw):
    # The nose is the front-most central surface, bounded above by the brow and below by the mouth.
    top=raw[:,2].max();floor=raw[:,2].min()
    span=top-floor;center_x=np.median(raw[(raw[:,2]>floor+.6*span),0])
    strip=raw[(abs(raw[:,0]-center_x)<.052*span)&(raw[:,2]>floor+.20*span)&(raw[:,2]<floor+.72*span)]
    tip=strip[np.argmax(strip[:,1])]
    return top,tip

def sample_linear_color(path,uv):
    tex=np.asarray(Image.open(path).convert('RGB'))
    row=np.clip((uv[:,1]*tex.shape[0]).astype(int),0,tex.shape[0]-1)
    col=np.clip((uv[:,0]*tex.shape[1]).astype(int),0,tex.shape[1]-1)
    srgb=np.median(tex[row,col],axis=0)/255.
    return np.where(srgb<=.04045,srgb/12.92,((srgb+.055)/1.055)**2.4)

if __name__=='__main__':
    native=read(BASE/'R3_ArmsRefined/head_source.json')
    body=read(BASE/'R3_ArmsRefined/AnatomyReview/derived_saved_mesh.json')
    names={b['name']:b['index'] for b in body['bones']}
    body_indices={}
    for b in native['bones']:
        a=b
        while a['name'] not in names:a=native['bones'][a['parent']]
        body_indices[b['index']]=names[a['name']]
    np0=np.array(native['positions'])+[0,0,4.5];nw=[transfer(v) for v in native['weights']]
    skin=np.array(native['triangle_materials'])==0
    ntri=np.array(native['triangles'])[skin]
    nri=np.asarray(native['triangle_uvs'])[skin]
    native_norm=np.zeros_like(np0)
    q=np0[ntri];norm=-np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0])
    for k in range(3):np.add.at(native_norm,ntri[:,k],norm)
    native_norm=unit(native_norm)
    # Maintain Jason collar UV seams while keeping adjacent original neck weights.
    corners=np.column_stack((ntri.ravel(),nri.reshape(-1,2)))
    unique,back=np.unique(corners,axis=0,return_inverse=True)
    ids=unique[:,0].astype(int);p,n,uv,w,tri,li=neck_section(np0[ids],native_norm[ids],unique[:,1:],[nw[i] for i in ids],back.reshape(-1,3),155.30,False)
    center=np.median(p[np.asarray(li)],axis=0)
    la,lr=ring(p,li,center)
    # Direct vertex/normal/UV transfer from the Meshy GLB, with a uniform fit above the lower neck.
    extract_original_textures()
    surface=np.load(OUT/'game_surface.npz')
    raw=surface['p']
    crown=181.0 if SOURCE==COMBINED else 179.7
    top,tip=sample_nose(raw);scale=float((crown-164.90)/(top-tip[2]))
    mp=(raw-tip)*scale+[0,13.20,164.90]
    mn=surface['n'];mu=surface['uv']
    hit=cKDTree(np0).query(mp)[1]
    mw=[nw[i] if z<162 else {names['head']:1.} for i,z in zip(hit,mp[:,2])]
    # A bust cut can vary by Meshy iteration; select a continuous neck section beneath the jaw.
    cut=max(155.65,float(np.min(mp[:,2]))+.35)
    if cut>157.6:raise ValueError(f'Meshy crop ends at {cut:.2f} cm; the source needs a longer neck.')
    x,nx,u,wx,fx,hi=neck_section(mp,mn,mu,mw,surface['tri'],cut,True)
    ha,hr=ring(x,hi,center)
    if not len(la) or not len(ha):raise ValueError('Missing neck contour')
    theta=np.arctan2(x[:,1]-center[1],x[:,0]-center[0])
    targ=np.stack([np.interp(theta,la,p[lr,k],period=math.tau) for k in (0,1)],axis=1)
    s=np.clip((cut+nape_rise(x)+2.15-x[:,2])/2.15,0,1);s=s*s*(3-2*s)
    x[:,:2]=(1-s[:,None])*x[:,:2]+s[:,None]*targ
    # Blend the lower edge's shading and deformation into the same native shoulder border.
    changing=np.flatnonzero(s>0)
    nearest=cKDTree(p[lr,:2]).query(x[changing,:2])[1]
    for vi,match in zip(changing,nearest):
        near=lr[match]
        wx[vi]=interpolate(wx[vi],w[near],s[vi])
        nx[vi]=unit(nx[vi]*(1-s[vi])+n[near]*s[vi])
    offset=len(x)
    # Connect both independent rings with outward triangles. Bridge UVs use the adjacent native neck.
    # On the neck's native atlas seam, choose the nearest native corner on that side.
    near=cKDTree(p[lr,:2]).query(x[hr,:2])[1]
    uv_neck=uv[lr[near]]
    face_color=sample_linear_color(TEX/'T_Smith_Face_BC.png',u[hr])
    neck_color=sample_linear_color(ROOT/'BodyOutfit/Textures/T_Smith_Skin_head_BC.png',uv[lr])
    neck_ratio=np.clip(face_color/np.maximum(neck_color,.005),.36,2.8)
    bp=np.concatenate([x[hr],p[lr]]);bu=np.concatenate([uv_neck,uv[lr]])
    bn=unit(np.column_stack([bp[:,:2]-center[:2],np.zeros(len(bp))]))
    bw=[wx[i] for i in hr]+[w[i] for i in lr]
    i=j=0;bridge=[]
    while i<len(hr) or j<len(lr):
        an=ha[(i+1)%len(hr)]+(math.tau if i+1>=len(hr) else 0)
        bnxt=la[(j+1)%len(lr)]+(math.tau if j+1>=len(lr) else 0)
        if i<len(hr) and (j>=len(lr) or an<bnxt):
            t=[i%len(hr),(i+1)%len(hr),len(hr)+j%len(lr)];i+=1
        else:
            t=[i%len(hr),len(hr)+(j+1)%len(lr),len(hr)+j%len(lr)];j+=1
        a,b,c=bp[t]
        if np.dot(np.cross(b-a,c-a),np.mean(bn[t],axis=0))>0:t=t[::-1]
        bridge.append(t)
    fp=np.concatenate([x,p,bp]);fn=np.concatenate([nx,n,bn]);fu=np.concatenate([u,uv,bu])
    ff=np.concatenate([fx,tri+offset,np.asarray(bridge)+offset+len(p)])
    fw=wx+w+bw;mids=[0]*len(fx)+[1]*(len(tri)+len(bridge))
    data={'p':np.round(fp,6).tolist(),'n':np.round(fn,7).tolist(),'uv':np.round(fu,7).tolist(),'tri':ff.tolist(),
          'w':[[[k,v] for k,v in weights.items()] for weights in fw],'m':mids}
    with gzip.open(OUT/'face.json.gz','wt',encoding='utf8',compresslevel=3) as f:json.dump(data,f,separators=(',',':'))
    np.savez_compressed(OUT/'surface.npz',p=x,tri=fx)
    (OUT/'fit.json').write_text(json.dumps({'source':SOURCE.relative_to(ROOT).as_posix(),'integrated_meshy_hair':SOURCE==COMBINED,'uniform_scale_cm':scale,'source_nose_xyz':tip.tolist(),'target_nose':[0,13.2,164.9],'crown_cm':crown,'face_triangles':len(fx),'native_neck_triangles':len(tri),'neck_transition_cm':[155.30,cut+2.15],'neck_tint_upper_linear':neck_ratio.tolist(),'rigid_head_index':names['head'],'native_skeleton':body['skeleton']},indent=2))
