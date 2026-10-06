"""Diagnose the reported RSH inspect discontinuity and sleeve distortion."""
import json, sys, math, hashlib
from pathlib import Path
import numpy as np
from mathutils import Matrix, Vector, Quaternion
O=Path(__file__).parent;S=O.parent
sys.path.insert(0,str(S/'RSH12InspectGrip20261004'))
from grip_scene import load,pose
rig,D,_,meta=load()
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
reflect=Matrix.Diagonal((1,-1,1,1))
to_ue=(rig.matrix_world.inverted()@reflect@Matrix.Diagonal((.01,.01,.01,1))).inverted()
shirt=json.loads((S/'ChainmailCameraClearance20260929/DW715/LOD0.json').read_text())
disk=S.parent/'Content/Characters/ModularOutfit20260924/ChainmailCameraClearance20260929/DW715/SK_DW715_Chainmail.uasset'
report={'garment_snapshot_current':hashlib.sha256(disk.read_bytes()).hexdigest()==shirt['asset_sha256'],'profiles':{}}
ids=[i for i,w in enumerate(shirt['weights']) if sum(v for n,v in w.items() if n.endswith('_l'))>.5]
points=np.array([[*shirt['positions'][i],1.] for i in ids]);weights=[shirt['weights'][i] for i in ids]
used=sorted({n for w in weights for n in w})
bound={}
for n in used:
    tr=shirt['rest'][n];m=Matrix.LocRotScale(Vector(tr['p']),Quaternion((tr['q'][3],*tr['q'][:3])),Vector(tr['s']))
    bound[n]=points@np.array(m.inverted()).T
ww={n:np.array([w.get(n,0.) for w in weights])[:,None] for n in used}
remap={old:i for i,old in enumerate(ids)}
faces=np.array([[remap[i] for i in f] for f in shirt['triangles'] if all(i in remap for i in f)])
edges=np.unique(np.sort(np.concatenate((faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]])),axis=1),axis=0)
edge_rest=np.linalg.norm(points[edges[:,0],:3]-points[edges[:,1],:3],axis=1)
mask=edge_rest>.15;edges=edges[mask];edge_rest=edge_rest[mask]
profiles=[('revised',O/'profile.json')] if '--after' in sys.argv else [('current',S/'RSH12Foregrips20261004/Profiles/angled.json'),('previous',S/'RSH12ResonanceWrist20261005/Before/angled.json')]
for label,path in profiles:
    profile=json.loads(path.read_text());last=None;lastskin=None;rows=[];jumps=[];skinsteps=[]
    for k,sample in enumerate(D['clips']['inspect']['samples']):
        p=pose(rig,D,profile,'inspect',sample)
        world={n:to_ue@m@reflect for n,m in p.items()}
        posed=sum((bound[n]@np.array(world[n]).T)*ww[n] for n in used)[:,:3]
        stretch=np.linalg.norm(posed[edges[:,0]]-posed[edges[:,1]],axis=1)/edge_rest
        row={'frame':k,'t':sample['time'],'edge_ratio_p99':float(np.quantile(stretch,.99)),'edge_ratio_max':float(stretch.max())}
        if last is not None:
            for n in ('clavicle_l','upperarm_l','lowerarm_l','hand_l','upperarm_twist_01_l','upperarm_twist_02_l','lowerarm_twist_01_l','lowerarm_twist_02_l','hand_r','WPN_root'):
                q=p[n].to_quaternion();oldq=last[n].to_quaternion();angle=math.degrees(q.rotation_difference(oldq).angle);angle=min(angle,360-angle)
                jumps.append(dict(frame=k,bone=n,degrees=angle,centimeters=(p[n].translation-last[n].translation).length*100))
            skinsteps.append(dict(frame=k,max_cm=float(np.linalg.norm(posed-lastskin,axis=1).max())))
        rows.append(row);last=p;lastskin=posed
    report['profiles'][label]={'rotation_peaks':sorted(jumps,key=lambda r:-r['degrees'])[:16],
        'position_peaks':sorted(jumps,key=lambda r:-r['centimeters'])[:10],
        'sleeve_step_peaks':sorted(skinsteps,key=lambda r:-r['max_cm'])[:8],
        'sleeve_stretch_peaks':sorted(rows,key=lambda r:-r['edge_ratio_max'])[:8]}
(O/('diagnosis-after.json' if '--after' in sys.argv else 'diagnosis.json')).write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report,indent=2),flush=True)
