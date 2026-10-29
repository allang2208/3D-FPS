"""V16: shoulder reach starts with the world turn, without a separate extension.

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
        if side=='l':enter=(.02,.31);leave=(.08,.32)
        else:enter=(.24,.49);leave=(.01,.26)
        arrival=smooth((times-enter[0])/(enter[1]-enter[0]))
        departure=1.-smooth((times-stop-leave[0])/(leave[1]-leave[0]))
        weight=arrival*departure
        target=ip[ball]+(toe-ip[ball])*weight[:,None]
        first=np.clip((times-enter[0])/(enter[1]-enter[0]),0.,1.)
        last=np.clip((times-stop-leave[0])/(leave[1]-leave[0]),0.,1.)
        target[:,2]+=(np.sin(np.pi*first)**2*3.+np.sin(np.pi*last)**2*2.)*size
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
    # Fit the real mounted blade to a horizontal, outboard cutting direction.
    # Keep its contact transform and native fingers fixed; the forearm absorbs
    # the axial roll so the wrist supplies only the remaining small swing.
    _,mount=native.blade_mount(body)
    tip=c.unit(np.array(json.loads((ROOT/'SourceAssets/Kukri20261020/model.json').read_text())['tip_cm']))
    wanted=torso.apply(np.tile([-np.cos(np.radians(40.)),-turn_sign*np.sin(np.radians(40.)),0.],(len(frames),1)))
    wanted=c.unit(wanted*np.array([1.,1.,0.]))
    face=np.tile([0.,0.,-1.],(len(frames),1))
    blade=c.frame(wanted,face)*c.frame(tip,np.array([0.,1.,0.])).inv()
    target_hand=blade*mount.inv()
    supported=target_hand*R.from_quat(body.ref[hi,3:7]).inv()
    fitted_fore=c.align(supported.apply(np.tile(body.ref[hi,:3],(len(frames),1))),fore)*supported
    # The previous idle-derived elbow plane carried almost 180 degrees of
    # axial roll against this grip. Transport the native elbow frame back up
    # the arm, rather than putting that turn into the forearm joint/skin.
    supported_upper=fitted_fore*R.from_quat(body.ref[ei,3:7]).inv()
    fitted_upper=c.align(supported_upper.apply(np.tile(body.ref[ei,:3],(len(frames),1))),upper)*supported_upper
    uq=R.from_quat(c.slerp(uq.as_quat(),fitted_upper.as_quat(),amount[:,None]))
    inherited=uq*R.from_quat(body.idle[ei,3:7])
    base_fore=c.align(inherited.apply(np.tile(body.ref[hi,:3],(len(frames),1))),fore)*inherited
    fq=R.from_quat(c.slerp(base_fore.as_quat(),fitted_fore.as_quat(),amount[:,None]))
    hand=R.from_quat(c.slerp((fq*R.from_quat(body.idle[hi,3:7])).as_quat(),target_hand.as_quat(),amount[:,None]))
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


def deploy_weapon_chain(body,frames,times,ready,release):
    """One native-chain transition while the actor starts its first turn.

    Interpolating changing IK pole/roll solutions can swap rotation branches.
    Capture the compact start and deployed end once, then carry every native
    parent-space joint along that same turn-phase transition.
    """
    first=int(np.searchsorted(times,ready-1e-8))
    last=int(np.flatnonzero(release>=1.-1e-8)[0])
    indices=np.arange(first,last+1)
    start,end=frames[first].copy(),frames[last].copy()
    for i,name in enumerate(body.names):
        if not name.endswith('_r') or not name.startswith(('clavicle_','upperarm_','lowerarm_','hand_')):continue
        if '_twist_' in name:continue
        frames[indices,i,3:7]=c.slerp(start[i,3:7],end[i,3:7],release[indices,None])


def recover_native_arms(body,frames,times,stop,duration):
    """Return the native chains from one captured pose in parent space."""
    indices=np.flatnonzero(times>=stop-1e-8)
    blend=smooth((times[indices]-stop)/duration)
    first=frames[indices[0]].copy()
    for i,name in enumerate(body.names):
        if not name.endswith(('_l','_r')):continue
        if not name.startswith(('clavicle_','upperarm_','lowerarm_','hand_',
                                'thumb_','index_','middle_','ring_','pinky_')):continue
        if '_twist_' in name:continue  # Derived once from the final arm below.
        frames[indices,i,3:7]=c.slerp(first[i,3:7],body.idle[i,3:7],blend[:,None])


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
    supported_rise=np.clip((rise_u-.07)/.93,0.,1.)
    lowering=np.where(times<ready,smooth(times/ready),
        np.where(times<=stop,1.+(depth-1.)*smooth(spin_u),depth*(1.-smooth(supported_rise))))
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
    # Use the same turn phase as the actor/feet, so no reach is baked into the
    # stationary windup. Deploy through the first part of turn one, then keep
    # the existing moving sweep and recovery rather than pausing at full reach.
    phase=old.arms.phase(spin_u)
    turn_degrees=abs(tuning['turnDegrees'])*phase
    release={'r':smooth(turn_degrees/110.),'l':smooth(turn_degrees/145.)}
    arm_amount={side:ownership*release[side] for side in 'rl'}
    extension=release['r']*(1.-smooth((times-stop)/(.70*recover)))
    scap=spline(keys,[k['scapula'] for k in poses],times)
    desired={}
    idle_torso=R.from_quat(iq[body.ix['spine_03']])*R.from_quat(body.tq[body.ix['spine_03']]).inv()
    for side,index in [('r',0),('l',1)]:
        i=body.ix['clavicle_'+side]
        base=torso*idle_torso.inv()*R.from_quat(iq[i])
        delta=R.from_euler('z',(scap[:,index]*arm_amount[side])[:,None],degrees=True)
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
        arm_frame=R.from_quat(c.slerp(torso.as_quat(),arm_frame.as_quat(),arm_amount[side][:,None]))
        idle_hand=idle_torso.inv().apply(ip[hi]-ip[ui])
        values=[idle_hand if k['right' if side=='r' else 'left'] is None else
                np.array(k['right' if side=='r' else 'left'])*length for k in poses]
        hand=spline(keys,values,times)
        # Keep the native folded arm during the windup. Only a small draw-back
        # accompanies torso loading; the hand opens out as the turn begins.
        compact=np.tile(idle_hand,(count,1))
        if side=='r':
            load=smooth(times/(ready*.75))
            compact+=np.array([-.025,-.060,-.020])*length*load[:,None]
        hand=compact+(hand-compact)*release[side][:,None]
        # Both hand paths are shoulder-relative. The free arm stays outboard,
        # so the old chest-front projection must not push it into a guard.
        origin=p[:,ui]
        goal=origin+arm_frame.apply(hand)
        idle_elbow=idle_torso.inv().apply(ip[ei]-ip[ui])
        # The elbow follows the draw/release before the wrist. Keep its bend
        # plane outside the torso rather than switching between arbitrary poles.
        if side=='r':
            local_pole=np.c_[-np.full(count,.48),-turn_sign*np.full(count,.30),-np.full(count,.04)]*length
        else:
            balance=smooth((times-ready)/(.35*spin))*(1.-smooth((times-stop)/recover))
            local_pole=np.c_[.15+.035*balance,.22+.025*balance,-np.full(count,.45)]*length
        amount=arm_amount[side]
        pole=idle_elbow*(1-amount[:,None])+local_pole*amount[:,None]
        pole_world=p[:,ui]+arm_frame.apply(pole)
        arm(body,frames,side,goal,pole_world,amount,arm_frame,turn_sign)
    deploy_weapon_chain(body,frames,times,ready,release['r'])
    held=old.grip(body)
    relaxed_free_hand(body,frames,arm_amount['l'])
    recover_native_arms(body,frames,times,stop,recover)
    old.right_fingers(body,frames,held)
    native.native_twists(body,frames)
    idle_twists=body.idle[None].copy()
    native.native_twists(body,idle_twists)
    for i,name in enumerate(body.names):
        if name.startswith(('upperarm_twist_','lowerarm_twist_')):
            # Final hand/arm rotations already contain their entry/exit blend.
            # Fade only the idle helper offset, not the completed twist again.
            offset=R.from_quat(body.idle[i,3:7])*R.from_quat(idle_twists[0,i,3:7]).inv()
            amount=arm_amount[name[-1]]
            correction=R.from_quat(c.slerp([0.,0.,0.,1.],offset.as_quat(),(1.-amount)[:,None]))
            frames[:,i,3:7]=(correction*R.from_quat(frames[:,i,3:7])).as_quat()
    frames[0]=body.idle;frames[-1]=body.idle
    old.right_fingers(body,frames,held)
    return frames


def main():
    cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    tuning=effective_tuning()
    times,cuts,keys,poses=timeline(tuning)
    report=dict(version='V16 horizontal blade and coherent free-arm recovery',runtime_tested=False,rendered=False,
        tuning=tuning,reference_motion_imported=False,gameplay_changed=False,first_person_changed=False,
        design='motion.json',previous_animation_frames_used=False,base_authoring='V10 rig and timing utilities',
        user_direction='Third-person only: hold the blade horizontal and outward; correct left arm twist and displacement during recovery; preserve simultaneous reach and spin',
        arm_deploy_degrees={'right':110.,'left':145.},
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
                source='Original native-body V16 authoring following user direction',
                adaptation='Horizontal outboard blade from the actual fixed grip; forearm roll with a softly bent elbow; one parent-space left-arm return to native idle; simultaneous reach and spin, progressive squat and gameplay clock retained.')
        (OUT/(label+'-actions.json')).write_text(json.dumps(dict(mesh=data['mesh'],names=body.names,parents=body.parents,clips=clips),separators=(',',':')))
        report['bodies'][label]=dict(mesh=data['mesh'],idle_asset=data['idle_asset'],
            previous_roles={role:active['clips']['Kukri.FullBody.'+role] for role in ROLES},
            authoring_reference_source=data['authoring_reference_source'],
            clips={role:dict(frames=len(v['frames']),rate_num=v['rate_num'],rate_den=v['rate_den'],duration=v['duration']) for role,v in clips.items()})
        print('KUKRI_WINDMILL_GRIP_AUTHORED '+label,flush=True)
    (OUT/'authoring.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__':main()
