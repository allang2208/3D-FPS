"""Native single-hand uppercut from the user's Meshy Charged_Upward_Slash.

Keep the donor's whole right arm, torso and stepping performance. Accommodate
its very bent empty wrist to the real Kukri grip, and finish on the live carry.
No edits to the first-person clip, combat clock, capsule lunge or other roles.
"""
import importlib.util
import json
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.spatial.transform import Rotation as R

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m

shared=module('meshy_grip_source',Path('SourceAssets/KukriMeshyWhirlwind20261025/author.py'))
c=shared.c
SOURCE=json.loads((OUT/'source.json').read_text())
SI={n:i for i,n in enumerate(SOURCE['names'])}
SR=np.asarray(SOURCE['reference_world'])
SF=np.asarray(SOURCE['frames'])
RATE=120
LENGTH=38/30
TIMES=np.arange(round(LENGTH*RATE)+1)/RATE
CLOCK=np.array([0.,.08,.16,.24,.29,.30,.350,.433,.57,.72,.96,1.10,LENGTH])
DONOR=np.array([0.,.12,.45,.82,.95,1.,1.075,1.20,1.40,1.70,2.20,2.65,SOURCE['duration']])


def source_motion():
    times=PchipInterpolator(CLOCK,DONOR)(TIMES)
    world=np.array([c.sample(SF,float(t),SOURCE['rate']) for t in times])
    hip=SI['pelvis']
    forward=(R.from_quat(SF[:,hip,3:7])*R.from_quat(SR[hip,3:7]).inv()).apply(np.tile([0.,1.,0.],(len(SF),1)))
    yaw=np.unwrap(np.arctan2(-forward[:,0],forward[:,1]))
    source_yaw=np.interp(times,np.arange(len(SF))/SOURCE['rate'],yaw)
    # The donor turns about 190 degrees away from its initial stance. Retain a
    # limited coil/release for a forward-facing attack; do not rotate the actor.
    coil=np.radians(26.)*np.tanh((source_yaw-yaw[0])/np.radians(48.))
    orient=R.from_euler('z',(coil-source_yaw)[:,None])
    # Remove gross travel once. Preserve the smaller pelvis sway; the existing
    # capsule lunge continues to own displacement and obstruction response.
    landmarks=np.array([0.,.50,1.40,1.80,2.60,SOURCE['duration']])
    path=np.array([c.sample(SF,float(t),SOURCE['rate'])[hip,:2] for t in landmarks])
    root_path=PchipInterpolator(landmarks,path)(times)
    for j in range(world.shape[1]):
        world[:,j,:2]-=root_path
        world[:,j,:3]=orient.apply(world[:,j,:3])
        world[:,j,3:7]=(orient*R.from_quat(world[:,j,3:7])).as_quat()
    return world,times


def anatomical_rotation(body,name,world):
    i,j=body.ix[name],SI[name]
    child=body.axis_child(name)
    if name.startswith('hand_'):
        side=name[-1];end='RightHand_End' if side=='r' else 'LeftHand_End'
        a=c.frame(SR[SI[end],:3]-SR[j,:3],np.array([0.,1.,0.]))
        b=c.frame(body.tp[body.ix['middle_01_'+side]]-body.tp[i],body.tp[body.ix['index_01_'+side]]-body.tp[body.ix['pinky_01_'+side]])
    elif child and child in SI:
        av=SR[SI[child],:3]-SR[j,:3];bv=body.tp[body.ix[child]]-body.tp[i]
        sa=np.array([0.,1.,0.]);ta=body.target_forward
        if abs(c.unit(av)@sa)>.92:sa=np.array([0.,0.,1.])
        if abs(c.unit(bv)@ta)>.92:ta=np.array([0.,0.,1.])
        a,b=c.frame(av,sa),c.frame(bv,ta)
    else:a=b=R.identity()
    mount=R.from_quat(SR[j,3:7]).inv()*a*b.inv()*R.from_quat(body.tq[i])
    return R.from_quat(world[:,j,3:7])*mount


