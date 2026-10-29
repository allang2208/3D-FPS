"""V10 master-timeline performance with supported wrists and planted toes.

Only native rig math, binding and grip fitting are reused. No V8/V9 animation
frames, phase curves or transition functions are consumed. All three output
clips are slices of the same continuous performance, including its arms/feet.
"""
import importlib.util
import json
from pathlib import Path
import numpy as np
from scipy.interpolate import CubicSpline
from scipy.spatial.transform import Rotation as R

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
spec=importlib.util.spec_from_file_location('windmill_native_utilities',ROOT/'SourceAssets/KukriWhirlwindSourceMotion20261025/author.py')
rig=importlib.util.module_from_spec(spec);spec.loader.exec_module(rig)
c,old,native=rig.c,rig.old,rig.native
RATE=120
ROLES=('Whirlwind.Start','Whirlwind.Loop','Whirlwind.End')


def smooth(v):
    v=np.clip(v,0.,1.);return v*v*v*(10.+v*(-15.+6.*v))


def spline(keys,values,times):
    values=np.asarray(values,dtype=float);zero=np.zeros(values.shape[1:])
    return CubicSpline(keys,values,bc_type=((1,zero),(1,zero)))(times)


def timeline(tuning):
    ready,spin,end=[tuning[k] for k in ('readySeconds','spinSeconds','recoverSeconds')]
    segments=[np.linspace(0.,ready,round(ready*RATE)+1),
              np.linspace(ready,ready+spin,round(spin*RATE)+1),
              np.linspace(ready+spin,ready+spin+end,round(end*RATE)+1)]
    times=np.concatenate([segments[0],segments[1][1:],segments[2][1:]])
    cuts=[(0,len(segments[0])),(len(segments[0])-1,len(segments[0])+len(segments[1])-1),
          (len(segments[0])+len(segments[1])-2,len(times))]
    design=json.loads((OUT/'motion.json').read_text())
    offsets={'ready':0.,'spin':ready,'recover':ready+spin}
    lengths={'ready':ready,'spin':spin,'recover':end}
    keys=np.array([offsets[k['stage']]+k['u']*lengths[k['stage']] for k in design['keys']])
    return times,cuts,keys,design['keys']


def feet(body,frames,times,tuning,size):
    """World toe anchors with ankle rotation around the planted toe."""
    ready,spin,recover=[tuning[k] for k in ('readySeconds','spinSeconds','recoverSeconds')]
    stop=ready+spin
    progress=np.clip((times-ready)/spin,0.,1.)
    turns=abs(tuning['turnDegrees'])/360.
    angular=turns*old.arms.phase(progress)
    actor=-2*np.pi*angular
    ip,iq=body.world(body.idle)
    goals,rots,poles={},{},{}
    for side,offset in [('l',0.),('r',.5)]:
        step=2*angular-offset
        whole=np.floor(step);phase=step-whole
        flight=np.clip((phase-.5)*2,0.,1.)
        centre=(whole+offset+.25)/2
        anchor=-2*np.pi*(centre+.5*smooth(flight))
        relative=anchor-actor
        yaw=R.from_euler('z',relative[:,None])
        lift=np.sin(np.pi*flight)**2
        # The ankle follows the toe, not an independently offset foot point.
        toe=yaw.apply(np.c_[(1 if side=='l' else -1)*18.5*size*(1+.10*lift),np.full(len(times),9.*size),np.zeros(len(times))])
        foot,ball=body.ix['foot_'+side],body.ix['ball_'+side]
        toe[:,2]=ip[ball,2]+4.2*size*lift
        heel=np.where(phase<.5,-14.*np.sin(np.pi*phase*2)**2,6.*np.sin(np.pi*flight)**2)
        rotation=R.from_euler('z',(.72*relative)[:,None])*R.from_euler('x',heel[:,None],degrees=True)*R.from_quat(iq[foot])
        # Stagger the step out and braking return on the same master clock.
        if side=='l':enter=(.03,.30);leave=(.16,.49)
        else:enter=(.25,.48);leave=(.01,.30)
        arrival=smooth((times-enter[0])/(enter[1]-enter[0]))
        departure=1.-smooth((times-stop-leave[0])/(leave[1]-leave[0]))
        weight=arrival*departure
        target=ip[ball]+(toe-ip[ball])*weight[:,None]
        first=np.clip((times-enter[0])/(enter[1]-enter[0]),0.,1.)
        last=np.clip((times-stop-leave[0])/(leave[1]-leave[0]),0.,1.)
        target[:,2]+=(np.sin(np.pi*first)**2+np.sin(np.pi*last)**2)*4.5*size
        rotation=R.from_quat(c.slerp(iq[foot],rotation.as_quat(),weight[:,None]))
        toe_local=R.from_quat(iq[foot]).inv().apply(ip[ball]-ip[foot])
        goals[side]=target-rotation.apply(np.tile(toe_local,(len(times),1)))
        rots[side]=rotation
        bent=R.from_euler('z',(.48*relative)[:,None]).apply(np.tile([26 if side=='l' else -26,42,-27],(len(times),1)))*size
        target_pole=frames[:,body.hip,:3]+bent
        poles[side]=ip[body.ix['calf_'+side]]*(1-weight[:,None])+target_pole*weight[:,None]
    old.steps.fit_legs(body,frames,goals,rots,poles)


