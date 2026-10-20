"""Rigid registration of the approved right arm; no new wrist/finger/limb pose.

Keep the old SVCH palm anchor. Transport the ENTIRE source right arm with one
rigid transform. Internal local joints remain the compressed approved source.
Only the two leaf twist bones follow the established V9 100/50 convention.
"""
import copy,json,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as Rot,Slerp
O=Path(__file__).parent;sys.path.insert(0,str(O.parent))
from contact_inputs import N,PI,matrices,components
data=json.loads((O/'compressed_inputs.json').read_text());assert data['names']==N
R=matrices(data['reference']);source_profile=json.loads((O.parent/'R5/shared_profile_r5.json').read_text())
out=copy.deepcopy(source_profile)
def rot(m):return Rot.from_matrix(m[:3,:3]/np.linalg.norm(m[:3,:3],axis=0))
def unit(x):return x/max(np.linalg.norm(x),1e-12)
C,L,H,T1,T2=[N.index(n+'_r') for n in ('clavicle','lowerarm','hand','lowerarm_twist_01','lowerarm_twist_02')]
right={C}
for i,p in enumerate(PI):
    if p in right:right.add(i)
axis=rot(R[L]).inv().apply(unit(R[H,:3,3]-R[L,:3,3]))
rest={b:rot(R[L]).inv()*rot(R[b]) for b in (H,T1,T2)}
report={'principle':'Preserve approved source internal right-arm joints; rigid whole-arm registration only; V9 leaf twist 100/50.',
        'clips':[],'max_palm_position_error_cm':0.,'max_palm_rotation_error_deg':0.,'max_internal_joint_rotation_error_deg':0.}
for dst in out['clips']:
    kind=dst['base'].split('_')[-1]
    clip=next(c for c in data['clips'].values() if c['path']==dst['base'])
    times=[min(i/120,clip['duration']) for i in range(len(clip['frames']))]
    old_tracks=[(N.index(t['bone']),np.array(t['times']),np.array(t['values']).reshape(-1,10)) for t in dst['tracks']]
    values={b:[] for b in (C,T1,T2)};previous_roll=None
    for i,t in enumerate(times):
        base=np.array(clip['frames'][i]);old=base.copy()
        for bi,ts,vs in old_tracks:
            if len(ts)==1:v=vs[0]
            else:
                k=int(np.clip(np.searchsorted(ts,t)-1,0,len(ts)-2));a=float(np.clip((t-ts[k])/(ts[k+1]-ts[k]),0,1))
                v=vs[k]*(1-a)+vs[k+1]*a
                v[3:7]=Slerp([0,1],Rot.from_quat(vs[k:k+2,3:7]))(a).as_quat()
            old[bi,:3]+=v[:3];old[bi,3:7]=(Rot.from_quat(v[3:7])*Rot.from_quat(base[bi,3:7])).as_quat();old[bi,7:]+=v[7:]
        src=components(matrices(base));target=components(matrices(old));new=target.copy()
        rigid=rot(target[H])*rot(src[H]).inv()
        for b in right:
            new[b,:3,:3]=rigid.as_matrix()@src[b,:3,:3]
            new[b,:3,3]=target[H,:3,3]+rigid.apply(src[b,:3,3]-src[H,:3,3])
        q=(rot(new[L]).inv()*rot(new[H])*rest[H].inv()).as_quat()
        if q[3]<0:q=-q
        hand_roll=2*np.arctan2(q[:3]@axis,q[3])
        if previous_roll is not None:hand_roll=previous_roll+np.arctan2(np.sin(hand_roll-previous_roll),np.cos(hand_roll-previous_roll))
        previous_roll=hand_roll
        for b,share in ((T1,1.),(T2,.5)):
            new[b,:3,:3]=(rot(new[L])*Rot.from_rotvec(axis*hand_roll*share)*rest[b]).as_matrix()*np.linalg.norm(src[b,:3,:3],axis=0)
        report['max_palm_position_error_cm']=max(report['max_palm_position_error_cm'],float(np.linalg.norm(new[H,:3,3]-target[H,:3,3])))
        report['max_palm_rotation_error_deg']=max(report['max_palm_rotation_error_deg'],float(np.degrees((rot(new[H]).inv()*rot(target[H])).magnitude())))
        for b in right-{C,T1,T2}:
            local=np.linalg.solve(new[PI[b]],new[b])
            error=np.degrees((rot(local).inv()*Rot.from_quat(base[b,3:7])).magnitude())
            report['max_internal_joint_rotation_error_deg']=max(report['max_internal_joint_rotation_error_deg'],float(error))
        for b in values:
            loc=np.linalg.solve(new[PI[b]],new[b]);delta=[*(loc[:3,3]-base[b,:3]),*(rot(loc)*Rot.from_quat(base[b,3:7]).inv()).as_quat(),*(np.linalg.norm(loc[:3,:3],axis=0)-base[b,7:])]
            if values[b] and np.dot(values[b][-1][3:7],delta[3:7])<0:delta[3:7]=[-x for x in delta[3:7]]
            values[b].append(delta)
    removed=[t['bone'] for t in dst['tracks'] if N.index(t['bone']) in right]
    dst['tracks']=[t for t in dst['tracks'] if N.index(t['bone']) not in right]
    for b,rows in values.items():dst['tracks'].append({'bone':N[b],'times':times,'values':np.round(rows,9).ravel().tolist()})
    report['clips'].append({'clip':clip['path'],'removed_local_pose_tracks':removed,'right_tracks_now':[N[b] for b in values]})
(O/'shared_profile_native_v9.json').write_text(json.dumps(out,separators=(',',':')))
(O/'registration_receipt.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='clips'},indent=2))