def arm_chain(body,frames,side,goal,pole,hand):
    p,q=body.world(frames)
    ui,ei,hi=[body.ix[a+'_'+side] for a in ('upperarm','lowerarm','hand')]
    origin=p[:,ui]
    l1=np.linalg.norm(body.ref[ei,:3]);l2=np.linalg.norm(body.ref[hi,:3])
    axis=c.unit(goal-origin)
    reach=np.clip(np.linalg.norm(goal-origin,axis=1),abs(l1-l2)+.03,(l1+l2)*.976)
    goal=origin+axis*reach[:,None]
    bend=pole-origin;bend=c.unit(bend-axis*np.sum(bend*axis,axis=1)[:,None])
    along=(l1*l1-l2*l2+reach*reach)/(2*reach)
    elbow=origin+axis*along[:,None]+bend*np.sqrt(np.maximum(0.,l1*l1-along*along))[:,None]
    upper,fore=elbow-origin,goal-elbow
    ru=body.tp[ei]-body.tp[ui];rf=body.tp[hi]-body.tp[ei]
    uq=c.frame(upper,fore)*c.frame(ru,rf).inv()*R.from_quat(body.tq[ui])
    fq=c.frame(fore,upper)*c.frame(rf,ru).inv()*R.from_quat(body.tq[ei])
    body.set_world_rotations(frames,{ui:uq,ei:fq,hi:hand})


def support_wrist(body,frames,side):
    hi=body.ix['hand_'+side];ref=R.from_quat(body.ref[hi,3:7])
    palm=R.from_quat(body.tq[hi]).inv().apply(body.tp[body.ix['middle_01_'+side]]-body.tp[hi])
    axis=c.unit(body.ref[hi,:3])
    neutral=c.align(ref.apply(palm),axis)*ref
    delta=(R.from_quat(frames[:,hi,3:7])*neutral.inv()).as_quat()
    delta=np.where(delta[:,3:]<0,-delta,delta)
    twist=c.unit(np.c_[(delta[:,:3]@axis)[:,None]*axis,delta[:,3]])
    angle=np.unwrap(2*np.arctan2(twist[:,:3]@axis,twist[:,3]))
    angle-=2*np.pi*round(float(np.median(angle))/(2*np.pi))
    # A smooth end range, not a hard 180-degree branch or a per-frame wrist flip.
    a=np.abs(angle);soft=np.minimum(a,np.radians(85.))+np.radians(25.)*np.tanh(np.maximum(0.,a-np.radians(85.))/np.radians(25.))
    tw=R.from_rotvec(axis[None]*(np.sign(angle)*soft)[:,None])
    swing=R.from_quat(delta)*R.from_quat(twist).inv();v=swing.as_rotvec()
    a=np.linalg.norm(v,axis=1);limit=np.radians(27. if side=='r' else 30.)
    swing=R.from_rotvec(v*(limit*np.tanh(a/limit)/np.maximum(a,1e-9))[:,None])
    frames[:,hi,3:7]=(swing*tw*neutral).as_quat()


def upper_twists(body,frames):
    # Distribute the native shoulder's axial turn along its own helper stations.
    for side in 'lr':
        ui,ei=[body.ix[a+'_'+side] for a in ('upperarm','lowerarm')]
        reference=R.from_quat(body.ref[ui,3:7]);current=R.from_quat(frames[:,ui,3:7])
        axis=c.unit(body.ref[ei,:3]);ref_axis=reference.apply(axis)
        swing=c.align(np.tile(ref_axis,(len(frames),1)),current.apply(np.tile(axis,(len(frames),1))))
        delta=reference.inv()*swing.inv()*current
        v=delta.as_rotvec()
        for suffix in ('01','02'):
            key='upperarm_twist_'+suffix+'_'+side
            if key not in body.ix:continue
            i=body.ix[key];weight=np.clip(np.linalg.norm(body.ref[i,:3])/np.linalg.norm(body.ref[ei,:3]),0.,1.)
            frames[:,i,3:7]=(R.from_rotvec(-(1-weight)*v)*R.from_quat(body.ref[i,3:7])).as_quat()
    return frames


