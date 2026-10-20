import sys,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as Rot
O=Path(__file__).parent
sys.path.insert(0,str(O.parent))
from contact_inputs import D,N,PI,R,matrices,components
def unit(v):return v/max(np.linalg.norm(v),1e-12)
def rot(m):return Rot.from_matrix(m[:3,:3]/np.linalg.norm(m[:3,:3],axis=0))
def angle(a,b):return float(np.degrees(np.arccos(np.clip(unit(a)@unit(b),-1,1))))
profile=json.loads((O.parent/'shared_profile.json').read_text())
clip=D['clips']['inspect'];entry=next(c for c in profile['clips'] if c['base']==clip['path'])
def corrected(index):
    base=np.array(clip['frames'][index]);new=base.copy();t=min(index/120,clip['duration'])
    for track in entry['tracks']:
        values=np.array(track['values']).reshape(-1,10);times=np.array(track['times'])
        v=values[np.abs(times-t).argmin()];bi=N.index(track['bone'])
        new[bi,:3]+=v[:3];new[bi,3:7]=(Rot.from_quat(v[3:7])*Rot.from_quat(base[bi,3:7])).as_quat();new[bi,7:]+=v[7:]
    return components(matrices(base)),components(matrices(new))
L,H,T1,T2,M,I,P=[N.index(n+'_r') for n in ('lowerarm','hand','lowerarm_twist_01','lowerarm_twist_02','middle_01','index_metacarpal','pinky_metacarpal')]
fore=unit(R[H,:3,3]-R[L,:3,3]);axis=rot(R[L]).inv().apply(fore)
rest={i:rot(R[L]).inv()*rot(R[i]) for i in (H,T1,T2)}
f0=unit(R[M,:3,3]-R[H,:3,3]);r0=R[I,:3,3]-R[P,:3,3];r0=unit(r0-(r0@f0)*f0);z0=np.cross(f0,r0)
f0,r0,z0=[rot(R[T1]).inv().apply(v) for v in (f0,r0,z0)]
def roll(q):
    v=q.as_quat()
    if v[3]<0:v=-v
    return float(np.degrees(2*np.arctan2(v[:3]@axis,v[3])))
def metric(p):
    ql=rot(p[L]);qh=rot(p[H]);qt=rot(p[T1])
    h=qt.inv().apply(unit(p[M,:3,3]-p[H,:3,3]))
    return {'axis_bend_deg':angle(p[H,:3,3]-p[L,:3,3],(qh*rot(R[H]).inv()).apply(fore)),
        'hand_roll_deg':roll(ql.inv()*qh*rest[H].inv()),
        'twist01_roll_deg':roll(ql.inv()*qt*rest[T1].inv()),
        'flex_deg':float(np.degrees(np.arctan2(-h@z0,h@f0))),
        'deviation_deg':float(np.degrees(np.arctan2(h@r0,h@f0))),
        'elbow_cm':p[L,:3,3].tolist(),'wrist_cm':p[H,:3,3].tolist()}
if __name__=='__main__':
    rows=[]
    for index in range(0,len(clip['frames']),4):
        a,b=corrected(index);rows.append({'time':index/120,'source':metric(a),'r4':metric(b)})
    a,b=corrected(round(3.716667*120));report={'inspect_3_7167':{'source':metric(a),'r4':metric(b)},
        'max_bend':{k:max(r[k]['axis_bend_deg'] for r in rows) for k in ('source','r4')},'frames':rows}
    (O/'wrist_diagnosis.json').write_text(json.dumps(report,indent=1))
    print(json.dumps({k:v for k,v in report.items() if k!='frames'},indent=1))