def arm(body,frames,side,goal,pole,amount,torso):
    """Transport a native bent elbow; roll the palm axially, never kink it."""
    ui,ei,hi=[body.ix[n+'_'+side] for n in ('upperarm','lowerarm','hand')]
    p,q=body.world(frames);ip,iq=body.world(body.idle)
    origin=p[:,ui]
    l1=np.linalg.norm(body.ref[ei,:3]);l2=np.linalg.norm(body.ref[hi,:3])
    direction=c.unit(goal-origin)
    distance=np.clip(np.linalg.norm(goal-origin,axis=1),abs(l1-l2)+.02,(l1+l2)*.955)
    goal=origin+direction*distance[:,None]
    bend=pole-origin;bend=c.unit(bend-direction*np.sum(bend*direction,axis=1)[:,None])
    along=(l1*l1-l2*l2+distance*distance)/(2*distance)
    elbow=origin+direction*along[:,None]+bend*np.sqrt(np.maximum(0.,l1*l1-along*along))[:,None]
    upper,fore=elbow-origin,goal-elbow
    ref_u,ref_f=ip[ei]-ip[ui],ip[hi]-ip[ei]
    uq=c.frame(upper,fore)*c.frame(ref_u,ref_f).inv()*R.from_quat(iq[ui])
    fq=c.frame(fore,upper)*c.frame(ref_f,ref_u).inv()*R.from_quat(iq[ei])
    # A straight supported wrist in its own native axes. Grip fingers and the
    # blade remain rigidly attached; only axial rotation changes palm facing.
    hand_bind=R.from_quat(body.tq[hi]);local_ref=R.from_quat(body.ref[hi,3:7])
    palm=hand_bind.inv().apply(body.tp[body.ix['middle_01_'+side]]-body.tp[hi])
    axis=c.unit(body.ref[hi,:3])
    neutral=c.align(local_ref.apply(palm),axis)*local_ref
    base=fq*neutral
    fore_axis=c.unit(fore)
    up=torso.apply(np.tile([0.,0.,1.],(len(frames),1)))
    if side=='r':
        tip=np.array(json.loads((ROOT/'SourceAssets/Kukri20261020/model.json').read_text())['tip_cm'])
        landmark=body.blade_local.apply(c.unit(tip))
        wanted=c.unit(np.cross(fore_axis,up))
    else:
        landmark=hand_bind.inv().apply(body.tp[body.ix['index_01_l']]-body.tp[body.ix['pinky_01_l']])
        wanted=up
    v=base.apply(np.tile(landmark,(len(frames),1)))
    v=c.unit(v-fore_axis*np.sum(v*fore_axis,axis=1)[:,None])
    w=c.unit(wanted-fore_axis*np.sum(wanted*fore_axis,axis=1)[:,None])
    angle=np.unwrap(np.arctan2(np.sum(np.cross(v,w)*fore_axis,axis=1),np.sum(v*w,axis=1)))
    angle-=2*np.pi*round(float(np.median(angle))/(2*np.pi))
    # Smooth comfort limit; no quaternion +/-180 branch or hard per-frame clamp.
    limit=np.radians(95. if side=='r' else 85.)
    roll=limit*np.tanh(angle/limit)
    hand=(R.from_rotvec(fore_axis*roll[:,None])*base)
    # Entry and recovery keep the current idle wrist and roll while the native
    # elbow plane and support rotation take over smoothly.
    idle_local=R.from_quat(body.idle[hi,3:7])
    hand=R.from_quat(c.slerp((fq*idle_local).as_quat(),hand.as_quat(),amount[:,None]))
    body.set_world_rotations(frames,{ui:uq,ei:fq,hi:hand})