def build_body(label,data,world):
    body=c.Body(data);size=body.scale/94.;n=len(TIMES)
    ip,iq=body.world(body.idle)
    scale=np.mean([sum(np.linalg.norm(body.tp[body.ix[b+'_'+s]]-body.tp[body.ix[a+'_'+s]]) for a,b in [('thigh','calf'),('calf','foot')])/
        sum(np.linalg.norm(SR[SI[b+'_'+s],:3]-SR[SI[a+'_'+s],:3]) for a,b in [('thigh','calf'),('calf','foot')]) for s in 'lr'])
    floor=np.mean([body.tp[body.ix['ball_'+s],2]-SR[SI['ball_'+s],2]*scale for s in 'lr'])
    origin=np.r_[ip[body.hip,:2],floor]
    frames=np.repeat(body.ref[None],n,axis=0)
    names=['pelvis','spine_01','spine_02','spine_03','neck_01','head']+[a+'_'+s for s in 'lr' for a in ('clavicle','thigh','calf','foot','ball')]
    desired={body.ix[name]:anatomical_rotation(body,name,world) for name in names}
    body.set_world_rotations(frames,desired)
    frames[:,body.hip,:3]=world[:,SI['pelvis'],:3]*scale+origin
    enter=c.ease(TIMES/.18);leave=c.ease((TIMES-.94)/(LENGTH-.94));weight=enter*(1-leave)
    frames=c.blend(np.repeat(body.idle[None],n,axis=0),frames,weight[:,None,None])
    goals={};poles={};rotations={}
    for side in 'lr':
        foot=body.ix['foot_'+side]
        goal=world[:,SI['foot_'+side],:3]*scale+origin
        ein=(.0,.15) if side=='l' else (.055,.25)
        eout=(.89,1.10) if side=='l' else (1.04,LENGTH)
        win=c.ease((TIMES-ein[0])/(ein[1]-ein[0]));wout=c.ease((TIMES-eout[0])/(eout[1]-eout[0]))
        gw=win*(1-wout)
        goals[side]=ip[foot]+(goal-ip[foot])*gw[:,None]
        # Feet join/leave on separate lifted arcs, with zero endpoint velocity.
        goals[side][:,2]+=size*(4*np.sin(np.pi*win)**2+5*np.sin(np.pi*wout)**2)
        poles[side]=ip[body.ix['calf_'+side]]+(world[:,SI['calf_'+side],:3]*scale+origin-ip[body.ix['calf_'+side]])*gw[:,None]
        rotations[side]=R.from_quat(c.slerp(np.tile(iq[foot],(n,1)),desired[foot].as_quat(),gw[:,None]))
    shared.steps.fit_legs(body,frames,goals,rotations,poles)

    p,q,torso=shared.arms.chest(body,frames)
    src_torso=R.from_quat(world[:,SI['spine_03'],3:7])*R.from_quat(SR[SI['spine_03'],3:7]).inv()
    carry=torso*src_torso.inv()
    _,_,idle_torso=shared.arms.chest(body,body.idle[None])
    front=shared.chest_envelope(body,label)
    middle=(p[:,body.ix['upperarm_l']]+p[:,body.ix['upperarm_r']])*.5
    arm_weight=c.ease(TIMES/.16)*(1-c.ease((TIMES-.91)/(LENGTH-.91)))
    for side in 'rl':
        ui,ei,hi=[body.ix[a+'_'+side] for a in ('upperarm','lowerarm','hand')]
        su,se,sh=[SI[a+'_'+side] for a in ('upperarm','lowerarm','hand')]
        arm_scale=(np.linalg.norm(body.ref[ei,:3])+np.linalg.norm(body.ref[hi,:3]))/(np.linalg.norm(SR[se,:3]-SR[su,:3])+np.linalg.norm(SR[sh,:3]-SR[se,:3]))
        raw_goal=p[:,ui]+carry.apply(world[:,sh,:3]-world[:,su,:3])*arm_scale
        raw_pole=p[:,ui]+carry.apply(world[:,se,:3]-world[:,su,:3])*arm_scale
        idle_hand=idle_torso.inv().apply(ip[hi]-ip[ui])[0]
        idle_elbow=idle_torso.inv().apply(ip[ei]-ip[ui])[0]
        initial=p[:,ui]+torso.apply(np.tile(idle_hand,(n,1)))
        initial_pole=p[:,ui]+torso.apply(np.tile(idle_elbow,(n,1)))
        hand=carry*anatomical_rotation(body,'hand_'+side,world)
        if side=='l':
            v=src_torso.inv().apply(world[:,sh,:3]-world[:,SI['spine_03'],:3])
            offset=np.c_[(12+5*np.tanh(v[:,0]/.2))*size,np.full(n,front+9*size)+2*size*np.tanh(v[:,1]/.25),(-16+3*np.tanh(v[:,2]/.2))*size]
            raw_goal=middle+torso.apply(offset)
            raw_pole=p[:,ui]+torso.apply(np.tile([18.,13.,-27.],(n,1))*size)
        goal=initial+(raw_goal-initial)*arm_weight[:,None]
        pole=initial_pole+(raw_pole-initial_pole)*arm_weight[:,None]
        arm_chain(body,frames,side,goal,pole,hand)
        pp,qq=body.world(frames)
        palm=R.from_quat(body.tq[hi]).inv().apply(body.tp[body.ix['middle_01_'+side]]-body.tp[hi])
        fore=c.unit(pp[:,hi]-pp[:,ei]);up=torso.apply(np.tile([0.,0.,1.],(n,1)))
        forward=torso.apply(np.tile([0.,1.,0.],(n,1)))
        if side=='r':
            rise=c.ease((TIMES-.29)/.12)*(1-c.ease((TIMES-.57)/.22))
            tip=forward*(1-.68*rise[:,None])+up*(.08+.98*rise[:,None])
            along=c.unit(fore+.055*up)
            parallel=np.abs(np.sum(c.unit(tip)*along,axis=1))>.94
            tip[parallel]=up[parallel]
            guide=c.frame(along,tip)*c.frame(palm,body.blade_local.apply([0.,0.,1.])).inv()
            influence=.80*c.ease((TIMES-.20)/.10)*(1-c.ease((TIMES-.63)/.20))
            hand=R.from_quat(c.slerp(hand.as_quat(),guide.as_quat(),influence[:,None]))
        else:
            across=R.from_quat(body.tq[hi]).inv().apply(body.tp[body.ix['index_01_l']]-body.tp[body.ix['pinky_01_l']])
            hand=c.frame(c.unit(fore+.06*up),up)*c.frame(palm,across).inv()
        body.set_world_rotations(frames,{hi:hand})
        support_wrist(body,frames,side)
        # The complete arm reaches the exact current idle, including its roll.
        for index in (ui,ei,hi):
            frames[:,index,3:7]=c.slerp(np.tile(body.idle[index,3:7],(n,1)),frames[:,index,3:7],arm_weight[:,None])
    frames=upper_twists(body,body.twists(frames))
    for i,name in enumerate(body.names):
        if '_twist_' in name and name.startswith(('upperarm','lowerarm')):
            frames[:,i,3:7]=c.slerp(np.tile(body.idle[i,3:7],(n,1)),frames[:,i,3:7],arm_weight[:,None])
    fist=shared.fingers.native_fist(body,json.loads(shared.fingers.FIST_SOURCE.read_text()))
    for i,name in enumerate(body.names):
        digit=name.split('_')[0]
        if name.endswith('_l') and digit in ('thumb','index','middle','ring','pinky'):
            delay={'pinky':0.,'ring':.006,'middle':.012,'index':.020,'thumb':.045}[digit]
            w=c.ease((TIMES-delay)/.15)*(1-c.ease((TIMES-.83)/(LENGTH-.83)))
            frames[:,i,3:7]=c.slerp(np.tile(body.idle[i,3:7],(n,1)),fist[i,3:7],w[:,None])
    frames[0]=body.idle;frames[-1]=body.idle
    held=shared.grip(body);shared.right_fingers(body,frames,held)
    for k in range(1,n):
        frames[k,:,3:7]*=np.where(np.sum(frames[k-1,:,3:7]*frames[k,:,3:7],axis=1)<0,-1.,1.)[:,None]
    return frames,dict(source_scale_cm=scale,torso_front_envelope_cm=front,source_right_arm=True,native_grip=True)


