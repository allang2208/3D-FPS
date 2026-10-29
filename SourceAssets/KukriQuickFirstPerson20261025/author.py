"""Transfer the installed FPS quick melee's two arms, palms and free fingers.

Keep the left jab/open/retract and the right pommel cock/strike/rebound on the
same one-second clock. Fit native shoulders and bone lengths, without copying
the camera transform or independently animating the blade against the fist.
"""
import importlib.util
import json
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation as R

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m

shared=module('quick_native_grip',Path('SourceAssets/KukriMeshyWhirlwind20261025/author.py'))
upper=module('quick_native_twists',Path('SourceAssets/KukriMeshyUppercut20261025/author.py'))
c=shared.c
DATA=json.loads((OUT/'inputs.json').read_text())
SOURCE=DATA['native'];SI={n:i for i,n in enumerate(SOURCE['names'])}
SR=np.asarray(SOURCE['reference_world']);SF=np.asarray(SOURCE['quick']['frames'])
RATE=120;LENGTH=1.;CONTACT=11/30;RELEASE=CONTACT+.12
TIMES=np.arange(121)/RATE
C=R.from_euler('z',180,degrees=True)


def palm_mount(body,side):
    sh=SI['hand_'+side];th=body.ix['hand_'+side]
    sq=R.from_quat(SR[sh,3:7]);tq=R.from_quat(body.tq[th])
    a=np.array([sq.inv().apply(SR[SI[d+'_01_'+side],:3]-SR[sh,:3]) for d in ('index','middle','pinky')])
    b=np.array([tq.inv().apply(body.tp[body.ix[d+'_01_'+side]]-body.tp[th]) for d in ('index','middle','pinky')])
    rot=c.frame(b[1],b[0]-b[2])*c.frame(a[1],a[0]-a[2]).inv()
    return rot,b.mean(0)-rot.apply(a.mean(0))


def free_fingers(body):
    """Transfer every left digit frame, including the FPS fist opening beat."""
    mount,offset=palm_mount(body,'l');sh=SI['hand_l'];th=body.ix['hand_l']
    source_hand=R.from_quat(SF[:,sh,3:7]);target_hand=R.from_quat(body.tq[th])
    transfer=target_hand*mount*source_hand.inv()
    frames=np.repeat(body.ref[None],len(SF),axis=0);desired={}
    for digit in ('thumb','index','middle','ring','pinky'):
        chain=[f'{digit}_{k:02d}_l' for k in (1,2,3)]
        for k,name in enumerate(chain):
            a,b=(k,k+1) if k<2 else (1,2)
            source_axis=R.from_quat(SR[SI[name],3:7]).inv().apply(SR[SI[chain[b]],:3]-SR[SI[chain[a]],:3])
            target_axis=R.from_quat(body.tq[body.ix[name]]).inv().apply(body.tp[body.ix[chain[b]]]-body.tp[body.ix[chain[a]]])
            desired[body.ix[name]]=transfer*R.from_quat(SF[:,SI[name],3:7])*c.align(target_axis,source_axis)
    body.set_world_rotations(frames,desired)
    for digit in ('thumb','index','middle','ring','pinky'):
        chain=[f'{digit}_{k:02d}_l' for k in (1,2,3)]
        points=[body.tp[th]+target_hand.apply(mount.apply(source_hand.inv().apply(SF[:,SI[name],:3]-SF[:,sh,:3]))+offset) for name in chain]
        body.solve(frames,chain,points[2],points[1],desired[body.ix[chain[2]]])
    for i,name in enumerate(body.names):
        par=body.parents[i]
        if name.endswith('_l') and '_half_' in name and par in desired:
            delta=R.from_quat(body.ref[par,3:7]).inv()*R.from_quat(frames[:,par,3:7])
            frames[:,i,3:7]=(R.from_rotvec(-.5*delta.as_rotvec())*R.from_quat(body.ref[i,3:7])).as_quat()
    return frames


