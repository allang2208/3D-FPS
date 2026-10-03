"""Relieve the cover-lift wrist bend by rotating the elbow around the fixed shoulder-hand axis."""
import json
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter1d,maximum_filter1d
from scipy.spatial.transform import Rotation as R
HERE=Path(__file__).resolve().parent
OUT=HERE/'Tracks';OUT.mkdir(exist_ok=True)
d=json.loads((HERE/'Inputs/BarePalmV7.json').read_text())
poses=json.loads((HERE/'Inputs/poses.json').read_text())
def mat(t):
    m=np.eye(4);m[:3,:3]=R.from_quat(t['q']).as_matrix()*np.array(t['s']);m[:3,3]=t['p'];return m
rest={n:mat(v) for n,v in d['bones'].items()}
refrot={n:R.from_quat(v['q']).as_matrix() for n,v in d['bones'].items()}
indices={b['index']:n for n,b in d['bones'].items()}
parents={n:indices.get(b['parent']) for n,b in d['bones'].items()}
S,E,H=[rest[n][:3,3] for n in ['upperarm_l','lowerarm_l','hand_l']]
u0=E-S;f0=H-E;f0/=np.linalg.norm(f0)
width=rest['index_metacarpal_l'][:3,3]-rest['pinky_metacarpal_l'][:3,3]
changed=['upperarm_l','upperarm_twist_01_l','upperarm_twist_02_l','lowerarm_l','lowerarm_twist_02_l','lowerarm_twist_01_l','hand_l']
def unit(x):return x/np.linalg.norm(x)
def swing(a,b):
    a=unit(a);b=unit(b);q=np.r_[np.cross(a,b),1+np.clip(a@b,-1,1)]
    if np.linalg.norm(q)<1.e-6:raise RuntimeError('Antiparallel arm axis')
    return R.from_quat(unit(q)).as_matrix()
def basis(axis,side):
    axis=unit(axis);side=unit(side-axis*(side@axis));return np.column_stack((axis,side,np.cross(axis,side)))
bind=basis(f0,width)
def ang(a,b):return float(np.degrees(np.arccos(np.clip(unit(a)@unit(b),-1,1))))
def channels(m,previous):
    scale=np.linalg.norm(m[:3,:3],axis=0);q=R.from_matrix(m[:3,:3]/scale).as_quat()
    if previous is not None and q@previous<0:q=-q
    return {'p':m[:3,3].tolist(),'q':q.tolist(),'s':scale.tolist()},q

