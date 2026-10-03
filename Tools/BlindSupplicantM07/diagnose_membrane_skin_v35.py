"""Source-only diagnosis of the reported lower membrane skin distortion."""
import json
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OUT=ROOT/'MembraneSkinV35'
source=json.loads((OUT/'current_ue_source.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'BodyMotionV18/Proxy/M07_Original_GillContacts_V18.blend'))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
names=[b.name for b in rig.data.bones]
def mat(t):return np.asarray(Matrix.LocRotScale(Vector(t['p']),Quaternion(t['q']),Vector(t['s'])))
reference=np.asarray([mat(source['reference'][n]) for n in names])
inv=np.linalg.inv(reference)
clips={role:[np.asarray([mat(s['bones'][n]) for n in names])@inv for s in r['samples']] for role,r in source['clips'].items()}
meshes=[]
repaired='--repaired' in sys.argv
solution=np.load(OUT/'skin_solution.npz') if repaired else None
for label in range(7):
    obj=bpy.data.objects['M07_OriginalBody_Display' if not label else f'M07_OriginalGill_{label:02d}_Display']
    p=np.asarray([v.co[:] for v in obj.data.vertices],float)
    p[:,1]*=-1 # FBX reference mesh conversion to UE coordinates.
    f=np.asarray([list(t.vertices) for t in obj.data.polygons])
    w=np.zeros((len(p),len(names)))
    groups={g.index:names.index(g.name) for g in obj.vertex_groups if g.name in names}
    for v in obj.data.vertices:
        for g in v.groups:
            if g.group in groups:w[v.index,groups[g.group]]=g.weight
    if repaired:
        a,b=solution['offsets'][label:label+2]
        w=solution['weights'][a:b]
    meshes.append((p,f,w))
report={'panels':[],'seams':[],'source_scope':'Requested diagnosis of authored weights and actual UE clip transforms; no game run'}
for label,(p,f,w) in enumerate(meshes):
    if not label:continue
    e=np.unique(np.sort(np.concatenate((f[:,[0,1]],f[:,[1,2]],f[:,[2,0]])),axis=1),axis=0)
    length=np.linalg.norm(p[e[:,1]]-p[e[:,0]],axis=1)
    mask=(length>.05)&(p[e].mean(axis=1)[:,2]<200)
    own=[i for i,n in enumerate(names) if n.startswith(f'gill_{label:02d}_')]
    body=[i for i,n in enumerate(names) if not n.startswith('gill_')]
    lower=p[:,2]<170
    body_mass=w[:,body].sum(axis=1)
    neighbor_mass=w.sum(axis=1)-body_mass-w[:,own].sum(axis=1)
    row={'panel':label,'vertices':len(p),'bbox':[p.min(axis=0).tolist(),p.max(axis=0).tolist()],
         'lower_body_spill':int((lower&(body_mass>.01)).sum()),'lower_neighbor_gill_mass':int((lower&(neighbor_mass>.01)).sum()),
         'lower_total':int(lower.sum()),'worst':[]}
    for role,poses in clips.items():
        worst=(0,None)
        for frame,m in enumerate(poses):
            homogeneous=np.c_[p,np.ones(len(p))]
            skin=np.einsum('vi,ijk,vk->vj',w,m,homogeneous)[:,:3]
            changed=np.linalg.norm(skin[e[:,1]]-skin[e[:,0]],axis=1)
            ratio=changed/np.maximum(length,1.e-10)
            index=np.argmax(np.where(mask,ratio,0))
            if ratio[index]>worst[0]:
                v=e[index]
                worst=(float(ratio[index]),dict(frame=frame,edge=v.tolist(),positions=p[v].tolist(),length_cm=float(length[index]),deformed_cm=float(changed[index]),weights=[{names[i]:round(float(w[j,i]),4) for i in np.flatnonzero(w[j]>.0001)} for j in v],
                    edges_over_150percent=int((mask&(ratio>1.5)).sum())))
        row['worst'].append({'role':role,'ratio':worst[0],**worst[1]})
    report['panels'].append(row)
    print('PANEL',label,'lower body',row['lower_body_spill'],'neighbor',row['lower_neighbor_gill_mass'],[(r['role'],round(r['ratio'],2),r['edges_over_150percent']) for r in row['worst']],flush=True)
bins={}
for label,(p,f,w) in enumerate(meshes):
    for i,point in enumerate(p):
        key=tuple(np.round(point,3))
        if key in bins:
            prev,j=bins[key]
            delta=float(np.abs(meshes[prev][2][j]-w[i]).sum())
            if delta>.05 and (label or prev):report['seams'].append(dict(label=label,other=prev,vertex=i,other_vertex=j,delta=delta,p=point.tolist()))
        else:bins[key]=(label,i)
report['gill_reference']={n:source['reference'][n] for n in names if n.startswith('gill_')}
(OUT/('repaired_source_diagnosis.json' if repaired else 'source_diagnosis.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SEAM_CONFLICTS',len(report['seams']),flush=True)