def solve(body,frames,side,goal,pole,hand,roll_weight):
    p,q=body.world(frames)
    ui,ei,hi=[body.ix[a+'_'+side] for a in ('upperarm','lowerarm','hand')]
    origin=p[:,ui];l1=np.linalg.norm(body.ref[ei,:3]);l2=np.linalg.norm(body.ref[hi,:3])
    axis=c.unit(goal-origin)
    reach=np.clip(np.linalg.norm(goal-origin,axis=1),abs(l1-l2)+.02,(l1+l2)*.978)
    end=origin+axis*reach[:,None]
    v=pole-origin;bend=c.unit(v-axis*np.sum(v*axis,axis=1)[:,None])
    along=(l1*l1-l2*l2+reach*reach)/(2*reach)
    elbow=origin+axis*along[:,None]+bend*np.sqrt(np.maximum(0.,l1*l1-along*along))[:,None]
    u,f=elbow-origin,end-elbow
    ru=body.tp[ei]-body.tp[ui];rf=body.tp[hi]-body.tp[ei]
    uq=c.frame(u,f)*c.frame(ru,rf).inv()*R.from_quat(body.tq[ui])
    fq=c.frame(f,u)*c.frame(rf,ru).inv()*R.from_quat(body.tq[ei])
    inherited_u=c.align(p[:,ei]-origin,u)*R.from_quat(q[:,ui])
    inherited_f=c.align(p[:,hi]-p[:,ei],f)*R.from_quat(q[:,ei])
    uq=R.from_quat(c.slerp(inherited_u.as_quat(),uq.as_quat(),roll_weight[:,None]))
    fq=R.from_quat(c.slerp(inherited_f.as_quat(),fq.as_quat(),roll_weight[:,None]))
    body.set_world_rotations(frames,{ui:uq,ei:fq,hi:hand})


def native_twists(body,frames):
    for side in 'lr':
        hi=body.ix['hand_'+side]
        delta=(R.from_quat(frames[:,hi,3:7])*R.from_quat(body.ref[hi,3:7]).inv()).as_quat()
        axis=c.unit(body.ref[hi,:3])
        twist=c.unit(np.c_[(delta[:,:3]@axis)[:,None]*axis,delta[:,3]])
        angle=np.unwrap(2*np.arctan2(twist[:,:3]@axis,twist[:,3]))
        angle-=2*np.pi*round(float(angle[0])/(2*np.pi))
        for suffix in ('01','02'):
            i=body.ix['lowerarm_twist_'+suffix+'_'+side]
            station=np.linalg.norm(body.ref[i,:3])/np.linalg.norm(body.ref[hi,:3])
            frames[:,i,3:7]=(R.from_rotvec(axis[None]*(angle*station)[:,None])*R.from_quat(body.ref[i,3:7])).as_quat()
    return upper.upper_twists(body,frames)


def blade_mount(body):
    mount,offset=palm_mount(body,'r')
    hold=json.loads((ROOT/'SourceAssets/KukriThirdPerson20261024/native-grip.json').read_text())['bones']
    h=np.asarray(hold['hand_r']);w=np.asarray(hold['WPN_root']);hr=R.from_quat(h[3:7])
    return mount.apply(hr.inv().apply(w[:3]-h[:3]))+offset,mount*hr.inv()*R.from_quat(w[3:7])


