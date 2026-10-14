"""Offline authoring math for the coupled grip; does not run the game."""
from pathlib import Path
import json
import numpy as np
from scipy.spatial.transform import Rotation as R

src=Path(__file__).with_name('author_actions.py')
ns={'__file__':str(src)}
exec(compile(src.read_text().split('clips={}')[0],str(src),'exec'),ns)
rig=ns['rig'];ix=ns['ix'];idle_w=ns['idle_w'];ref=ns['ref'];grips=ns['grips']
d=json.loads(src.with_name('authored-actions.json').read_text())
result={}
for label,c in d['clips'].items():
    report={}
    for side in ('r','l'):
        a,b,h=[ix[n+'_'+side] for n in ('upperarm','lowerarm','hand')]
        l1,l2=np.linalg.norm(ref[b,:3]),np.linalg.norm(ref[h,:3]);worst=(0,0)
        previous=None;motion={n:(0,0) for n in ('upperarm_'+side,'lowerarm_'+side,'hand_'+side)}
        for j,frame in enumerate(c['frames']):
            f=np.array(frame);w=rig.fk(f);target=w[h,:7];origin=w[a,:3]
            axis=rig.unit(target[:3]-origin);distance=np.linalg.norm(target[:3]-origin)
            along=(l1*l1-l2*l2+distance*distance)/(2*distance)
            radius=np.sqrt(max(0,l1*l1-along*along));center=origin+axis*along
            ideal=rig.rot(rig.mul(target[3:7],rig.inv(ref[h,3:7])),rig.unit(ref[h,:3]))
            wanted=target[:3]-ideal*l2-center;wanted-=axis*np.dot(wanted,axis)
            elbow=center+rig.unit(wanted)*radius
            angle=np.degrees(np.arccos(np.clip(np.dot(rig.unit(target[:3]-elbow),ideal),-1,1)))
            if angle>worst[0]:worst=(round(angle,1),j)
            if previous is not None:
                for name in motion:
                    change=np.degrees((R.from_quat(previous[ix[name],3:7]).inv()*R.from_quat(f[ix[name],3:7])).magnitude())
                    if change>motion[name][0]:motion[name]=(round(change,1),j)
            previous=f
        local=np.array(c['frames'])[:,h,3:7]
        articulation=(R.from_quat(ref[h,3:7]).inv()*R.from_quat(local)).magnitude()*180/np.pi
        report[side]={'minimum_wrist_swing_max':worst,'wrist_articulation_max':[round(float(max(articulation)),1),int(np.argmax(articulation))],'joint_motion':motion}
    result[label]=report
src.with_name('authoring-joint-motion.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
