"""Rebuild native whirlwind from the supplied Meshy arm performance.

The source owns the left shoulder, elbow plane and wrist articulation. The
weapon arm remains a single-hand outer sweep with its existing native grip.
Periodic phase curves join both turns; native full-chain entry/recovery share
the same boundary poses. No actor turn is baked into these local tracks.
"""
import importlib.util
import json
from pathlib import Path
import numpy as np
from scipy.interpolate import CubicSpline, PchipInterpolator
from scipy.ndimage import gaussian_filter1d
from scipy.spatial.transform import Rotation as R

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
old=module('spin_v6',Path('SourceAssets/KukriMeshyWhirlwind20261025/author.py'))
native=module('spin_native_helpers',Path('SourceAssets/KukriQuickFirstPerson20261025/author.py'))
c=old.c;SI=old.SI;SR=old.SR;SF=old.SF
DATA=json.loads((OUT/'active-inputs.json').read_text())
ROLES=old.ROLES

def mesh_references():
    # A shared MetaHuman Skeleton's reference can differ from its actual mesh.
    # Use the exported native mesh bind for both IK lengths and skinning.
    for label,data in DATA.items():
        path=ROOT/f'SourceAssets/FarreachBackpack20261024/SlimFitR2_20261024/BodyInputs/Normalized/{label.capitalize()}/body.json'
        geo=json.loads(path.read_text())
        if geo['source']!=data['mesh'] or [b['name'] for b in geo['bones']]!=data['names']:
            raise RuntimeError('Native mesh reference mismatch')
        world=np.array([geo['reference'][n] for n in data['names']]);local=world.copy()
        for i,parent in enumerate(data['parents']):
            if parent<0:continue
            inverse=R.from_quat(world[parent,3:7]).inv()
            local[i,:3]=inverse.apply(world[i,:3]-world[parent,:3])/world[parent,7:]
            local[i,3:7]=(inverse*R.from_quat(world[i,3:7])).as_quat()
            local[i,7:]=world[i,7:]/world[parent,7:]
        data['reference']=local.tolist();data['reference_world']=world.tolist()
        data['authoring_reference_source']=str(path.relative_to(ROOT))

mesh_references()

def donor_rotation(body,name,world):
    i,j=body.ix[name],SI[name];child=body.axis_child(name)
    if name=='hand_l':
        a=c.frame(SR[SI['LeftHand_End'],:3]-SR[j,:3],np.array([0.,1.,0.]))
        b=c.frame(body.tp[body.ix['middle_01_l']]-body.tp[i],body.tp[body.ix['index_01_l']]-body.tp[body.ix['pinky_01_l']])
    else:
        av=SR[SI[child],:3]-SR[j,:3];bv=body.tp[body.ix[child]]-body.tp[i]
        a=c.frame(av,np.array([0.,1.,0.]));b=c.frame(bv,body.target_forward)
    mount=R.from_quat(SR[j,3:7]).inv()*a*b.inv()*R.from_quat(body.tq[i])
    return R.from_quat(world[:,j,3:7])*mount

def source_left_arm(body,frames,source,front):
    count=len(frames);size=body.scale/94.
    sc=R.from_quat(source[:,SI['spine_03'],3:7])*R.from_quat(SR[SI['spine_03'],3:7]).inv()
    p,q,tc=old.arms.chest(body,frames)
    transfer=tc*sc.inv()
    # Same-side source clavicle anticipation, not the mirrored axe support arm.
    desired={body.ix[name]:transfer*donor_rotation(body,name,source) for name in
             ('clavicle_l','upperarm_l','lowerarm_l','hand_l')}
    body.set_world_rotations(frames,desired)
    p,q=body.world(frames)
    ui,ei,hi=[body.ix[n+'_l'] for n in ('upperarm','lowerarm','hand')]
    source_length=sum(np.linalg.norm(SR[SI[b+'_l'],:3]-SR[SI[a+'_l'],:3]) for a,b in
                      [('upperarm','lowerarm'),('lowerarm','hand')])
    length=np.linalg.norm(body.ref[ei,:3])+np.linalg.norm(body.ref[hi,:3])
    scale=length/source_length
    wrist=sc.inv().apply(source[:,SI['hand_l'],:3]-source[:,SI['upperarm_l'],:3])
    elbow=sc.inv().apply(source[:,SI['lowerarm_l'],:3]-source[:,SI['upperarm_l'],:3])
    # Keep the donor's substantial cross-body lift, fold, release and return.
    # Recenter only enough to turn an axe movement into a free-hand guard.
    wrist=(.65*wrist+[-.05,.13,.10])*scale
    elbow=(.95*elbow+[0.,.035,.03])*scale
    middle=(p[:,body.ix['upperarm_l']]+p[:,body.ix['upperarm_r']])*.5
    origin=tc.inv().apply(p[:,ui]-middle)
    h=origin+wrist
    # A soft front constraint applies only inside the torso's width/height.
    in_width=1-c.ease((np.abs(h[:,0])-20*size)/(10*size))
    in_height=c.ease((h[:,2]+40*size)/(8*size))*(1-c.ease((h[:,2]-3*size)/(9*size)))
    push=np.logaddexp(0.,(front+6*size-h[:,1])/(1.5*size))*1.5*size
    wrist[:,1]+=push*in_width*in_height
    goal=p[:,ui]+tc.apply(wrist);pole=p[:,ui]+tc.apply(elbow)
    relative_wrist=R.from_quat(q[:,ei]).inv()*R.from_quat(q[:,hi])
    body.solve(frames,['upperarm_l','lowerarm_l','hand_l'],goal,pole,R.from_quat(q[:,hi]))
    # Carry the source's wrist articulation with the fitted forearm; an IK
    # direction correction must not become an extra bend at the wrist.
    _,fitted=body.world(frames)
    body.set_world_rotations(frames,{hi:R.from_quat(fitted[:,ei])*relative_wrist})
    native.upper.support_wrist(body,frames,'l')
    # The donor's 2.5 s take runs twice in 1.067 s. Retain its wrist phrasing
    # at 70% excursion instead of amplifying a fast empty-hand flick into a snap.
    wrist_local=R.from_quat(frames[:,hi,3:7]);centre=wrist_local.mean()
    frames[:,hi,3:7]=(centre*R.from_rotvec(.70*(centre.inv()*wrist_local).as_rotvec())).as_quat()
    fist=old.fingers.native_fist(body,json.loads(old.fingers.FIST_SOURCE.read_text()))
    # Meshy has no finger tracks. Author relaxed native digits, with a small
    # grip/release response, instead of claiming the source supplied a fist.
    closure=.34+.20*(1-c.ease((np.linalg.norm(wrist,axis=1)/length-.48)/.35))
    old.steps.set_fist(body,frames,fist,closure)
    return frames