def head_clearance(body,frames,goals,poles,hands,weights):
    """Fit the backward-facing blade outside a padded head envelope.

    The right wrist orientation stays locked to the source grip. Corrections
    move the complete arm outwards, rather than turning the knife in the fist.
    The envelope is an authoring proxy, not a runtime collision assertion.
    """
    model=json.loads((ROOT/'SourceAssets/Kukri20261020/model.json').read_text())
    bounds=model['bounds_cm']
    samples=np.array([[x,y,z] for x in np.linspace(*bounds['x'],4) for y in np.linspace(*bounds['y'],3) for z in np.linspace(*bounds['z'],31)])
    mount_pos,mount_rot=blade_mount(body)
    p,q=body.world(frames);head=body.ix['head'];hand=body.ix['hand_r']
    hrot=R.from_quat(q[:,head])*R.from_quat(body.tq[head]).inv()
    # Native head joint is below the face/scalp; include the face and hair line.
    size=body.scale/94.;centre=p[:,head]+hrot.apply(np.tile([0.,1.5,9.],(len(frames),1))*size)
    radii=np.array([12.,14.,16.])*size
    shoulder=p[:,body.ix['upperarm_r']]
    length=(np.linalg.norm(body.ref[body.ix['lowerarm_r'],:3])+np.linalg.norm(body.ref[hand,:3]))*.976
    outward=c.unit(shoulder-p[:,body.ix['upperarm_l']])
    rq=hands['r'];bq=rq*mount_rot
    offsets=np.array([rq[k].apply(mount_pos)+bq[k].apply(samples) for k in range(len(frames))])
    original=goals['r'].copy();fitted=original.copy()
    def fit(k,target,seed):
        transform=hrot[k].inv().as_matrix()/radii[:,None]
        def constraint(x):
            local=(x+offsets[k]-centre[k])@transform.T
            return np.r_[np.sum(local*local,axis=1)-1.01,(length*length-np.sum((x-shoulder[k])**2))/(length*length)]
        def jacobian(x):
            local=(x+offsets[k]-centre[k])@transform.T
            return np.vstack([2*local@transform,-2*(x-shoulder[k])/(length*length)])
        def objective(x):return np.sum((x-original[k])**2)+.65*np.sum((x-target)**2)
        def gradient(x):return 2*(x-original[k])+1.3*(x-target)
        if min(constraint(seed))>=0. and np.linalg.norm(seed-original[k])<1e-6:return seed
        candidates=[]
        for start in (seed,original[k]+outward[k]*14.,original[k]+np.array([0.,14.,0.])):
            result=minimize(objective,start,jac=gradient,method='SLSQP',
                constraints=[dict(type='ineq',fun=constraint,jac=jacobian)],options=dict(maxiter=90,ftol=1e-8))
            if min(constraint(result.x))>=-1e-5:
                candidates.append(result)
                if result.success:break
        if not candidates:raise RuntimeError('No reachable head-clearance arm fit at frame '+str(k))
        return min(candidates,key=lambda r:r.fun).x
    for k in range(1,len(frames)-1):
        target=original[k]+(fitted[k-1]-original[k-1])*.70
        fitted[k]=fit(k,target,original[k])
    smooth=gaussian_filter1d(fitted-original,1.7,axis=0,mode='nearest')
    # Project the smoothed correction back onto the reachable, clear hand set.
    # Wrist/weapon orientation remains the exact transferred FPS orientation.
    for k in range(1,len(frames)-1):
        fitted[k]=fit(k,original[k]+smooth[k],fitted[k])
    correction=fitted-original
    goals['r']=fitted;poles['r']+=correction*.35
    solve(body,frames,'r',goals['r'],poles['r'],hands['r'],weights)
    return np.linalg.norm(correction,axis=1)


