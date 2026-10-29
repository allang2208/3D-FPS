"""V13: shoulder-height reach and a native relaxed left arm.

The three sequences share one timeline. Native anatomy/grip math derives from
V10; posture, support and free-hand behavior follow the user's new direction.
"""
import importlib.util
import json
import re
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


def effective_tuning():
    tuning=json.loads((ROOT/'Content/ColdSteelData/skills.json').read_text(encoding='utf-8-sig'))['whirlwind']
    # Read the same constants used by both the local executor and authority.
    source=(ROOT/'Source/FPSGAME/Weapons/Kukri/KukriWhirlwindRhythm.h').read_text()
    def constant(name):
        return float(re.search(r'constexpr float '+name+r'=([0-9.]+)f;',source).group(1))
    tuning['spinSeconds']/=constant('SpinSpeedScale')
    tuning['turnDegrees']=constant('TurnDirection')*abs(tuning['turnDegrees'])
    tuning['hitStopSeconds']=constant('ContactStopSeconds')
    tuning['hitStopBudget']=constant('ContactStopBudget')
    return tuning


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
    """Compact alternating toe pivots, with knees following the support feet."""
    ready,spin,recover=[tuning[k] for k in ('readySeconds','spinSeconds','recoverSeconds')]
    stop=ready+spin
    progress=np.clip((times-ready)/spin,0.,1.)
    turns=abs(tuning['turnDegrees'])/360.
    angular=turns*old.arms.phase(progress)
    sign=np.sign(tuning['turnDegrees'])
    actor=sign*2*np.pi*angular
    ip,iq=body.world(body.idle)
    current,_=body.world(frames)
    goals,rots,poles={},{},{}
    for side,offset in [('l',0.),('r',.5)]:
        step=2*angular-offset
        whole=np.floor(step);phase=step-whole
        flight=np.clip((phase-.5)*2,0.,1.)
        centre=(whole+offset+.25)/2
        anchor=sign*2*np.pi*(centre+.5*smooth(flight))
        relative=anchor-actor
        yaw=R.from_euler('z',relative[:,None])
        lift=np.sin(np.pi*flight)**2
        # The ankle follows the toe, not an independently offset foot point.
        # Center toe anchors on the spin circle. A shared forward offset would
        # pull both toes toward the midline at opposing support phases.
        toe=yaw.apply(np.c_[(1 if side=='l' else -1)*18.*size*(1+.05*lift),np.zeros(len(times)),np.zeros(len(times))])
        foot,ball=body.ix['foot_'+side],body.ix['ball_'+side]
        toe[:,2]=ip[ball,2]+2.8*size*lift
        heel=np.where(phase<.5,-8.*np.sin(np.pi*phase*2)**2,4.*np.sin(np.pi*flight)**2)
        rotation=R.from_euler('z',relative[:,None])*R.from_euler('x',heel[:,None],degrees=True)*R.from_quat(iq[foot])
        # Stagger the step out and braking return on the same master clock.
        if side=='l':enter=(.02,.31);leave=(.12,.48)
        else:enter=(.24,.49);leave=(.01,.34)
        arrival=smooth((times-enter[0])/(enter[1]-enter[0]))
        departure=1.-smooth((times-stop-leave[0])/(leave[1]-leave[0]))
        weight=arrival*departure
        target=ip[ball]+(toe-ip[ball])*weight[:,None]
        first=np.clip((times-enter[0])/(enter[1]-enter[0]),0.,1.)
        last=np.clip((times-stop-leave[0])/(leave[1]-leave[0]),0.,1.)
        target[:,2]+=(np.sin(np.pi*first)**2+np.sin(np.pi*last)**2)*3.*size
        rotation=R.from_quat(c.slerp(iq[foot],rotation.as_quat(),weight[:,None]))
        toe_local=R.from_quat(iq[foot]).inv().apply(ip[ball]-ip[foot])
        goals[side]=target-rotation.apply(np.tile(toe_local,(len(times),1)))
        rots[side]=rotation
        thigh=current[:,body.ix['thigh_'+side]]
        knee_x=.65*goals[side][:,0]+.35*thigh[:,0]
        knee_x=np.maximum(knee_x,thigh[:,0]+2.*size) if side=='l' else np.minimum(knee_x,thigh[:,0]-2.*size)
        target_pole=np.c_[knee_x,np.maximum(goals[side][:,1],thigh[:,1])+42.*size,frames[:,body.hip,2]-28.*size]
        poles[side]=ip[body.ix['calf_'+side]]*(1-weight[:,None])+target_pole*weight[:,None]
    # Hip height belongs to the deliberate lower/rise curve. Do not append the
    # old per-frame pelvis drop, which would reintroduce a second crouch/bob.
    for side in 'lr':
        body.solve(frames,[n+'_'+side for n in ('thigh','calf','foot')],goals[side],poles[side],rots[side])


