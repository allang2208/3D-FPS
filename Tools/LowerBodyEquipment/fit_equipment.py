"""Fit owned render garments to Jason, retaining topology and authored folds."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
import trimesh

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/LowerBodyEquipment20261003')
def read(k):return json.loads((ROOT/(k+'.json')).read_text())
target=read('body');skin=read('donor_skin')
tv=np.array(target['positions']);tt=np.array(target['triangles'],int)
tb=target['bones'];target_by_name={b['name']:b for b in tb}

def groups(d):
    bones=d['bones'];lookup=[]
    for b in bones:
        i=b['index'];g='torso'
        while i>=0:
            n=bones[i]['name']
            if n in [p+'_'+s for p in ['thigh','calf','foot','ball','hand','lowerarm','upperarm'] for s in ['l','r']]:g=n;break
            if n in ('head','neck_01','neck_02'):g='neck';break
            i=bones[i]['parent']
        lookup.append(g)
    out=[]
    for ws in d['weights']:
        sums={}
        for b,w in ws:sums[lookup[b]]=sums.get(lookup[b],0)+w
        out.append(max(sums,key=sums.get))
    return np.array(out)

def bind_warp(d):
    p=np.array(d['positions']);out=np.zeros_like(p);rows={}
    for vi,ws in enumerate(d['weights']):
        for b,w in ws:rows.setdefault(b,[]).append((vi,w))
    for bi,values in rows.items():
        b=d['bones'][bi]
        while b['name'] not in target_by_name and b['parent']>=0:b=d['bones'][b['parent']]
        t=target_by_name.get(b['name'],tb[0]);ids=np.array([v[0] for v in values]);w=np.array([v[1] for v in values])
        local=(p[ids]-b['position'])@np.linalg.inv(np.array(b['axes']))
        out[ids]+=(local@np.array(t['axes'])+t['position'])*w[:,None]
    return out

def neighbors(q,qg,p,pg,k):
    ids=np.empty((len(q),k),int);dist=np.empty((len(q),k))
    for g in np.unique(qg):
        qi=np.flatnonzero(qg==g);pi=np.flatnonzero(pg==g)
        if len(pi)<k:pi=np.arange(len(p))
        ds,ix=cKDTree(p[pi]).query(q[qi],k=k);ids[qi]=pi[ix];dist[qi]=ds
    w=1/np.maximum(dist,.12)**2;w/=w.sum(1)[:,None]
    return ids,w

tg=groups(target);sg=groups(skin);sv=bind_warp(skin)
surface_tris=tt[np.array(target['triangle_materials'])==2]
visible=np.unique(surface_tris);ni,nw=neighbors(sv,sg,tv[visible],tg[visible],5)
residual=(tv[visible][ni]*nw[:,:,None]).sum(1)-sv
residual*=np.minimum(1,7/np.maximum(np.linalg.norm(residual,axis=1),1e-8))[:,None]
si,sw=neighbors(sv,sg,sv,sg,16);residual=(residual[si]*sw[:,:,None]).sum(1)
centers=tv[surface_tris].mean(1);facegroups=tg[surface_tris[:,0]]
normals=np.zeros_like(tv);tn=np.cross(tv[tt[:,2]]-tv[tt[:,0]],tv[tt[:,1]]-tv[tt[:,0]])
for j in range(3):np.add.at(normals,tt[:,j],tn)
normals/=np.maximum(np.linalg.norm(normals,axis=1),1e-12)[:,None]

def project(points,pg):
    ids=np.empty((len(points),3),int);bary=np.empty((len(points),3))
    for group in np.unique(pg):
        qi=np.flatnonzero(pg==group);ti=np.flatnonzero(facegroups==group)
        if len(ti)<24:ti=np.arange(len(surface_tris))
        _,near=cKDTree(centers[ti]).query(points[qi],k=24)
        for start in range(0,len(qi),1024):
            rows=qi[start:start+1024];cand=surface_tris[ti[near[start:start+1024]]]
            cp=trimesh.triangles.closest_point(tv[cand].reshape(-1,3,3),np.repeat(points[rows],24,axis=0)).reshape(-1,24,3)
            best=np.argmin(np.linalg.norm(cp-points[rows,None,:],axis=2),axis=1)
            ids[rows]=cand[np.arange(len(rows)),best]
            bary[rows]=trimesh.triangles.points_to_barycentric(tv[ids[rows]],cp[np.arange(len(rows)),best])
    bary=np.clip(bary,0,1);bary/=bary.sum(1)[:,None]
    return ids,bary

fitted_meshes={}
for key in ['jeans','cargo','sneakers']:
    d=read(key);g=groups(d);v=bind_warp(d)
    ids,w=neighbors(v,g,sv,sg,10);fitted=v+(residual[ids]*w[:,:,None]).sum(1)
    native,cw=project(fitted,g);surface=(tv[native]*cw[:,:,None]).sum(1)
    normal=(normals[native]*cw[:,:,None]).sum(1);normal/=np.maximum(np.linalg.norm(normal,axis=1),1e-12)[:,None]
    clearance=np.sum((fitted-surface)*normal,axis=1)
    # Keep the original sole and pockets, correcting only contact clearance.
    fitted+=normal*np.maximum(0,.3-clearance)[:,None]
    weights=[]
    for src,blend in zip(native,cw):
        total={}
        for vi,mix in zip(src,blend):
            for bi,bw in target['weights'][vi]:total[bi]=total.get(bi,0)+bw*mix
        top=sorted(total.items(),key=lambda p:-p[1])[:8];den=sum(w for _,w in top)
        weights.append([[int(b),float(w/den)] for b,w in top if w>1e-5])
    d.update(positions=fitted.tolist(),weights=weights,bones=tb)
    (ROOT/(key+'_fitted.json')).write_text(json.dumps(d,separators=(',',':')))
    fitted_meshes[key]=fitted
    print('LOWER_BODY_FITTED',key,len(fitted),flush=True)

# Let the jeans drape outside the sneaker collar while preserving its hem.
# This neutral cuff also works with bare feet, so switching shoes needs no mesh swap.
shoe=fitted_meshes['sneakers'];shoe_tri=np.array(read('sneakers')['triangles'],int)
shoe_centers=shoe[shoe_tri].mean(1)
shoe_normals=np.cross(shoe[shoe_tri[:,2]]-shoe[shoe_tri[:,0]],shoe[shoe_tri[:,1]]-shoe[shoe_tri[:,0]])
shoe_normals/=np.maximum(np.linalg.norm(shoe_normals,axis=1),1e-12)[:,None]
for key in ['jeans','cargo']:
    p=fitted_meshes[key];ids=np.flatnonzero(p[:,2]<shoe[:,2].max()+3)
    if len(ids):
        _,near=cKDTree(shoe_centers).query(p[ids],k=24)
        cp=trimesh.triangles.closest_point(shoe[shoe_tri[near]].reshape(-1,3,3),np.repeat(p[ids],24,axis=0)).reshape(-1,24,3)
        best=np.argmin(np.linalg.norm(cp-p[ids,None,:],axis=2),axis=1)
        closest=cp[np.arange(len(ids)),best];n=shoe_normals[near[np.arange(len(ids)),best]]
        # Horizontal expansion retains the designed trouser length.
        n[:,2]=0;n/=np.maximum(np.linalg.norm(n,axis=1),1e-12)[:,None]
        distance=np.sum((p[ids]-closest)*n,axis=1)
        nearby=np.linalg.norm(p[ids]-closest,axis=1)<4
        p[ids]+=n*(np.minimum(3,np.maximum(0,.45-distance))*nearby)[:,None]
        d=read(key+'_fitted');d['positions']=p.tolist()
        (ROOT/(key+'_fitted.json')).write_text(json.dumps(d,separators=(',',':')))

# Split existing body sections by garment coverage; original UVs and weights
# stay intact. Per-item masks allow independent jeans/cargo/shoe combinations.
base=read('base');bv=np.array(base['positions']);bt=np.array(base['triangles'],int);bc=bv[bt].mean(1)
old=np.array(base['triangle_materials']);mask=np.zeros(len(bt),int)
eligible=np.isin(old,[3,4,7])
for bit,key in enumerate(['jeans','cargo']):
    p=fitted_meshes[key];waist=p[p[:,2]>np.quantile(p[:,2],.8)]
    angle=np.arctan2(waist[:,1],waist[:,0]);query=np.arctan2(bc[:,1],bc[:,0])
    top=np.full(len(bc),float(np.quantile(waist[:,2],.92))-.9)
    for ai in range(96):
        a=-np.pi+(ai+.5)*2*np.pi/96
        near=waist[np.abs(np.angle(np.exp(1j*(angle-a))))<.13,2]
        selected=np.abs(np.angle(np.exp(1j*(query-a))))<np.pi/96
        if len(near):top[selected]=np.quantile(near,.97)-.9
    covered=eligible&(bc[:,2]<top)
    for side,sign in [('l',1),('r',-1)]:
        leg=p[p[:,0]*sign>0];cuff=np.quantile(leg[:,2],.012)+1.1
        covered[(bc[:,0]*sign>0)&(bc[:,2]<cuff)]=False
    mask[covered]|=1<<bit
p=fitted_meshes['sneakers']
for side,sign in [('l',1),('r',-1)]:
    foot=np.array(target_by_name['foot_'+side]['position']);shoe=p[p[:,0]*sign>0]
    ankle=shoe[np.linalg.norm(shoe[:,:2]-foot[:2],axis=1)<7]
    height=float(np.quantile(ankle[:,2],.92)-1) if len(ankle) else foot[2]+1.5
    mask[eligible&(bc[:,0]*sign>0)&(bc[:,2]<height)]|=4
materials=list(base['materials']);regions=old.copy();origins={};covers={k:[] for k in fitted_meshes}
for original,m in sorted(set(zip(old.tolist(),mask.tolist()))):
    if m==0:continue
    new=len(materials);origins[str(new)]=original
    materials.append({'slot':'SkinLower_'+str(original)+'_'+str(m),'asset':materials[original]['asset']})
    regions[(old==original)&(mask==m)]=new
    for bit,key in enumerate(fitted_meshes):
        if m&(1<<bit):covers[key].append(new)
base.update(triangle_materials=regions.tolist(),materials=materials,section_origins=origins,covers=covers)
(ROOT/'base_fitted.json').write_text(json.dumps(base,separators=(',',':')))
print('LOWER_BODY_COVERAGE_AUTHORED',covers,flush=True)
