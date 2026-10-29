"""Whirlwind: extended weapon arm and a chest-relative closed left guard.

Native shoulder/elbow planes and palm axes drive the complete arm chains.
The existing body, support steps and signed actor rotation stay on one clock.
"""
import importlib.util
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
PREVIOUS=ROOT/'SourceAssets/KukriWhirlwind20261025'
BASE=ROOT/'SourceAssets/KukriThirdPerson20261024/ComboV3'
spec=importlib.util.spec_from_file_location('kukri_body',BASE/'author.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
ROLES=('Whirlwind.Start','Whirlwind.Loop','Whirlwind.End')


def phase(u):
    a,b=.12,.18
    area=1-.5*(a+b)
    ramp=lambda x:x*x*x-.5*x*x*x*x
    return np.where(u<a,a*ramp(u/a)/area,np.where(u>1-b,1-b*ramp((1-u)/b)/area,(u-.5*a)/area))


def chest(body,frames):
    p,q=body.world(frames)
    j=body.ix['spine_03']
    return p,q,R.from_quat(q[:,j])*R.from_quat(body.tq[j]).inv()


def shoulders(body,frames,weight,wave):
    _,q,torso=chest(body,frames)
    desired={}
    for side in 'rl':
        i=body.ix['clavicle_'+side]
        # Small supported scapular lift/protraction; left shoulder stays relaxed.
        tilt=np.c_[np.zeros(len(frames)),np.full(len(frames),-3. if side=='r' else 1.),
                   (4. if side=='r' else -7.)+1.2*wave]
        goal=torso*R.from_euler('xyz',tilt,degrees=True)*R.from_quat(body.tq[i])
        desired[i]=R.from_quat(c.slerp(q[:,i],goal.as_quat(),weight[:,None]))
    body.set_world_rotations(frames,desired)


def solve_arm(body,frames,side,goal,pole,roll_weight,hand_weight,boundary_hand):
    p,q,torso=chest(body,frames)
    ui,ei,hi=[body.ix[n+'_'+side] for n in ('upperarm','lowerarm','hand')]
    shoulder=p[:,ui]
    l1=np.linalg.norm(body.ref[ei,:3]);l2=np.linalg.norm(body.ref[hi,:3])
    axis=c.unit(goal-shoulder)
    distance=np.clip(np.linalg.norm(goal-shoulder,axis=1),abs(l1-l2)+.02,(l1+l2)*.985)
    goal=shoulder+axis*distance[:,None]
    bend=pole-shoulder
    bend=c.unit(bend-axis*np.sum(bend*axis,axis=1)[:,None])
    along=(l1*l1-l2*l2+distance*distance)/(2*distance)
    elbow=shoulder+axis*along[:,None]+bend*np.sqrt(np.maximum(0.,l1*l1-along*along))[:,None]
    upper=elbow-shoulder;fore=goal-elbow
    ref_upper=body.tp[ei]-body.tp[ui];ref_fore=body.tp[hi]-body.tp[ei]
    uq=c.frame(upper,fore)*c.frame(ref_upper,ref_fore).inv()*R.from_quat(body.tq[ui])
    fq=c.frame(fore,upper)*c.frame(ref_fore,ref_upper).inv()*R.from_quat(body.tq[ei])
    # At entry/exit carry the actual boundary roll, then settle to the native
    # elbow plane. Both rotations have the same bone axis, so lengths stay fixed.
    inherited_u=c.align(p[:,ei]-shoulder,upper)*R.from_quat(q[:,ui])
    inherited_f=c.align(p[:,hi]-p[:,ei],fore)*R.from_quat(q[:,ei])
    uq=R.from_quat(c.slerp(inherited_u.as_quat(),uq.as_quat(),roll_weight[:,None]))
    fq=R.from_quat(c.slerp(inherited_f.as_quat(),fq.as_quat(),roll_weight[:,None]))
    hand_ref=R.from_quat(body.tq[hi])
    palm=hand_ref.inv().apply(body.tp[body.ix['middle_01_'+side]]-body.tp[hi])
    up=torso.apply(np.tile([0.,0.,1.],(len(frames),1)))
    forward=torso.apply(np.tile([0.,1.,0.],(len(frames),1)))
    palm_goal=c.unit(c.unit(fore)+(.055 if side=='r' else .08)*up)
    if side=='r':
        # Match the real grip's blade axis with a natural wrist. Forcing the
        # knife and forearm onto one line would bend this grip's wrist ~83 deg.
        grip_tip=body.blade_local.apply([0.,0.,1.])
        hand=c.frame(palm_goal,forward+.18*up)*c.frame(palm,grip_tip).inv()
    else:
        across=hand_ref.inv().apply(body.tp[body.ix['index_01_l']]-body.tp[body.ix['pinky_01_l']])
        # Thumb upward, palm toward the chest, fist supported by the forearm.
        hand=c.frame(palm_goal,up)*c.frame(palm,across).inv()
    carried=fq*R.from_quat(boundary_hand)
    hand=R.from_quat(c.slerp(carried.as_quat(),hand.as_quat(),hand_weight[:,None]))
    body.set_world_rotations(frames,{ui:uq,ei:fq,hi:hand})


def local_arm_points(body,frame):
    p,q,rot=chest(body,frame[None])
    return {side:{
        'hand':rot.inv().apply(p[:,body.ix['hand_'+side]]-p[:,body.ix['upperarm_'+side]])[0],
        'elbow':rot.inv().apply(p[:,body.ix['lowerarm_'+side]]-p[:,body.ix['upperarm_'+side]])[0],
        'hand_local':frame[body.ix['hand_'+side],3:7].copy()
    } for side in 'rl'}


def make_loop(body,original,turns):
    frames=original.copy();n=len(frames)
    cycles=turns*phase(np.linspace(0.,1.,n))
    wave=np.sin(2*np.pi*cycles)
    # Squared sine closes with zero derivative at each stage boundary.
    effort=np.sin(np.pi*cycles)**2
    shoulders(body,frames,np.ones(n),wave)
    p,_,rot=chest(body,frames)
    mid=(p[:,body.ix['upperarm_l']]+p[:,body.ix['upperarm_r']])*.5
    size=body.scale/94.
    for side in 'rl':
        ui,ei,hi=[body.ix[a+'_'+side] for a in ('upperarm','lowerarm','hand')]
        length=np.linalg.norm(body.ref[ei,:3])+np.linalg.norm(body.ref[hi,:3])
        if side=='r':
            direction=c.unit(np.c_[-np.ones(n),.14+.025*wave,-.08+.025*effort])
            goal=p[:,ui]+rot.apply(direction*(length*(.958-.010*effort))[:,None])
            pole=p[:,ui]+rot.apply(np.tile([-.32,.15,-.50],(n,1))*length)
        else:
            offset=np.c_[-3.+.7*wave,18.+.6*effort,-14.+.6*effort]*size
            goal=mid+rot.apply(offset)
            pole=p[:,ui]+rot.apply(np.tile([.15,.20,-.58],(n,1))*length)
        solve_arm(body,frames,side,goal,pole,np.ones(n),np.ones(n),body.ref[hi,3:7])
    frames=body.twists(frames)
    frames[-1]=frames[0]
    return frames


def make_transition(body,original,loop_boundary,entry,rate):
    frames=original.copy();n=len(frames);ts=np.arange(n)/rate;duration=ts[-1]
    idle_boundary=original[0] if entry else original[-1]
    idle=local_arm_points(body,idle_boundary);guard=local_arm_points(body,loop_boundary)
    scap=c.ease(ts/(duration*.90)) if entry else 1-c.ease(ts/duration)
    shoulders(body,frames,scap,np.zeros(n))
    p,_,rot=chest(body,frames)
    for side in 'rl':
        ui=body.ix['upperarm_'+side]
        if entry:
            weight=c.ease((ts-(.055 if side=='r' else .015))/(.405 if side=='r' else .285))
        else:
            weight=1-c.ease((ts-(.025 if side=='r' else .16))/(.46 if side=='r' else .35))
        offset=idle[side]['hand']*(1-weight[:,None])+guard[side]['hand']*weight[:,None]
        pole_offset=idle[side]['elbow']*(1-weight[:,None])+guard[side]['elbow']*weight[:,None]
        # Lead the draw/return through a shallow forward arc, without crossing
        # the guarding fist or snapping between component-space wrist targets.
        arc=np.sin(np.pi*weight)**2
        offset+=arc[:,None]*np.array([0.,4. if side=='r' else 2.,-2. if side=='r' else 0.])*body.scale/94.
        goal=p[:,ui]+rot.apply(offset);pole=p[:,ui]+rot.apply(pole_offset)
        solve_arm(body,frames,side,goal,pole,weight,weight,idle[side]['hand_local'])
    frames=body.twists(frames)
    if entry:frames[0]=original[0];frames[-1]=loop_boundary
    else:frames[0]=loop_boundary;frames[-1]=original[-1]
    return frames


def main():
    cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    saved=json.loads((PREVIOUS/'assets-saved.json').read_text())
    tuning=json.loads((ROOT/'Content/ColdSteelData/skills.json').read_text(encoding='utf-8-sig'))['whirlwind']
    receipt=dict(bodies={},runtime_tested=False,rendered=False,gameplay_changed=False,first_person_changed=False,
        source=str(PREVIOUS.relative_to(ROOT)),pose='Weapon arm extended with a soft elbow; left fist held across the chest with thumb up',
        native_blade_grip=True,torso_relative_targets=True)
    for label,data in c.INPUT['targets'].items():
        section=cfg if label=='jason' else cfg['body_variants'][label]
        previous={role:section['clips']['Kukri.FullBody.'+role] for role in ROLES}
        for role in ROLES:
            if previous[role]!=saved['bodies'][label]['clips']['Kukri.FullBody.'+role]:
                raise RuntimeError('Active whirlwind changed; do not replace unknown source: '+label+' '+role)
        baseline=json.loads((PREVIOUS/(label+'-actions.json')).read_text())
        body=c.Body(data);clips=baseline['clips']
        loop=make_loop(body,np.asarray(clips['Whirlwind.Loop']['frames']),abs(tuning['turnDegrees'])/360.)
        start=make_transition(body,np.asarray(clips['Whirlwind.Start']['frames']),loop[0],True,clips['Whirlwind.Start']['rate'])
        end=make_transition(body,np.asarray(clips['Whirlwind.End']['frames']),loop[-1],False,clips['Whirlwind.End']['rate'])
        for role,frames in zip(ROLES,(start,loop,end)):
            clips[role]['frames']=frames.tolist()
            clips[role]['adaptation']='Chest-relative extended right arm with soft elbow; left closed fist across chest, thumb up; native elbow planes and supported wrists; staggered draw/return and exact stage endpoints; existing body support steps and actor clock retained.'
        (OUT/(label+'-actions.json')).write_text(json.dumps(baseline,separators=(',',':')))
        receipt['bodies'][label]=dict(mesh=data['mesh'],previous_roles=previous,
            edited_rotation_tracks=['clavicle_'+s for s in 'rl']+[a+'_'+s for s in 'rl' for a in ('upperarm','lowerarm','hand','lowerarm_twist_01','lowerarm_twist_02')],
            right_reach_fraction=[.948,.958],left_guard_cm_from_shoulders_midpoint=[-3.,18.,-14.],
            clips={role:dict(frames=len(clips[role]['frames']),rate=clips[role]['rate']) for role in ROLES})
        print('KUKRI_WHIRLWIND_GUARD_AUTHORED '+label,flush=True)
    (OUT/'authoring.json').write_text(json.dumps(receipt,indent=2))


if __name__=='__main__':
    main()