def arm(body,frames,side,goal,pole,amount,torso,turn_sign):
    """Transport a native bent elbow; roll the palm axially, never kink it."""
    ui,ei,hi=[body.ix[n+'_'+side] for n in ('upperarm','lowerarm','hand')]
    p,q=body.world(frames);ip,iq=body.world(body.idle)
    origin=p[:,ui]
    l1=np.linalg.norm(body.ref[ei,:3]);l2=np.linalg.norm(body.ref[hi,:3])
    direction=c.unit(goal-origin)
    distance=np.clip(np.linalg.norm(goal-origin,axis=1),abs(l1-l2)+.02,(l1+l2)*(.985 if side=='r' else .965))
    goal=origin+direction*distance[:,None]
    bend=pole-origin;bend=c.unit(bend-direction*np.sum(bend*direction,axis=1)[:,None])
    along=(l1*l1-l2*l2+distance*distance)/(2*distance)
    elbow=origin+direction*along[:,None]+bend*np.sqrt(np.maximum(0.,l1*l1-along*along))[:,None]
    upper,fore=elbow-origin,goal-elbow
    ref_u,ref_f=ip[ei]-ip[ui],ip[hi]-ip[ei]
    uq=c.frame(upper,fore)*c.frame(ref_u,ref_f).inv()*R.from_quat(iq[ui])
    fq=c.frame(fore,upper)*c.frame(ref_f,ref_u).inv()*R.from_quat(iq[ei])
    if side=='l':
        # Transport this mesh's bind axes through the actual clavicle. A free
        # arm has no grip-facing constraint: do not borrow the guard's elbow
        # roll or add a separate world-space thumb/palm alignment afterwards.
        parent=body.parents[ui]
        inherited_upper=R.from_quat(q[:,parent])*R.from_quat(body.ref[ui,3:7])
        neutral_upper=c.align(inherited_upper.apply(np.tile(body.ref[ei,:3],(len(frames),1))),upper)*inherited_upper
        idle_upper=c.align(ref_u,upper)*R.from_quat(iq[ui])
        uq=R.from_quat(c.slerp(idle_upper.as_quat(),neutral_upper.as_quat(),amount[:,None]))
        inherited=uq*R.from_quat(body.ref[ei,3:7])
        neutral_fore=c.align(inherited.apply(np.tile(body.ref[hi,:3],(len(frames),1))),fore)*inherited
        idle_fore=c.align(ref_f,fore)*R.from_quat(iq[ei])
        fq=R.from_quat(c.slerp(idle_fore.as_quat(),neutral_fore.as_quat(),amount[:,None]))
        wrist=R.from_quat(c.slerp(body.idle[hi,3:7],body.ref[hi,3:7],amount[:,None]))
        body.set_world_rotations(frames,{ui:uq,ei:fq,hi:fq*wrist})
        return
    # A straight supported wrist in its own native axes. Grip fingers and the
    # blade remain rigidly attached; only axial rotation changes palm facing.
    hand_bind=R.from_quat(body.tq[hi]);local_ref=R.from_quat(body.ref[hi,3:7])
    palm=hand_bind.inv().apply(body.tp[body.ix['middle_01_'+side]]-body.tp[hi])
    axis=c.unit(body.ref[hi,:3])
    neutral=c.align(local_ref.apply(palm),axis)*local_ref
    base=fq*neutral
    fore_axis=c.unit(fore)
    up=torso.apply(np.tile([0.,0.,1.],(len(frames),1)))
    tip=np.array(json.loads((ROOT/'SourceAssets/Kukri20261020/model.json').read_text())['tip_cm'])
    landmark=body.blade_local.apply(c.unit(tip))
    wanted=-turn_sign*c.unit(np.cross(fore_axis,up))
    v=base.apply(np.tile(landmark,(len(frames),1)))
    v=c.unit(v-fore_axis*np.sum(v*fore_axis,axis=1)[:,None])
    w=c.unit(wanted-fore_axis*np.sum(wanted*fore_axis,axis=1)[:,None])
    angle=np.unwrap(np.arctan2(np.sum(np.cross(v,w)*fore_axis,axis=1),np.sum(v*w,axis=1)))
    angle-=2*np.pi*round(float(np.median(angle))/(2*np.pi))
    # Smooth comfort limit; no quaternion +/-180 branch or hard per-frame clamp.
    limit=np.radians(115. if side=='r' else 85.)
    roll=limit*np.tanh(angle/limit)
    hand=(R.from_rotvec(fore_axis*roll[:,None])*base)
    if side=='r':
        # Share blade-facing pronation with the forearm; do not put all of the
        # reversed cutting orientation into the wrist. The elbow/hand endpoints
        # and the authored native grip remain fixed by this axial rotation.
        fq=R.from_rotvec(fore_axis*(.65*roll*amount)[:,None])*fq
    # Entry and recovery keep the current idle wrist and roll while the native
    # elbow plane and support rotation take over smoothly.
    idle_local=R.from_quat(body.idle[hi,3:7])
    hand=R.from_quat(c.slerp((fq*idle_local).as_quat(),hand.as_quat(),amount[:,None]))
    body.set_world_rotations(frames,{ui:uq,ei:fq,hi:hand})