def periodic_curve(frames,sigma=8.):
    f=frames.copy();count=len(f)
    for k in range(1,count):
        f[k,:,3:7]*=np.where(np.sum(f[k-1,:,3:7]*f[k,:,3:7],axis=1)<0,-1.,1.)[:,None]
    if np.any(np.sum(f[0,:,3:7]*f[-1,:,3:7],axis=1)<0):
        raise RuntimeError('Non-periodic quaternion winding needs explicit handling')
    # Filter in a periodic domain before interpolating. This joins both pose
    # and velocity, including the donor's settling motion at the seam.
    f=gaussian_filter1d(f,sigma,axis=0,mode='wrap')
    f[:,:,3:7]=c.unit(f[:,:,3:7])
    f=np.concatenate([f,f[:1]],axis=0)
    curve=CubicSpline(np.linspace(0.,1.,count+1),f,axis=0,bc_type='periodic')
    def evaluate(phase):
        result=curve(np.mod(phase,1.));result[:,:,3:7]=c.unit(result[:,:,3:7]);return result
    return evaluate

def smoother(x):
    x=np.clip(x,0,1);return x*x*x*(10+x*(-15+6*x))

def transition(body,boundary,entry,seconds):
    rate=120;count=round(seconds*rate)+1;times=np.arange(count)/rate;u=times/times[-1]
    a,b=(body.idle,boundary) if entry else (boundary,body.idle)
    frames=np.array([c.blend(a,b,smoother(t)) for t in u])
    ap,aq=body.world(a);bp,bq=body.world(b)
    windows={'l':(.04,.57),'r':(.40,.94)} if entry else {'r':(.04,.55),'l':(.42,.95)}
    old.steps.step_transition(body,frames,times,{s:ap[body.ix['foot_'+s]] for s in 'lr'},
        {s:bp[body.ix['foot_'+s]] for s in 'lr'},
        {s:aq[body.ix['foot_'+s]] for s in 'lr'},
        {s:bq[body.ix['foot_'+s]] for s in 'lr'},
        {s:(a*times[-1],b*times[-1]) for s,(a,b) in windows.items()},body.scale/94.)
    # Recompute native twist helpers while keeping the complete arm chains;
    # no separate fixed-guard solver overwrites the final clavicle/wrist pose.
    native.native_twists(body,frames)
    frames[0]=a;frames[-1]=b
    return frames

def metrics(body,frames,rate):
    p,q,torso=old.arms.chest(body,frames)
    mid=(p[:,body.ix['upperarm_l']]+p[:,body.ix['upperarm_r']])*.5
    local=torso.inv().apply(p[:,body.ix['hand_l']]-mid)
    wrist=R.from_quat(frames[:,body.ix['hand_l'],3:7])
    delta=np.degrees((wrist[1:]*wrist[:-1].inv()).magnitude())
    arm_names=('clavicle_l','upperarm_l','lowerarm_l','hand_l')
    changes={name:float(np.degrees((R.from_quat(frames[1:,body.ix[name],3:7])*
        R.from_quat(frames[:-1,body.ix[name],3:7]).inv()).magnitude()).max()) for name in arm_names}
    return dict(left_hand_chest_range_cm=np.ptp(local,axis=0).tolist(),
        left_hand_max_frame_step_cm=float(np.linalg.norm(np.diff(p[:,body.ix['hand_l']],axis=0),axis=1).max()),
        left_wrist_max_frame_angle_degrees=float(delta.max()),max_joint_frame_degrees=changes,sample_rate=rate)