report={}
for name,clip in poses.items():
    if not (name.endswith('_reload') or name.endswith('_reload_empty')):continue
    rows=clip['frames'];required=[];circles=[]
    for row in rows:
        s,e,w=[np.array(row[n]['p']) for n in ['upperarm_l','lowerarm_l','hand_l']]
        L1=np.linalg.norm(e-s);L2=np.linalg.norm(w-e);axis=unit(w-s);distance=np.linalg.norm(w-s)
        center=s+axis*(L1*L1-L2*L2+distance*distance)/(2*distance);radial=e-center
        hand=R.from_quat(row['hand_l']['q']).as_matrix()@refrot['hand_l'].T@f0
        target=w-hand*L2-center;target-=axis*(target@axis)
        phi=0.
        if ang(hand,w-e)>50. and np.linalg.norm(target)>1.e-6 and np.linalg.norm(radial)>1.e-6:
            preferred=np.arctan2(axis@np.cross(unit(radial),unit(target)),unit(radial)@unit(target))
            cap=min(abs(preferred),np.radians(45));sign=np.sign(preferred)
            lo,hi=0.,cap
            for _ in range(22):
                mid=(lo+hi)/2;candidate=center+R.from_rotvec(axis*sign*mid).apply(radial)
                if ang(hand,w-candidate)>50:lo=mid
                else:hi=mid
            phi=sign*hi
        required.append(phi);circles.append((center,axis,radial))
    fps=(len(rows)-1)/clip['duration']
    # Broaden the support arc, then ease it: no one-frame correction switch.
    radius=max(1,round(fps*.033));sigma=max(1,fps*.025)
    required=np.array(required)
    arc=gaussian_filter1d(maximum_filter1d(np.maximum(required,0),size=2*radius+1,mode='nearest')-
        maximum_filter1d(np.maximum(-required,0),size=2*radius+1,mode='nearest'),sigma,mode='nearest')
    # Smooth the elbow's pole in a parallel-transported frame. Smoothing world
    # positions would shorten the bones and disturb the fixed palm contacts.
    phases=[];pole_frames=[];last_axis=None
    for center,axis,radial in circles:
        x=unit(radial) if last_axis is None else swing(last_axis,axis)@pole_frames[-1][0]
        y=np.cross(axis,x);pole_frames.append((x,y));last_axis=axis
        phases.append(np.arctan2(radial@y,radial@x))
    phases=np.unwrap(phases)
    eased=gaussian_filter1d(phases+arc,sigma,mode='nearest')
    edge=np.minimum(1.,np.minimum(np.arange(len(rows))/12.,np.arange(len(rows)-1,-1,-1)/12.))
    edge=edge*edge*(3-2*edge)
    arc=(eased-phases)*edge
    tracks={n:[] for n in changed};prev={n:None for n in changed}
    new_pose_rows=[];before=[];after=[];drift=[]
    for i,row in enumerate(rows):
        world={n:mat(v) for n,v in row.items()};s,e,w=[world[n][:3,3].copy() for n in ['upperarm_l','lowerarm_l','hand_l']]
        center,axis,radial=circles[i];new_e=center+R.from_rotvec(axis*arc[i]).apply(radial)
        carry=swing(e-s,new_e-s)
        world['upperarm_l'][:3,:3]=carry@world['upperarm_l'][:3,:3]
        hand=R.from_quat(row['hand_l']['q']).as_matrix()@refrot['hand_l'].T
        fore_skin=basis(w-new_e,hand@width)@bind.T
        upper_skin=swing(fore_skin@u0,new_e-s)@fore_skin
        for segment,names,origin,rest_origin,old_delta,new_delta,skin in [
            ('upper',['upperarm_twist_01_l','upperarm_twist_02_l'],s,S,u0,new_e-s,upper_skin),
            ('lower',['lowerarm_l','lowerarm_twist_02_l','lowerarm_twist_01_l'],new_e,E,H-E,w-new_e,fore_skin)]:
            for n in names:
                station=(rest[n][:3,3]-rest_origin)@old_delta/(old_delta@old_delta)
                offset=rest[n][:3,3]-rest_origin-station*old_delta
                world[n][:3,:3]=(skin@refrot[n])*np.array(row[n]['s'])
                world[n][:3,3]=origin+station*new_delta+skin@offset
        for n in changed:
            key,prev[n]=channels(np.linalg.inv(world[parents[n]])@world[n],prev[n]);tracks[n].append(key)
        before.append(ang(hand@f0,w-e));after.append(ang(hand@f0,w-new_e));drift.append(float(np.linalg.norm(new_e-e)))
        # Joint-space samples retained for the requested follow-up inspection.
        new_pose_rows.append({'shoulder':s.tolist(),'elbow':new_e.tolist(),'wrist':w.tolist()})
    data={'asset':clip['asset'],'keys':len(rows),'duration':clip['duration'],'tracks':tracks,'revision':'ArmJoint49',
          'method':'Fixed shoulder/hand and bone lengths; eased support arc plus transported elbow-pole smoothing; contact orientation retained'}
    (OUT/(name+'.json')).write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    report[name]={'max_wrist_before_degrees':max(before),'max_wrist_after_degrees':max(after),
        'max_elbow_travel_cm':max(drift),'max_pole_turn_degrees':float(np.degrees(np.abs(arc).max())),
        'first_last_pole_degrees':np.degrees(arc[[0,-1]]).tolist()}
(HERE/'motion_authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