def relaxed_free_hand(body,frames,ownership):
    """Relaxed cascade of fingers; no empty-object grip or chest guard fist."""
    fist=old.fingers.native_fist(body,json.loads(old.fingers.FIST_SOURCE.read_text()))
    curl={'thumb':.20,'index':.12,'middle':.18,'ring':.23,'pinky':.28}
    for i,name in enumerate(body.names):
        digit=name.split('_')[0]
        if not name.endswith('_l') or digit not in curl:continue
        relaxed=c.slerp(body.ref[i,3:7],fist[i,3:7],curl[digit])
        frames[:,i,3:7]=c.slerp(body.idle[i,3:7],relaxed,ownership[:,None])


def make_body(body,label,tuning,times,keys,poses):
    count=len(times);size=body.scale/94.
    frames=np.repeat(body.idle[None],count,axis=0)
    ip,iq=body.world(body.idle)
    ready,spin,recover=[tuning[k] for k in ('readySeconds','spinSeconds','recoverSeconds')]
    stop=ready+spin
    turn_sign=np.sign(tuning['turnDegrees'])
    ownership=smooth(times/.34)*(1.-smooth((times-stop)/recover))
    frames[:,body.hip,:3]=ip[body.hip]+spline(keys,[k['hip'] for k in poses],times)*size
    depth=json.loads((OUT/'motion.json').read_text())['lowering_cm']
    spin_u=np.clip((times-ready)/spin,0.,1.)
    rise_u=np.clip((times-stop)/recover,0.,1.)
    lowering=np.where(times<ready,smooth(times/ready),
        np.where(times<=stop,1.+(depth-1.)*smooth(spin_u),depth*(1.-smooth(rise_u))))
    frames[:,body.hip,2]=ip[body.hip,2]-lowering*size
    # Small horizontal transfer follows the alternating support; it adds no
    # vertical bounce and fades before the braking footwork.
    turns=abs(tuning['turnDegrees'])/360.
    support=-turn_sign*np.sin(4*np.pi*turns*old.arms.phase(spin_u))
    frames[:,body.hip,0]+=1.25*size*support*smooth(spin_u/.12)*(1.-smooth((spin_u-.82)/.18))
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
    forward=torso.apply(np.tile([0.,1.,0.],(count,1)))
    heading=R.from_euler('z',np.arctan2(-forward[:,0],forward[:,1])[:,None])
    extension=smooth((times-.10)/.36)*(1.-smooth((times-stop)/(.70*recover)))
    scap=spline(keys,[k['scapula'] for k in poses],times)
    desired={}
    idle_torso=R.from_quat(iq[body.ix['spine_03']])*R.from_quat(body.tq[body.ix['spine_03']]).inv()
    for side,index in [('r',0),('l',1)]:
        i=body.ix['clavicle_'+side]
        base=torso*idle_torso.inv()*R.from_quat(iq[i])
        delta=R.from_euler('z',(scap[:,index]*ownership)[:,None],degrees=True)
        if side=='r':
            # The clavicle participates in the shoulder-height reach.
            delta=R.from_euler('y',(6.*extension)[:,None],degrees=True)*delta
        desired[i]=torso*delta*torso.inv()*base
    body.set_world_rotations(frames,desired)
    p,_,torso=old.arms.chest(body,frames)
    for side in 'rl':
        ui,ei,hi=[body.ix[n+'_'+side] for n in ('upperarm','lowerarm','hand')]
        length=np.linalg.norm(body.ref[ei,:3])+np.linalg.norm(body.ref[hi,:3])
        # Right arm stays at shoulder height even while the torso pitches into
        # its crouch. The free arm follows gravity with only a little chest lean.
        arm_frame=heading if side=='r' else R.from_quat(c.slerp(heading.as_quat(),torso.as_quat(),.20))
        arm_frame=R.from_quat(c.slerp(torso.as_quat(),arm_frame.as_quat(),ownership[:,None]))
        idle_hand=idle_torso.inv().apply(ip[hi]-ip[ui])
        values=[idle_hand if k['right' if side=='r' else 'left'] is None else
                np.array(k['right' if side=='r' else 'left'])*length for k in poses]
        hand=spline(keys,values,times)
        # Both hand paths are shoulder-relative. The free arm stays outboard,
        # so the old chest-front projection must not push it into a guard.
        origin=p[:,ui]
        goal=origin+arm_frame.apply(hand)
        idle_elbow=idle_torso.inv().apply(ip[ei]-ip[ui])
        # The elbow follows the draw/release before the wrist. Keep its bend
        # plane outside the torso rather than switching between arbitrary poles.
        if side=='r':
            local_pole=np.c_[-np.full(count,.48),-turn_sign*np.full(count,.06),-np.full(count,.17)]*length
        else:
            balance=smooth((times-ready)/(.35*spin))*(1.-smooth((times-stop)/recover))
            local_pole=np.c_[.18+.04*balance,.15+.025*balance,-np.full(count,.47)]*length
        pole=idle_elbow*(1-ownership[:,None])+local_pole*ownership[:,None]
        arm(body,frames,side,goal,p[:,ui]+arm_frame.apply(pole),ownership,arm_frame,turn_sign)
    held=old.grip(body)
    relaxed_free_hand(body,frames,ownership)
    old.right_fingers(body,frames,held)
    native.native_twists(body,frames)
    idle_twists=body.idle[None].copy()
    native.native_twists(body,idle_twists)
    for i,name in enumerate(body.names):
        if name.startswith(('upperarm_twist_','lowerarm_twist_')):
            # Final hand/arm rotations already contain their entry/exit blend.
            # Fade only the idle helper offset, not the completed twist again.
            offset=R.from_quat(body.idle[i,3:7])*R.from_quat(idle_twists[0,i,3:7]).inv()
            correction=R.from_quat(c.slerp([0.,0.,0.,1.],offset.as_quat(),(1.-ownership)[:,None]))
            frames[:,i,3:7]=(correction*R.from_quat(frames[:,i,3:7])).as_quat()
    frames[0]=body.idle;frames[-1]=body.idle
    old.right_fingers(body,frames,held)
    return frames


