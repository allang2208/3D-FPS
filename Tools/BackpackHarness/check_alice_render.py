"""Requested ALICE facing/attribute checks, including deliberate side openings."""
import json
from collections import Counter
from pathlib import Path
import numpy as np
import trimesh

P=Path('D:/FPS3D/FPSGAME')
R=P/'SourceAssets/BackpacksReview20261021'
root=R/'FacingRepair20261022'
cube=json.loads((P/'SourceAssets/BackpackHarnessRebuild20261020/FacingRepair20261022/ue_cube_reference.json').read_text())
cv,ct=np.asarray(cube['positions']),np.asarray(cube['triangles'],int)
cn=np.cross(cv[ct[:,2]]-cv[ct[:,0]],cv[ct[:,1]]-cv[ct[:,0]])
if not np.all(np.einsum('ij,ij->i',cn,np.asarray(cube['normals']).mean(1))>0):
    raise RuntimeError('UE cube reference disagrees with facing convention')


def signatures(data,reverse=False):
    v=np.asarray(data['positions'],np.float32);uv=np.asarray(data['uv'],np.float32)
    result=Counter()
    for ti,face in enumerate(data['triangles']):
        corners=tuple((*v[vi],*uv[ti,ci]) for ci,vi in enumerate(face))
        if reverse:corners=corners[0],corners[2],corners[1]
        result[(data['triangle_materials'][ti],min(corners[i:]+corners[:i] for i in range(3)))]+=1
    return result


report={'reference':cube['asset'],'ue_front_face':'cross_e2_e1','phases':{},'preservation':[]}
for phase in ('Before','After'):
    rows=[]
    for path in sorted((root/phase).glob('*_lod*.json')):
        d=json.loads(path.read_text());v=np.asarray(d['positions']);t=np.asarray(d['triangles'],int)
        n=np.asarray(d['normals']);m=np.asarray(d['triangle_materials'])
        fn=np.cross(v[t[:,2]]-v[t[:,0]],v[t[:,1]]-v[t[:,0]])
        lengths=np.linalg.norm(fn,axis=1);fn/=np.maximum(lengths[:,None],1e-12)
        wrong=(lengths>1e-8)&(np.einsum('ij,ij->i',fn,n.mean(1))<-.0001)
        row={'kind':d['kind'],'lod':d['lod'],'triangles':len(t),'revision':d['revision'],
             'opposed_to_ue_normals':int(wrong.sum()),'materials':[]}
        for mi,material in enumerate(d['materials']):
            row['materials'].append({'slot':material['slot'],'triangles':int(sum(m==mi)),
                                     'opposed_to_ue_normals':int(sum(wrong&(m==mi)))})
        rows.append(row)
        if phase=='After':
            before=json.loads((root/'Before'/path.name).read_text())
            report['preservation'].append({'kind':d['kind'],'lod':d['lod'],
                'same_geometry_uv_materials_reversed_corners':signatures(d)==signatures(before,reverse=True),
                'same_material_slots':d['materials']==before['materials']})
        print('ALICE_FRONT_FACE',phase,d['kind'],len(t),'opposed',int(wrong.sum()),flush=True)
    report['phases'][phase]=rows

# Probe the already-authored recesses on actual saved canvas/lining. Do not
# demand a closed-mouth mesh: the side-pocket openings were requested by user.
source=json.loads((R/'alice_source.json').read_text());sv=np.asarray(source['positions'])
centre=(sv.min(0)+sv.max(0))/2
d=json.loads((root/'After/render_lod0.json').read_text());v=np.asarray(d['positions']);t=np.asarray(d['triangles'],int)
mesh=trimesh.Trimesh(v,t,process=False);fn=np.cross(v[t[:,2]]-v[t[:,0]],v[t[:,1]]-v[t[:,0]])
fn/=np.maximum(np.linalg.norm(fn,axis=1)[:,None],1e-12)
report['side_pocket_samples']=[]
for side in (-1,1):
    for y in (-.102,-.026):
        z=-.015+.0025*np.sin(np.pi*(y+.114)/.102)
        start=(np.asarray([side*.30,y,z])-centre)*[100,100,-100];direction=np.asarray([-side,0,0])
        face=int(mesh.ray.intersects_first([start],[direction])[0])
        report['side_pocket_samples'].append({'side':side,'y':y,'surface_hit':face>=0,
            'front_facing':bool(face>=0 and fn[face]@direction<0)})
receipt=json.loads((root/'After/receipt.json').read_text())
report['lod_count']=receipt['lod_count'];report['nanite_settings']=receipt['nanite_settings']
report['passed']=bool(len(report['phases']['After'])==2*receipt['lod_count'] and
    all(r['opposed_to_ue_normals']==0 for r in report['phases']['After']) and
    all(r['same_geometry_uv_materials_reversed_corners'] and r['same_material_slots'] for r in report['preservation']) and
    all(s['surface_hit'] and s['front_facing'] for s in report['side_pocket_samples']))
(root/'checks.json').write_text(json.dumps(report,indent=2))
print('ALICE_RENDER_CHECK_COMPLETE',report['passed'],report['preservation'],report['side_pocket_samples'],flush=True)
if not report['passed']:raise SystemExit(1)