def make_body(body,label,tuning,times,keys,poses):
    count=len(times);size=body.scale/94.
    frames=np.repeat(body.idle[None],count,axis=0)
    ip,iq=body.world(body.idle)
    ready,spin,recover=[tuning[k] for k in ('readySeconds','spinSeconds','recoverSeconds')]
    stop=ready+spin
    ownership=smooth(times/.34)*(1.-smooth((times-stop-.12)/(recover-.12)))
    frames[:,body.hip,:3]=ip[body.hip]+spline(keys,[k['hip'] for k in poses],times)*size
    angles=spline(keys,[k['torso'] for k in poses],times)
    desired={}
    for name,pitch,lean,yaw in [('pelvis',.38,.5,.42),('spine_01',.65,.7,.68),
        ('spine_02',.85,.9,.86),('spine_03',1.,1.,1.),('neck_01',.50,.5,.7),('head',.25,.3,.45)]:
        i=body.ix[name]
        rotation=R.from_euler('xyz',angles*np.array([pitch,lean,yaw]),degrees=True)*R.from_quat(body.tq[i])
        desired[i]=R.from_quat(c.slerp(iq[i],rotation.as_quat(),ownership[:,None]))
    body.set_world_rotations(frames,desired)
    feet(body,frames,times,tuning,size)
    _,_,torso=old.arms.chest(body,frames)
    scap=spline(keys,[k['scapula'] for k in poses],times)
    desired={}
    idle_torso=R.from_quat(iq[body.ix['spine_03']])*R.from_quat(body.tq[body.ix['spine_03']]).inv()
    for side,index in [('r',0),('l',1)]:
        i=body.ix['clavicle_'+side]
        base=torso*idle_torso.inv()*R.from_quat(iq[i])
        delta=R.from_euler('z',(scap[:,index]*ownership)[:,None],degrees=True)
        desired[i]=torso*delta*torso.inv()*base
    body.set_world_rotations(frames,desired)
    p,_,torso=old.arms.chest(body,frames)
    middle=(p[:,body.ix['upperarm_l']]+p[:,body.ix['upperarm_r']])*.5
    idle_middle=(ip[body.ix['upperarm_l']]+ip[body.ix['upperarm_r']])*.5
    for side in 'rl':
        ui,ei,hi=[body.ix[n+'_'+side] for n in ('upperarm','lowerarm','hand')]
        length=np.linalg.norm(body.ref[ei,:3])+np.linalg.norm(body.ref[hi,:3])
        idle_hand=idle_torso.inv().apply(ip[hi]-(ip[ui] if side=='r' else idle_middle))
        values=[idle_hand if k['right' if side=='r' else 'left'] is None else
                np.array(k['right' if side=='r' else 'left'])*(length if side=='r' else size) for k in poses]
        hand=spline(keys,values,times)
        if side=='l':
            # Torso clearance fades only as the true idle pose takes over.
            front=old.chest_envelope(body,label)+9.*size
            correction=np.maximum(0.,front-hand[:,1])*ownership
            hand[:,1]+=correction
        origin=p[:,ui] if side=='r' else middle
        goal=origin+torso.apply(hand)
        idle_elbow=idle_torso.inv().apply(ip[ei]-ip[ui])
        # The elbow follows the draw/release before the wrist. Keep its bend
        # plane outside the torso rather than switching between arbitrary poles.
        if side=='r':
            local_pole=np.c_[-np.full(count,.36),.13+.18*smooth((times-.38)/.35),-np.full(count,.48)]*length
        else:
            balance=smooth((times-.55)/.38)*(1.-smooth((times-1.22)/.36))
            local_pole=np.c_[.23+.19*balance,.22-.06*balance,-.54+.10*balance]*length
        pole=idle_elbow*(1-ownership[:,None])+local_pole*ownership[:,None]
        arm(body,frames,side,goal,p[:,ui]+torso.apply(pole),ownership,torso)
    held=old.grip(body)
    fist=old.fingers.native_fist(body,json.loads(old.fingers.FIST_SOURCE.read_text()))
    closure=np.clip(spline(keys,[k['fist'] for k in poses],times),0.,.72)
    old.steps.set_fist(body,frames,fist,closure)
    old.right_fingers(body,frames,held)
    native.native_twists(body,frames)
    for i,name in enumerate(body.names):
        if name.startswith(('upperarm_twist_','lowerarm_twist_')):
            frames[:,i,3:7]=c.slerp(body.idle[i,3:7],frames[:,i,3:7],ownership[:,None])
    frames[0]=body.idle;frames[-1]=body.idle
    old.right_fingers(body,frames,held)
    return frames