def main():
    cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    world,source_times=source_motion()
    report=dict(source=SOURCE['original'],source_sha256=SOURCE['sha256'],source_clip=SOURCE['clip'],source_seconds=SOURCE['duration'],
        target_clock=CLOCK.tolist(),source_clock=DONOR.tolist(),source_time_samples=source_times.tolist(),
        contact_seconds=.350,release_seconds=.433,runtime_tested=False,rendered=False,gameplay_changed=False,first_person_changed=False,bodies={})
    for label,data in c.INPUT['targets'].items():
        active=cfg if label=='jason' else cfg['body_variants'][label]
        if active['clips']['Kukri.FullBody.Idle']!=data['idle_asset']:
            raise RuntimeError('Active idle changed: capture the current boundary before authoring '+label)
        frames,detail=build_body(label,data,world)
        clip=dict(rate=RATE,frames=frames.tolist(),loop=False,contact=.350/LENGTH,release=.433/LENGTH,
            source='User Meshy GLB (3) / Charged_Upward_Slash',
            adaptation='Source right shoulder/elbow rising cut, whole torso and legs; 0.350 contact / 0.433 release, root travel removed and forward-facing coil; native blade grip and fingers, supported wrist swing/twist, upper/lower arm helpers, left guard counterbalance; sequential steps and exact carry endpoints.')
        (OUT/(label+'-actions.json')).write_text(json.dumps(dict(mesh=data['mesh'],names=data['names'],parents=data['parents'],clips={'Uppercut':clip}),separators=(',',':')))
        report['bodies'][label]=dict(mesh=data['mesh'],previous_uppercut=active['clips']['Kukri.FullBody.Uppercut'],idle_asset=data['idle_asset'],frames=len(frames),rate=RATE,seconds=LENGTH,**detail)
        print('KUKRI_MESHY_UPPERCUT_AUTHORED '+label,flush=True)
    (OUT/'authoring.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__':main()