def main():
    cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    tuning=json.loads((ROOT/'Content/ColdSteelData/skills.json').read_text(encoding='utf-8-sig'))['whirlwind']
    turns=abs(tuning['turnDegrees'])/360.
    if tuning['turnDegrees']>=0 or abs(turns-round(turns))>1e-6:raise RuntimeError('Signed whole-turn contract changed')
    progress=np.maximum.accumulate(np.maximum(0.,old.SOURCE_YAW-old.SOURCE_YAW[0]));progress/=progress[-1]
    progress=.80*progress+.20*np.linspace(0.,1.,len(progress))
    phase=np.arange(256)/256.
    source_time=PchipInterpolator(progress,np.arange(len(SF))/old.SOURCE['rate'])(phase)
    original=np.array([c.sample(SF,float(t),old.SOURCE['rate']) for t in source_time])
    world=old.mirror(original)
    yaw=old.heading(world,old.MR);unturn=R.from_euler('z',-yaw[:,None])
    for i in range(world.shape[1]):
        world[:,i,:3]=unturn.apply(world[:,i,:3])
        world[:,i,3:7]=(unturn*R.from_quat(world[:,i,3:7])).as_quat()
    # Rotate about the performer's pelvis, not the GLB export origin. Keep a
    # small source sway while the gameplay actor owns the spin and travel.
    planar=world[:,SI['pelvis'],:2].copy()
    world[:,:,:2]-=(planar-.20*(planar-planar.mean(axis=0)))[:,None,:]
    report=dict(source=old.SOURCE['original'],source_sha256=old.SOURCE['sha256'],source_clip=old.SOURCE['clip'],
        source_finger_tracks=False,source_time_warp='80% monotone source yaw + 20% source time',
        turn_degrees=tuning['turnDegrees'],gameplay_changed=False,first_person_changed=False,runtime_tested=False,bodies={})
    for label,data in DATA.items():
        body=c.Body(data);front=old.chest_envelope(body,label)
        cycle,scale=old.retarget(body,world)
        old.author_arms(body,cycle,original,front)
        source_left_arm(body,cycle,original,front)
        held=old.grip(body);old.right_fingers(body,cycle,held)
        native.native_twists(body,cycle)
        evaluate=periodic_curve(cycle)
        n=round(tuning['spinSeconds']*120)+1
        clock=np.linspace(0.,1.,n);loop=evaluate(turns*old.arms.phase(clock))
        native.native_twists(body,loop);old.right_fingers(body,loop,held)
        start=transition(body,loop[0],True,tuning['readySeconds'])
        end=transition(body,loop[-1],False,tuning['recoverSeconds'])
        old.right_fingers(body,start,held);old.right_fingers(body,end,held)
        clips={}
        for role,frames in zip(ROLES,(start,loop,end)):
            for k in range(1,len(frames)):
                frames[k,:,3:7]*=np.where(np.sum(frames[k-1,:,3:7]*frames[k,:,3:7],axis=1)<0,-1.,1.)[:,None]
            clips[role]=dict(rate=120,frames=frames.tolist(),contact=0.,release=.999,
                source='User Meshy GLB / Axe_Spin_Attack',
                adaptation='Source-driven left clavicle, elbow plane and relative wrist; torso clearance and relaxed native digits; periodic smooth phase curves across both turns; full-chain entry/recovery; existing right native grip.')
        (OUT/(label+'-actions.json')).write_text(json.dumps(dict(mesh=data['mesh'],names=body.names,parents=body.parents,clips=clips),separators=(',',':')))
        section=cfg if label=='jason' else cfg['body_variants'][label]
        old_loop=np.asarray(data['clips']['Whirlwind.Loop']['frames'])
        report['bodies'][label]=dict(mesh=data['mesh'],previous_roles={role:section['clips']['Kukri.FullBody.'+role] for role in ROLES},
            authoring_reference_source=data['authoring_reference_source'],retarget_source_asset=data['mesh'],
            previous_metrics=metrics(body,old_loop,60),candidate_metrics=metrics(body,loop[::2],60),
            torso_front_cm=front,source_scale_cm=scale,
            boundary_max_position_error_cm=float(max(np.abs(start[-1,:,:3]-loop[0,:,:3]).max(),np.abs(loop[-1,:,:3]-end[0,:,:3]).max())),
            boundary_max_rotation_error_degrees=float(max(np.degrees((R.from_quat(start[-1,:,3:7])*R.from_quat(loop[0,:,3:7]).inv()).magnitude()).max(),
                np.degrees((R.from_quat(loop[-1,:,3:7])*R.from_quat(end[0,:,3:7]).inv()).magnitude()).max())))
        print('WHIRLWIND_SOURCE_MOTION_AUTHORED '+label,flush=True)
    (OUT/'authoring.json').write_text(json.dumps(report,indent=2))

if __name__=='__main__':main()
