"""Restore original articulated armor binding and visible shell/liner spacing."""
import json
import numpy as np
from staff_thumb_steel_math import *
source=read('SourceAssets/ThirdPersonStaffThumbSteel20261009/original.json')
current=read('SourceAssets/ThirdPersonStaffThumbSteel20261009/production.json')
p=np.array(current['positions']);tri=np.array(current['triangles'],int);mids=np.array(current['triangle_materials'])
armor=np.unique(tri[mids==1]);lining=np.unique(tri[mids==0])
if np.intersect1d(armor,lining).size:raise RuntimeError('Shared steel/liner vertices need separate handling')
if source['triangles']!=current['triangles'] or source['triangle_materials']!=current['triangle_materials']:
    raise RuntimeError('Original and production topology differ')
original_names=[b['name'] for b in source['bones']];by_name={n:i for i,n in enumerate(names)}
repaired={**current,'weights':[list(ws) for ws in current['weights']]}
# Preserve topology/UVs and restore the authored rigid segments and continuous
# hand/wrist/thumb binding. The old liner binding has the same projection fault.
for i in range(len(p)):
    repaired['weights'][i]=[[by_name[original_names[b]],v] for b,v in source['weights'][i]]
# Diagnose the collapsed Jason layers before rebuilding the native-bound mesh.
cp,n,_=nearest_surface(p[armor],p,tri[mids==0])
signed=np.einsum('ij,ij->i',p[armor]-cp,n)
before=dict(armor_vertices=len(armor),liner_vertices=len(lining),buried_bind_vertices=int((signed<0).sum()),
    signed_clearance_percentiles_cm=np.percentile(signed,[0,5,50,95,100]).tolist())
print('STEEL_LAYER_INPUT',json.dumps(before),flush=True)
sp=np.array(source['positions']);bound=np.zeros_like(sp)
for bi,b in enumerate(source['bones']):
    rows=[(i,v) for i,ws in enumerate(source['weights']) for j,v in ws if j==bi]
    if not rows:continue
    rows=np.array(rows);ids=rows[:,0].astype(int)
    m=rest[b['name']]@np.linalg.inv(matrix(np.array(b['axes']).T,b['position']))
    bound[ids]+=(sp[ids]@m[:3,:3].T+m[:3,3])*rows[:,1,None]
p=bound.copy()
# The old residual field pulls some back-of-hand liner points more than 6 cm
# toward unrelated skin; it cannot be reused by the restored plate structure.
# Fit the clean native-bound glove directly, retaining its source skinning.
tp=np.array(target['positions']);tt=np.array(target['triangles'],int)
tt=tt[np.array(target['triangle_materials'])==2]
cp,normal,_=nearest_surface(p,tp,tt)
clearance=np.einsum('ij,ij->i',p-cp,normal)
margin=np.full(len(p),.10);margin[armor]=.32
delta=normal*np.maximum(margin-clearance,0)[:,None]
# Smooth only the fitting displacement, not the authored plate vertices.
for ids in (lining,armor):
    ds,near=cKDTree(p[ids]).query(p[ids],k=24)
    blend=np.exp(-ds**2/.5**2);blend/=blend.sum(1)[:,None]
    p[ids]+=(delta[ids][near]*blend[:,:,None]).sum(1)
# Rigid finger plates need enough stand-off for the liner's joint bulge in a
# closed grip. Translate each complete plate (including its rivets) in its
# dorsal direction; keep its gauge and shape, and mirror the fit to the left.
repaired['positions']=p.tolist()
grip=read('SourceAssets/ThirdPersonStaffGripFacing20261009/authored-grip.json')['variants']['false']
w=pose(grip);posed=skin(repaired,w)
plate_offsets={}
for digit in ('index','middle','ring','pinky'):
    for joint in ('01','02','03'):
        bone=f'{digit}_{joint}_r';bi=names.index(bone)
        ids=np.array([i for i in armor if len(repaired['weights'][i])==1 and repaired['weights'][i][0][0]==bi],int)
        if not len(ids):continue
        lp=(p[ids]-rest[bone][:3,3])@rest[bone][:3,:3]
        direction=np.mean(lp,axis=0);direction[0]=0;direction/=np.linalg.norm(direction)
        v=w[bone][:3,:3]@direction
        sample=posed[ids][::3]
        chosen=1.1
        for amount in np.arange(0,1.101,.05):
            cp,nn,_=nearest_surface(sample+v*amount,posed,tri[mids==0])
            gap=np.einsum('ij,ij->i',sample+v*amount-cp,nn)
            if np.percentile(gap,5)>=.09:
                chosen=float(amount);break
        plate_offsets[bone]=chosen
        for side in ('r','l'):
            bn=f'{digit}_{joint}_{side}';bj=names.index(bn)
            rows=np.array([i for i in armor if len(repaired['weights'][i])==1 and repaired['weights'][i][0][0]==bj],int)
            if not len(rows):continue
            rad=(p[rows]-rest[bn][:3,3])@rest[bn][:3,:3]
            dv=rad.mean(0);dv[0]=0;dv/=np.linalg.norm(dv)
            p[rows]+=chosen*(rest[bn][:3,:3]@dv)
before['rigid_plate_standoff_cm']=plate_offsets
print('PLATE_STANDOFF',plate_offsets,flush=True)
# Keep the continuous thumb guard clear of the soft liner at its two bends.
# This is a weighted radial shell offset, not an independent rigid thumb cap.
for i in armor:
    push=np.zeros(3)
    for bi,weight in repaired['weights'][i]:
        n=names[bi]
        if not n.startswith('thumb_'):continue
        point=(p[i]-rest[n][:3,3])@rest[n][:3,:3];point[0]=0
        push+=weight*(rest[n][:3,:3]@point/max(np.linalg.norm(point),1e-9))
    p[i]+=.18*push
repaired['positions']=p.tolist()
repaired['authoring']='Native bone frame transfer and source skinning restored on plate and liner; direct local Jason skin clearance fit; no residual-field projection'
(OUT/'steel-repaired.json').write_text(json.dumps(repaired,separators=(',',':')))
(OUT/'steel-layer-authoring.json').write_text(json.dumps(before,indent=2))
print('STEEL_LAYER_AUTHORED',flush=True)
