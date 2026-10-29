"""Meshy Axe_Spin_Attack -> native, right-handed Kukri whirlwind.

The donor supplies pelvis, spine, head, stepping and arm phrasing. Reflect the
body/step performance for the existing negative gameplay turn; carry the
original right arm's phrasing in chest space, so the weapon never changes hand.
No time reversal and no extra whole-body turn is added to the runtime actor.
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

c=module('meshy_native_body',Path('SourceAssets/KukriThirdPerson20261024/ComboV3/author.py'))
arms=module('meshy_native_arms',Path('SourceAssets/KukriWhirlwindGuard20261025/author.py'))
fingers=module('meshy_native_fist',Path('SourceAssets/KukriThrustHand20261025/author.py'))
steps=module('meshy_native_steps',Path('SourceAssets/KukriWhirlwind20261025/author.py'))
SOURCE=json.loads((OUT/'source.json').read_text())
SI={n:i for i,n in enumerate(SOURCE['names'])}
SR=np.asarray(SOURCE['reference_world'])
SF=np.asarray(SOURCE['frames'])
ROLES=('Whirlwind.Start','Whirlwind.Loop','Whirlwind.End')
M=np.diag([-1.,1.,1.])


def mirror(a):
    out=a.copy()
    for name,i in SI.items():
        pair=name[:-2]+('_r' if name.endswith('_l') else '_l') if name.endswith(('_l','_r')) else name
        if name.startswith('Left'):pair=name.replace('Left','Right')
        elif name.startswith('Right'):pair=name.replace('Right','Left')
        j=SI.get(pair,i)
        out[...,i,:3]=a[...,j,:3]@M.T
        shape=a[...,j,3:7].shape
        out[...,i,3:7]=R.from_matrix(M@R.from_quat(a[...,j,3:7].reshape(-1,4)).as_matrix()@M).as_quat().reshape(shape)
    return out


MR=mirror(SR)
MF=mirror(SF)


def heading(frames,reference):
    q=R.from_quat(frames[:,SI['pelvis'],3:7])*R.from_quat(reference[SI['pelvis'],3:7]).inv()
    forward=q.apply(np.tile([0.,1.,0.],(len(frames),1)))
    return np.unwrap(np.arctan2(-forward[:,0],forward[:,1]))


SOURCE_YAW=heading(SF,SR)
# Monotone source landmarks retain the main pivot. The small clock term keeps
# the final settling motion finite instead of collapsing it into one frame.
progress=(SOURCE_YAW-SOURCE_YAW[0])/(2*np.pi)
progress=np.maximum.accumulate(np.maximum(0.,progress))
progress/=progress[-1]
progress=.94*progress+.06*np.linspace(0.,1.,len(progress))
SOURCE_TIME=PchipInterpolator(progress,np.arange(len(SF))/SOURCE['rate'])


def grip(body):
    """Same anatomical palm mount and finite digit IK as FPSPlayerBodyGrip.cpp."""
    native=c.INPUT['native'];ni={n:i for i,n in enumerate(native['names'])}
    nr=np.asarray(native['reference_world'])
    hold=json.loads((ROOT/'SourceAssets/KukriThirdPerson20261024/native-grip.json').read_text())['bones']
    hp=np.asarray(hold['hand_r']);hr=R.from_quat(hp[3:7])
    target=body.ix['hand_r'];tr=R.from_quat(body.tq[target])
    a=np.array([R.from_quat(nr[ni['hand_r'],3:7]).inv().apply(nr[ni[d+'_01_r'],:3]-nr[ni['hand_r'],:3]) for d in ('index','middle','pinky')])
    b=np.array([tr.inv().apply(body.tp[body.ix[d+'_01_r']]-body.tp[target]) for d in ('index','middle','pinky')])
    mount=c.frame(b[1],b[0]-b[2])*c.frame(a[1],a[0]-a[2]).inv()
    offset=b.mean(0)-mount.apply(a.mean(0))
    transfer=tr*mount*hr.inv();desired={}
    frame=body.ref[None].copy()
    for digit in ('thumb','index','middle','ring','pinky'):
        names=[f'{digit}_{k:02d}_r' for k in (1,2,3)]
        for k,name in enumerate(names):
            ia,ib=(k,k+1) if k<2 else (1,2)
            src=R.from_quat(nr[ni[name],3:7]).inv().apply(nr[ni[names[ib]],:3]-nr[ni[names[ia]],:3])
            dst=R.from_quat(body.tq[body.ix[name]]).inv().apply(body.tp[body.ix[names[ib]]]-body.tp[body.ix[names[ia]]])
            desired[body.ix[name]]=transfer*R.from_quat(hold[name][3:7])*c.align(dst,src)
    body.set_world_rotations(frame,{i:R.from_quat(q.as_quat()[None]) for i,q in desired.items()})
    for digit in ('thumb','index','middle','ring','pinky'):
        names=[f'{digit}_{k:02d}_r' for k in (1,2,3)]
        points=[body.tp[target]+tr.apply(mount.apply(hr.inv().apply(np.asarray(hold[name][:3])-hp[:3]))+offset) for name in names]
        body.solve(frame,names,np.asarray(points[2])[None],np.asarray(points[1])[None],R.from_quat(desired[body.ix[names[2]]].as_quat()[None]))
    for i,name in enumerate(body.names):
        parent=body.parents[i]
        if name.endswith('_r') and '_half_' in name and parent in desired:
            delta=R.from_quat(body.ref[parent,3:7]).inv()*R.from_quat(frame[0,parent,3:7])
            frame[0,i,3:7]=(R.from_rotvec(-.5*delta.as_rotvec())*R.from_quat(body.ref[i,3:7])).as_quat()
    return frame[0]


def retarget(body,world):
    scale=np.mean([sum(np.linalg.norm(body.tp[body.ix[b+'_'+s]]-body.tp[body.ix[a+'_'+s]]) for a,b in [('thigh','calf'),('calf','foot')])/
        sum(np.linalg.norm(MR[SI[b+'_'+s],:3]-MR[SI[a+'_'+s],:3]) for a,b in [('thigh','calf'),('calf','foot')]) for s in 'lr'])
    offset=np.mean([body.tp[body.ix['ball_'+s],2]-MR[SI['ball_'+s],2]*scale for s in 'lr'])
    desired={};f=np.repeat(body.ref[None],len(world),axis=0)
    for name in ['pelvis','spine_01','spine_02','spine_03','neck_01','head']+[a+'_'+s for s in 'lr' for a in ['clavicle','thigh','calf','foot','ball']]:
        i,j=body.ix[name],SI[name]
        child=body.axis_child(name)
        if child and child in SI:
            av=MR[SI[child],:3]-MR[j,:3];bv=body.tp[body.ix[child]]-body.tp[i]
            sa=np.array([0.,1.,0.]);ta=body.target_forward
            if abs(c.unit(av)@sa)>.92:sa=np.array([0.,0.,1.])
            if abs(c.unit(bv)@ta)>.92:ta=np.array([0.,0.,1.])
            a,b=c.frame(av,sa),c.frame(bv,ta)
        else:a=b=R.identity()
        mount=R.from_quat(MR[j,3:7]).inv()*a*b.inv()*R.from_quat(body.tq[i])
        desired[i]=R.from_quat(world[:,j,3:7])*mount
    body.set_world_rotations(f,desired)
    f[:,body.hip,:3]=world[:,SI['pelvis'],:3]*scale+[0,0,offset]
    goals={s:world[:,SI['foot_'+s],:3]*scale+[0,0,offset] for s in 'lr'}
    poles={s:world[:,SI['calf_'+s],:3]*scale+[0,0,offset] for s in 'lr'}
    feet={s:desired[body.ix['foot_'+s]] for s in 'lr'}
    steps.fit_legs(body,f,goals,feet,poles)
    return f,scale


def chest_envelope(body,label):
    path=ROOT/f'SourceAssets/FarreachBackpack20261024/SlimFitR2_20261024/BodyInputs/Normalized/{label.capitalize()}/body.json'
    mesh=json.loads(path.read_text())
    if mesh['source']!=body.data['mesh']:raise RuntimeError('Body geometry does not match target')
    verts=np.asarray(mesh['positions'])
    spine={i for i,n in enumerate(body.names) if n.startswith('spine_')}
    weights=np.array([sum(w for i,w in row if i in spine) for row in mesh['weights']])
    shoulders=(body.tp[body.ix['upperarm_l']]+body.tp[body.ix['upperarm_r']])*.5
    region=(weights>.75)&(verts[:,2]>shoulders[2]-31)&(verts[:,2]<shoulders[2]-5)
    # Clearance is an authoring constraint against the actual torso envelope.
    front=float(np.quantile(verts[region,1]-shoulders[1],.995))
    return front


def author_arms(body,frames,original,front):
    """Convert two-hand axe phrasing to an extended single-hand sword arc."""
    n=len(frames);size=body.scale/94.
    source_chest=R.from_quat(original[:,SI['spine_03'],3:7])*R.from_quat(SR[SI['spine_03'],3:7]).inv()
    local={s:source_chest.inv().apply(original[:,SI['hand_'+s],:3]-original[:,SI['upperarm_'+s],:3]) for s in 'lr'}
    # Source clavicle anticipation is retained. The supported arm solution uses
    # each target's native elbow plane, rather than foreign bone-axis quaternions.
    p,_,torso=arms.chest(body,frames)
    middle=(p[:,body.ix['upperarm_l']]+p[:,body.ix['upperarm_r']])*.5
    for side in 'rl':
        ui,ei,hi=[body.ix[a+'_'+side] for a in ('upperarm','lowerarm','hand')]
        length=np.linalg.norm(body.ref[ei,:3])+np.linalg.norm(body.ref[hi,:3])
        v=local[side]
        if side=='r':
            # Keep a broad external sweep, with the donor's lift/drop and draw
            # rhythm; its original axe reach crosses the chest with both hands.
            direction=c.unit(np.c_[-np.ones(n),.22+.30*np.tanh(v[:,1]/.22),.10+.25*np.tanh(v[:,2]/.22)])
            reach=.91+.035*np.tanh((np.linalg.norm(v,axis=1)-.36)/.09)
            goal=p[:,ui]+torso.apply(direction*(length*reach)[:,None])
            pole=p[:,ui]+torso.apply(np.c_[-np.full(n,.38),.11+.06*np.tanh(v[:,1]/.2),-np.full(n,.5)]*length)
        else:
            offset=np.c_[2.+3*np.tanh((v[:,0]-.10)/.18),np.full(n,front+9*size)+1.7*size*np.tanh(v[:,1]/.2),(-17+2*np.tanh(v[:,2]/.2))*size]
            goal=middle+torso.apply(offset)
            pole=p[:,ui]+torso.apply(np.c_[np.full(n,.29),np.full(n,.23),-.55+.03*np.tanh(v[:,2]/.2)]*length)
        arms.solve_arm(body,frames,side,goal,pole,np.ones(n),np.ones(n),body.ref[hi,3:7])
    return body.twists(frames)


def right_fingers(body,frames,pose):
    for i,name in enumerate(body.names):
        if name.endswith('_r') and name.split('_')[0] in ('thumb','index','middle','ring','pinky'):
            frames[:,i,3:7]=pose[i,3:7]


def transition(body,boundary,entry,rate,duration):
    n=round(duration*rate)+1;ts=np.linspace(0.,duration,n)
    a,b=(body.idle,boundary) if entry else (boundary,body.idle)
    frames=np.array([c.blend(a,b,c.ease(t/duration)) for t in ts])
    ap,aq=body.world(a);bp,bq=body.world(b)
    windows={'l':(.03*duration,.58*duration),'r':(.43*duration,.96*duration)}
    if not entry:windows={'r':(.04*duration,.58*duration),'l':(.43*duration,.98*duration)}
    steps.step_transition(body,frames,ts,{s:ap[body.ix['foot_'+s]] for s in 'lr'},
        {s:bp[body.ix['foot_'+s]] for s in 'lr'},{s:aq[body.ix['foot_'+s]] for s in 'lr'},
        {s:bq[body.ix['foot_'+s]] for s in 'lr'},windows,body.scale/94.)
    # Interpolate hand goals in chest space, retaining a supported wrist and a
    # forward path during draw/return rather than straight local-angle collapse.
    frames=arms.make_transition(body,frames,boundary,entry,rate)
    frames[0]=a;frames[-1]=b
    return frames


def main():
    cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    tuning=json.loads((ROOT/'Content/ColdSteelData/skills.json').read_text(encoding='utf-8-sig'))['whirlwind']
    turns=abs(tuning['turnDegrees'])/360.
    if tuning['turnDegrees']>=0 or abs(turns-round(turns))>1e-6:
        raise RuntimeError('Author against the current negative whole-turn contract')
    rate=120;n=round(tuning['spinSeconds']*rate)+1
    cycles=turns*arms.phase(np.linspace(0.,1.,n));fractions=np.mod(cycles,1.)
    source_times=SOURCE_TIME(fractions)
    original=np.asarray([c.sample(SF,float(t),SOURCE['rate']) for t in source_times])
    world=mirror(original)
    # Strip the donor's global yaw ONCE. All bones receive the same rigid
    # transform; hip sways, foot plants and articulated spine motion survive.
    local_yaw=(R.from_quat(world[:,SI['pelvis'],3:7])*R.from_quat(MR[SI['pelvis'],3:7]).inv()).apply(np.tile([0.,1.,0.],(n,1)))
    yaw=np.arctan2(-local_yaw[:,0],local_yaw[:,1]);unturn=R.from_euler('z',-yaw[:,None])
    for i in range(world.shape[1]):
        world[:,i,:3]=unturn.apply(world[:,i,:3])
        world[:,i,3:7]=(unturn*R.from_quat(world[:,i,3:7])).as_quat()
    report=dict(source=SOURCE['original'],source_sha256=SOURCE['sha256'],source_clip=SOURCE['clip'],
        source_duration=SOURCE['duration'],source_time_warp='94% monotone source yaw + 6% source time, inverse sampled on gameplay phase',
        source_time_samples=source_times.tolist(),turn_degrees=tuning['turnDegrees'],runtime_tested=False,rendered=False,
        gameplay_changed=False,first_person_changed=False,bodies={})
    fist_source=json.loads(fingers.FIST_SOURCE.read_text())
    for label,data in c.INPUT['targets'].items():
        body=c.Body(data);front=chest_envelope(body,label)
        loop,scale=retarget(body,world)
        loop=author_arms(body,loop,original,front)
        fist=fingers.native_fist(body,fist_source)
        steps.set_fist(body,loop,fist,np.ones(n))
        held=grip(body);right_fingers(body,loop,held)
        loop[-1]=loop[0]
        start=transition(body,loop[0],True,60,tuning['readySeconds'])
        end=transition(body,loop[-1],False,60,round(tuning['recoverSeconds']*60)/60.)
        right_fingers(body,start,held);right_fingers(body,end,held)
        clips={}
        for role,frames,r in zip(ROLES,(start,loop,end),(60,120,60)):
            # Continuous quaternion signs are stored across every native track.
            for k in range(1,len(frames)):
                sign=np.where(np.sum(frames[k-1,:,3:7]*frames[k,:,3:7],axis=1)<0,-1.,1.)
                frames[k,:,3:7]*=sign[:,None]
            clips[role]=dict(rate=r,frames=frames.tolist(),contact=0.,release=.999,
                source='User Meshy GLB / Axe_Spin_Attack',
                adaptation='Mirrored source pelvis/spine/head/steps on the existing signed gameplay clock; original right-hand phrasing adapted to an extended single-hand arc, left chest guard; native palm mount, finite grip digit IK, supported wrists and native twist helpers; sequential entry/exit steps.')
        result=dict(mesh=data['mesh'],names=data['names'],parents=data['parents'],clips=clips)
        (OUT/(label+'-actions.json')).write_text(json.dumps(result,separators=(',',':')))
        active=cfg if label=='jason' else cfg['body_variants'][label]
        report['bodies'][label]=dict(mesh=data['mesh'],previous_roles={role:active['clips']['Kukri.FullBody.'+role] for role in ROLES},
            source_scale_cm=scale,torso_front_envelope_cm=front,native_grip=True,
            clips={role:dict(frames=len(item['frames']),rate=item['rate']) for role,item in clips.items()})
        print('KUKRI_MESHY_WHIRLWIND_AUTHORED '+label,flush=True)
    (OUT/'authoring.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__':main()
