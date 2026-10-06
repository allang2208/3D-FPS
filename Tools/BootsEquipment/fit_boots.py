"""Author Jason boots, trouser cuff variants and exact body coverage sections."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
import trimesh

P=Path('D:/FPS3D/FPSGAME')
R=P/'SourceAssets/BootsEquipment20261004'
PREVIOUS=P/'SourceAssets/LowerBodyEquipment20261003'
def read(name, root=R): return json.loads((root/(name+'.json')).read_text())
def write(name, data): (R/(name+'.json')).write_text(json.dumps(data,separators=(',',':')))
target=read('body',PREVIOUS);skin=read('donor_skin',PREVIOUS)
tv=np.array(target['positions']);tt=np.array(target['triangles'],int)
tb=target['bones'];target_by_name={b['name']:b for b in tb}

def groups(data):
    bones=data['bones'];lookup=[]
    parts={p+'_'+s for p in ['thigh','calf','foot','ball','hand','lowerarm','upperarm'] for s in ['l','r']}
    for bone in bones:
        index=bone['index'];group='torso'
        while index>=0:
            name=bones[index]['name']
            if name in parts:group=name;break
            if name in ('head','neck_01','neck_02'):group='neck';break
            index=bones[index]['parent']
        lookup.append(group)
    out=[]
    for weights in data['weights']:
        sums={}
        for bone,weight in weights:sums[lookup[bone]]=sums.get(lookup[bone],0)+weight
        out.append(max(sums,key=sums.get))
    return np.array(out)

def bind_warp(data):
    positions=np.array(data['positions']);out=np.zeros_like(positions);rows={}
    for vi,weights in enumerate(data['weights']):
        for bone,weight in weights:rows.setdefault(bone,[]).append((vi,weight))
    for bi,values in rows.items():
        bone=data['bones'][bi]
        while bone['name'] not in target_by_name and bone['parent']>=0:bone=data['bones'][bone['parent']]
        native=target_by_name.get(bone['name'],tb[0])
        ids=np.array([v[0] for v in values]);weight=np.array([v[1] for v in values])
        local=(positions[ids]-bone['position'])@np.linalg.inv(np.array(bone['axes']))
        out[ids]+=(local@np.array(native['axes'])+native['position'])*weight[:,None]
    return out

def neighbors(query,qgroups,points,pgroups,k):
    ids=np.empty((len(query),k),int);dist=np.empty((len(query),k))
    for group in np.unique(qgroups):
        qi=np.flatnonzero(qgroups==group);pi=np.flatnonzero(pgroups==group)
        if len(pi)<k:pi=np.arange(len(points))
        distances,indices=cKDTree(points[pi]).query(query[qi],k=k)
        ids[qi]=pi[indices];dist[qi]=distances
    weights=1/np.maximum(dist,.12)**2;weights/=weights.sum(1)[:,None]
    return ids,weights

tg=groups(target);sg=groups(skin);sv=bind_warp(skin)
surface_tris=tt[np.array(target['triangle_materials'])==2]
visible=np.unique(surface_tris)
ids,weights=neighbors(sv,sg,tv[visible],tg[visible],5)
residual=(tv[visible][ids]*weights[:,:,None]).sum(1)-sv
residual*=np.minimum(1,7/np.maximum(np.linalg.norm(residual,axis=1),1e-8))[:,None]
ids,weights=neighbors(sv,sg,sv,sg,16);residual=(residual[ids]*weights[:,:,None]).sum(1)
centers=tv[surface_tris].mean(1);facegroups=tg[surface_tris[:,0]]
normals=np.zeros_like(tv)
tn=np.cross(tv[tt[:,2]]-tv[tt[:,0]],tv[tt[:,1]]-tv[tt[:,0]])
for j in range(3):np.add.at(normals,tt[:,j],tn)
normals/=np.maximum(np.linalg.norm(normals,axis=1),1e-12)[:,None]

def project(points,pgroups):
    indices=np.empty((len(points),3),int);bary=np.empty((len(points),3))
    for group in np.unique(pgroups):
        qi=np.flatnonzero(pgroups==group);ti=np.flatnonzero(facegroups==group)
        if len(ti)<24:ti=np.arange(len(surface_tris))
        _,near=cKDTree(centers[ti]).query(points[qi],k=24)
        for start in range(0,len(qi),1024):
            rows=qi[start:start+1024];candidates=surface_tris[ti[near[start:start+1024]]]
            cp=trimesh.triangles.closest_point(tv[candidates].reshape(-1,3,3),np.repeat(points[rows],24,axis=0)).reshape(-1,24,3)
            best=np.argmin(np.linalg.norm(cp-points[rows,None,:],axis=2),axis=1)
            indices[rows]=candidates[np.arange(len(rows)),best]
            bary[rows]=trimesh.triangles.points_to_barycentric(tv[indices[rows]],cp[np.arange(len(rows)),best])
    bary=np.clip(bary,0,1);bary/=bary.sum(1)[:,None]
    return indices,bary

boots=read('boots');bg=groups(boots);bound=bind_warp(boots)
ids,weights=neighbors(bound,bg,sv,sg,10)
fitted=bound+(residual[ids]*weights[:,:,None]).sum(1)
native,blend=project(fitted,bg)
surface=(tv[native]*blend[:,:,None]).sum(1)
normal=(normals[native]*blend[:,:,None]).sum(1)
normal/=np.maximum(np.linalg.norm(normal,axis=1),1e-12)[:,None]
clearance=np.sum((fitted-surface)*normal,axis=1)
fitted+=normal*np.maximum(0,.3-clearance)[:,None]
weights=[]
for source,mix in zip(native,blend):
    total={}
    for vi,amount in zip(source,mix):
        for bi,bw in target['weights'][vi]:total[bi]=total.get(bi,0)+bw*amount
    top=sorted(total.items(),key=lambda pair:-pair[1])[:8]
    top=[(bi,w) for bi,w in top if w>1e-5];den=sum(w for _,w in top)
    weights.append([[int(bi),float(w/den)] for bi,w in top])
boots.update(positions=fitted.tolist(),weights=weights,bones=tb)
write('boots_fitted',boots)

# Cuffs drape outside the boot upper. Only the Boots combination uses these
# variants; accepted barefoot/sneaker trousers retain their original geometry.
boot_tri=np.array(boots['triangles'],int);boot_centers=fitted[boot_tri].mean(1)
boot_normals=np.cross(fitted[boot_tri[:,2]]-fitted[boot_tri[:,0]],fitted[boot_tri[:,1]]-fitted[boot_tri[:,0]])
boot_normals/=np.maximum(np.linalg.norm(boot_normals,axis=1),1e-12)[:,None]
for key in ['jeans','cargo']:
    pants=read(key);positions=np.array(pants['positions'])
    rows=np.flatnonzero(positions[:,2]<fitted[:,2].max()+3)
    _,near=cKDTree(boot_centers).query(positions[rows],k=24)
    cp=trimesh.triangles.closest_point(fitted[boot_tri[near]].reshape(-1,3,3),np.repeat(positions[rows],24,axis=0)).reshape(-1,24,3)
    best=np.argmin(np.linalg.norm(cp-positions[rows,None,:],axis=2),axis=1)
    closest=cp[np.arange(len(rows)),best];norm=boot_normals[near[np.arange(len(rows)),best]].copy()
    norm[:,2]=0;norm/=np.maximum(np.linalg.norm(norm,axis=1),1e-12)[:,None]
    distance=np.sum((positions[rows]-closest)*norm,axis=1)
    nearby=np.linalg.norm(positions[rows]-closest,axis=1)<5
    positions[rows]+=norm*(np.minimum(3,np.maximum(0,.45-distance))*nearby)[:,None]
    pants['positions']=positions.tolist();write(key+'_fitted',pants)

# Split only covered lower-leg skin, keeping all existing section IDs stable.
base=read('base');vertices=np.array(base['positions']);tri=np.array(base['triangles'],int)
mid=vertices[tri].mean(1);old=np.array(base['triangle_materials'])
body_groups=groups(base)[tri[:,0]]
covered=np.zeros(len(tri),bool);collar_heights={}
for side,sign in [('l',1),('r',-1)]:
    foot=np.array(target_by_name['foot_'+side]['position']);shoe=fitted[fitted[:,0]*sign>0]
    ankle=shoe[np.linalg.norm(shoe[:,:2]-foot[:2],axis=1)<8]
    height=float(np.quantile(ankle[:,2],.96)-1)
    collar_heights[side]=height
    covered|=np.isin(body_groups,['calf_'+side,'foot_'+side,'ball_'+side])&(mid[:,0]*sign>0)&(mid[:,2]<height)
materials=list(base['materials']);regions=old.copy();origins={};covers=[]
for original in sorted(set(old[covered].tolist())):
    matching=old==original
    if np.all(covered[matching]):covers.append(original);continue
    section=len(materials);origins[str(section)]=original
    materials.append({'slot':'SkinBoots_'+str(original),'asset':materials[original]['asset']})
    regions[matching&covered]=section;covers.append(section)
base.update(triangle_materials=regions.tolist(),materials=materials,section_origins=origins,boots_covers=covers)
write('base_fitted',base)
write('fitting_receipt',{'vertices':len(fitted),'triangles':len(boot_tri),'collar_heights':collar_heights,'boots_covers':covers,'section_origins':origins})
print('BOOTS_FIT_AUTHORED',len(fitted),len(boot_tri),covers,flush=True)