def main():
    cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    tuning=effective_tuning()
    times,cuts,keys,poses=timeline(tuning)
    report=dict(version='V13 shoulder-height reach and relaxed native left wrist',runtime_tested=False,rendered=False,
        tuning=tuning,reference_motion_imported=False,gameplay_changed=False,first_person_changed=False,
        design='motion.json',previous_animation_frames_used=False,base_authoring='V10 rig and timing utilities',
        user_direction='Extend the weapon arm at shoulder height; correct the free arm and wrist twist; preserve positive two-turn spin, speed and progressive squat',
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
                rate_num=RATE,rate_den=1,duration=(end-start-1)/RATE,
                runtime_duration=float(times[end-1]-times[start]),
                source='Original native-body V13 authoring following user direction',
                adaptation='Shoulder-height right reach with soft elbow and native grip; gravity-led relaxed left arm with bind-local wrist; coherent twist helpers; V12 signed footwork, 1.5x spin and monotone lowering retained.')
        (OUT/(label+'-actions.json')).write_text(json.dumps(dict(mesh=data['mesh'],names=body.names,parents=body.parents,clips=clips),separators=(',',':')))
        report['bodies'][label]=dict(mesh=data['mesh'],idle_asset=data['idle_asset'],
            previous_roles={role:active['clips']['Kukri.FullBody.'+role] for role in ROLES},
            authoring_reference_source=data['authoring_reference_source'],
            clips={role:dict(frames=len(v['frames']),rate_num=v['rate_num'],rate_den=v['rate_den'],duration=v['duration']) for role,v in clips.items()})
        print('KUKRI_WINDMILL_SHOULDER_AUTHORED '+label,flush=True)
    (OUT/'authoring.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__':main()
