"""Read native runtime-layer pose samples; report return continuity and grip lock."""
from pathlib import Path
import json, pickle, sys
import numpy as np
from scipy.spatial.transform import Rotation as R

r=Path(__file__).resolve().parent
names=pickle.load(open(r/'current.pkl','rb'))['names']
results={}
for label in sys.argv[1:]:
    cases={}
    for folder in sorted((r/label).iterdir()):
        if not (folder/'review.json').exists():continue
        j=json.loads((folder/'review.json').read_text());n=j['bone_count']
        a=np.fromfile(folder/'poses.f32',np.float32).reshape(-1,4+n*7)
        t,source=a[:,0],a[:,1];w=a[:,4:].reshape(-1,n,7)
        empty='_empty_' in folder.name;end=3.14 if empty else 3.50
        win=(source[:-1]>=2.76)&(source[:-1]<=end+.05)
        bones={}
        for bone in ['upperarm_l','upperarm_twist_02_l','lowerarm_l','lowerarm_twist_01_l','hand_l']:
            row=w[:,names.index(bone)];q=R.from_quat(row[:,3:7])
            step=np.degrees((q[:-1].inv()*q[1:]).magnitude())
            dist=np.linalg.norm(np.diff(row[:,:3],axis=0),axis=1)
            k=np.where(win)[0][np.argmax(step[win])]
            bones[bone]=dict(max_rotation_step_deg=float(step[k]),at_source=float(source[k]),max_translation_step_cm=float(dist[win].max()))
        gun=w[:,names.index('WPN_root')];hand=w[:,names.index('hand_l')]
        g=R.from_quat(gun[:,3:7]);h=R.from_quat(hand[:,3:7])
        rp=g.inv().apply(hand[:,:3]-gun[:,:3]);rq=g.inv()*h
        tail=source>=end+.04
        idlepos=rp[-1];idleq=rq[-1]
        cases[folder.name]=dict(duration=j['duration'],bones=bones,
            locked_grip_max_cm=float(np.linalg.norm(rp[tail]-idlepos,axis=1).max()),
            locked_grip_max_deg=float(np.degrees((idleq.inv()*rq[tail]).magnitude()).max()))
    results[label]=cases
    worst=max((v['max_rotation_step_deg'],c,b) for c,row in cases.items() for b,v in row['bones'].items())
    hand=max((row['bones']['hand_l']['max_translation_step_cm'],c) for c,row in cases.items())
    lock=max((row['locked_grip_max_cm'],c) for c,row in cases.items())
    print(label,'cases',len(cases),'max return rotation',worst,'max hand step',hand,'grip drift',lock)
(r/'continuity.json').write_text(json.dumps(results,indent=2))