def main():
    cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    tuning=json.loads((ROOT/'Content/ColdSteelData/skills.json').read_text(encoding='utf-8-sig'))['whirlwind']
    if tuning['turnDegrees']!=-720:raise RuntimeError('The authored movement expects the existing negative two-turn contract')
    times,cuts,keys,poses=timeline(tuning)
    report=dict(version='V10 continuous master performance',runtime_tested=False,rendered=False,
        reference_motion_imported=False,gameplay_changed=False,first_person_changed=False,
        design='motion.json',previous_animation_frames_used=False,
        reference_limit='Original adaptation; available Mabinogi footage does not resolve hand detail.',bodies={})
    for label,data in rig.DATA.items():
        active=cfg if label=='jason' else cfg['body_variants'][label]
        if active['body_mesh']!=data['mesh'] or active['clips']['Kukri.FullBody.Idle']!=data['idle_asset']:
            raise RuntimeError('Native mesh or idle changed; refresh inputs before authoring')
        body=c.Body(data)
        master=make_body(body,label,tuning,times,keys,poses)
        for k in range(1,len(master)):
            master[k,:,3:7]*=np.where(np.sum(master[k-1,:,3:7]*master[k,:,3:7],axis=1)<0.,-1.,1.)[:,None]
        clips={}
        for role,(start,end) in zip(ROLES,cuts):
            clips[role]=dict(rate=RATE,frames=master[start:end].tolist(),contact=0.,release=.999,
                source='Original continuous native-body authoring; Mabinogi direction only',
                adaptation='Single draw and sustained two-turn sweep; full master timeline shared across stages; natural elbow frame, axially supported palm, planted toe pivots and staggered braking return.')
        (OUT/(label+'-actions.json')).write_text(json.dumps(dict(mesh=data['mesh'],names=body.names,parents=body.parents,clips=clips),separators=(',',':')))
        report['bodies'][label]=dict(mesh=data['mesh'],idle_asset=data['idle_asset'],
            previous_roles={role:active['clips']['Kukri.FullBody.'+role] for role in ROLES},
            authoring_reference_source=data['authoring_reference_source'],
            clips={role:dict(frames=len(v['frames']),rate=RATE) for role,v in clips.items()})
        print('KUKRI_WINDMILL_MASTER_AUTHORED '+label,flush=True)
    (OUT/'authoring.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__':main()