def make_body(label,data):
    body=c.Body(data);old=data['previous'];old_frames=np.asarray(old['frames'])
    old_hit=old['markers'].get('Contact',old['duration']*.42)
    old_release=old['markers'].get('Release',old['duration']*.64)
    clock=PchipInterpolator([0.,CONTACT,RELEASE,LENGTH],[0.,old_hit,old_release,old['duration']])(TIMES)
    frames=np.array([c.sample(old_frames,float(t),old['rate']) for t in clock])
    envelope=c.ease(TIMES/.12)*(1-c.ease((TIMES-.84)/.16))
    frames=c.blend(np.repeat(body.idle[None],len(frames),axis=0),frames,envelope[:,None,None])
    ip,iq=body.world(body.idle);p,q=body.world(frames)
    chest=body.ix['spine_03']
    carry=R.from_quat(q[:,chest])*R.from_quat(iq[chest]).inv()
    # Small FPS shoulder preparation, applied as a delta to the native body.
    desired={}
    for side in 'lr':
        name='clavicle_'+side;i=body.ix[name];j=SI[name]
        delta=C*R.from_quat(SF[:,j,3:7])*R.from_quat(SF[0,j,3:7]).inv()*C.inv()
        target=carry*delta*carry.inv()*R.from_quat(q[:,i])
        desired[i]=R.from_quat(c.slerp(q[:,i],target.as_quat(),envelope[:,None]))
    body.set_world_rotations(frames,desired)
    p,q=body.world(frames)
    weights=c.ease(TIMES/.115)*(1-c.ease((TIMES-.84)/.16))
    goals={};poles={};hands={};arm_scales={}
    for side in 'rl':
        ui,ei,hi=[body.ix[a+'_'+side] for a in ('upperarm','lowerarm','hand')]
        su,se,sh=[SI[a+'_'+side] for a in ('upperarm','lowerarm','hand')]
        source_length=np.mean(np.linalg.norm(SF[:,se,:3]-SF[:,su,:3],axis=1)+np.linalg.norm(SF[:,sh,:3]-SF[:,se,:3],axis=1))
        native_length=np.linalg.norm(body.ref[ei,:3])+np.linalg.norm(body.ref[hi,:3])
        scale=native_length/source_length;arm_scales[side]=scale
        raw=p[:,ui]+carry.apply(C.apply(SF[:,sh,:3]-SF[:,su,:3]))*scale
        raw_pole=p[:,ui]+carry.apply(C.apply(SF[:,se,:3]-SF[:,su,:3]))*scale
        base=p[:,ui]+carry.apply(np.tile(ip[hi]-ip[ui],(len(frames),1)))
        base_pole=p[:,ui]+carry.apply(np.tile(ip[ei]-ip[ui],(len(frames),1)))
        goals[side]=base+(raw-base)*weights[:,None]
        poles[side]=base_pole+(raw_pole-base_pole)*weights[:,None]
        mount,_=palm_mount(body,side)
        source_hand=carry*C*R.from_quat(SF[:,sh,3:7])*mount.inv()
        base_hand=carry*R.from_quat(iq[hi])
        hands[side]=R.from_quat(c.slerp(base_hand.as_quat(),source_hand.as_quat(),weights[:,None]))
        solve(body,frames,side,goals[side],poles[side],hands[side],weights)
    correction=head_clearance(body,frames,goals,poles,hands,weights)
    frames=native_twists(body,frames)
    for i,name in enumerate(body.names):
        if '_twist_' in name and name.startswith(('upperarm','lowerarm')):
            frames[:,i,3:7]=c.slerp(np.tile(body.idle[i,3:7],(len(frames),1)),frames[:,i,3:7],weights[:,None])
    left=free_fingers(body)
    for i,name in enumerate(body.names):
        if name.endswith('_l') and name.split('_')[0] in ('thumb','index','middle','ring','pinky'):
            frames[:,i,3:7]=c.slerp(np.tile(body.idle[i,3:7],(len(frames),1)),left[:,i,3:7],weights[:,None])
    frames[0]=body.idle;frames[-1]=body.idle
    shared.right_fingers(body,frames,shared.grip(body))
    for k in range(1,len(frames)):
        frames[k,:,3:7]*=np.where(np.sum(frames[k-1,:,3:7]*frames[k,:,3:7],axis=1)<0,-1.,1.)[:,None]
    return frames,dict(native_arm_scales=arm_scales,head_clearance_arm_offset_cm=correction.tolist(),
        retained_body_source=old['asset'],body_time_samples=clock.tolist(),left_finger_motion='First-person fist/jab/open/retract',
        source_palm_orientations=True,first_person_camera_copied=False)


def main():
    cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    report=dict(source_asset=SOURCE['quick']['asset'],source_mesh=SOURCE['mesh'],seconds=LENGTH,rate=RATE,
        contact_seconds=CONTACT,release_clock_anchor_seconds=RELEASE,first_person_changed=False,gameplay_changed=False,
        runtime_tested=False,rendered=False,bodies={})
    for label,data in DATA['targets'].items():
        active=cfg if label=='jason' else cfg['body_variants'][label]
        if active['clips']['Kukri.FullBody.Pommel']!=data['previous']['asset'] or active['clips']['Kukri.FullBody.Idle']!=data['idle_asset']:
            raise RuntimeError('The captured body boundary/role changed: '+label)
        frames,detail=make_body(label,data)
        clip=dict(rate=RATE,frames=frames.tolist(),loop=False,contact=CONTACT,release=RELEASE,
            source=SOURCE['quick']['asset'],
            adaptation='Installed FPS two-arm motion: left closed jab/open/retract, right pommel cock/strike/rebound; anatomical native shoulders/lengths/elbow planes, source palm orientations and left finger curves; native knife grip, helper bones and full carry return; current torso/legs retimed to the same contact.')
        (OUT/(label+'-actions.json')).write_text(json.dumps(dict(mesh=data['mesh'],names=data['names'],parents=data['parents'],clips={'Pommel':clip}),separators=(',',':')))
        report['bodies'][label]=dict(mesh=data['mesh'],previous_pommel=data['previous']['asset'],idle_asset=data['idle_asset'],frames=len(frames),**detail)
        print('KUKRI_FIRST_PERSON_QUICK_AUTHORED '+label,flush=True)
    (OUT/'authoring.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__':main()
