"""Transfer the accepted grip to native Jason fingers without changing bone lengths."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as Q

R=Path(__file__).resolve().parent
d=json.loads((R/'inputs.json').read_text())
body=d['body']['bones']; target={b['name']:b for b in body}
source={b['name']:b for b in d['source']['bones']}
mount={b['name']:b for b in d['mount']['bones']}; pose=d['pose']
digits=('thumb','index','middle','ring','pinky')
rot=lambda b:Q.from_quat(b['q'])
pos=lambda b:np.array(b['p'],dtype=float)

def between(a,b):
    a=a/np.linalg.norm(a);b=b/np.linalg.norm(b)
    return Q.from_quat(np.r_[np.cross(a,b),1+np.dot(a,b)]/np.sqrt(2*(1+np.dot(a,b))))

# The weapon mount already maps Manny hand axes into Jason. Transfer each
# finger's actual directed segment through exactly that same wrist frame.
# This is an absolute contact pose, not Euler curls copied across bind rigs.
desired={}
for side in ('r','l'):
    hand='hand_'+side
    frame=rot(mount[hand])*rot(pose[hand]).inv()
    for digit in digits:
        for j in range(1,4):
            name=f'{digit}_{j:02}_{side}'
            # Distal bones point along the continuation of the middle segment.
            a=name if j<3 else f'{digit}_02_{side}'
            b=f'{digit}_{j+1:02}_{side}' if j<3 else name
            native_axis=rot(target[name]).inv().apply(pos(target[b])-pos(target[a]))
            source_axis=rot(source[name]).inv().apply(pos(source[b])-pos(source[a]))
            desired[name]=frame*rot(pose[name])*between(native_axis,source_axis)

        # Jason's fingers are shorter than Manny's. Matching rotations alone
        # misses the accepted contact by up to a centimetre. Solve the first
        # two native segments to the source distal joint, using its middle
        # joint as the bend-plane pole; preserve native lengths and distal roll.
        n1,n2,n3=[f'{digit}_{j:02}_{side}' for j in range(1,4)]
        root=pos(target[n1])
        goal=pos(target[hand])+frame.apply(pos(pose[n3])-pos(pose[hand]))
        pole=pos(target[hand])+frame.apply(pos(pose[n2])-pos(pose[hand]))
        l1=np.linalg.norm(pos(target[n2])-root)
        l2=np.linalg.norm(pos(target[n3])-pos(target[n2]))
        axis=goal-root;distance=np.linalg.norm(axis);axis/=distance
        reach=np.clip(distance,abs(l1-l2)+1e-5,l1+l2-1e-5)
        bend=pole-root-axis*np.dot(pole-root,axis);bend/=np.linalg.norm(bend)
        along=(l1*l1-l2*l2+reach*reach)/(2*reach)
        joint=root+axis*along+bend*np.sqrt(max(0,l1*l1-along*along))
        end=root+axis*reach
        for name,child,span in ((n1,n2,joint-root),(n2,n3,end-joint)):
            local_axis=rot(target[name]).inv().apply(pos(target[child])-pos(target[name]))
            desired[name]=between(desired[name].apply(local_axis),span)*desired[name]

local={}; world={}
for bone in body:
    name=bone['name']; parent=body[bone['parent']]['name'] if bone['parent']>=0 else None
    parent_ref=rot(target[parent]) if parent else Q.identity()
    bind_local=parent_ref.inv()*rot(bone)
    parent_pose=world[parent] if parent else Q.identity()
    if name in desired:
        local_rot=parent_pose.inv()*desired[name]
    elif name.endswith(('_half_r','_half_l')) and parent in desired:
        # MetaHuman skin assigns real weights to the *_half_* descendants.
        # Counter-rotate half the joint bend so their surface support follows
        # the midpoint, rather than inheriting the full bend twice.
        p=target[parent]; gp=body[p['parent']]['name']
        delta=(rot(target[gp]).inv()*rot(p)).inv()*local[parent]
        local_rot=Q.from_rotvec(-.5*delta.as_rotvec())*bind_local
    else:
        local_rot=bind_local
    local[name]=local_rot;world[name]=parent_pose*local_rot

tracks={}
for bone in body:
    name=bone['name']
    if not name.startswith(tuple(x+'_' for x in digits)):continue
    parent=target[body[bone['parent']]['name']]
    translation=rot(parent).inv().apply(pos(bone)-pos(parent))/np.array(parent['s'])
    tracks[name]=dict(p=translation.tolist(),q=local[name].as_quat().tolist(),
                      s=(np.array(bone['s'])/np.array(parent['s'])).tolist())
(R/'grip.json').write_text(json.dumps(dict(source_clip=d['source_clip'],body=d['body']['path'],
    body_idle=d['body_idle'],tracks=tracks,policy='native_lengths_source_segment_directions_half_joint_support',
    runtime_tested=False),indent=2))
print('JASON_SWORD_GRIP_AUTHORED',len(tracks),'finger and helper tracks')
