"""Free3D dual sword takes -> native Jason/Kaitlin dual combo slots.

Use the actual source shoulder/elbow/wrist chains, torso and stepping. Convert
Blender handedness once, map anatomical bind frames, and keep native digits.
First-person clips and all server hit windows remain unchanged.
"""
import importlib.util,json,hashlib
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.interpolate import PchipInterpolator
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
spec=importlib.util.spec_from_file_location('dual_source_helpers',ROOT/'SourceAssets/KukriDualCombatThirdPerson20261028/author.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
c,base,carry=old.c,old.base,old.carry
RATE=120;M=np.diag([1.,-1.,1.])
MAP={'pelvis':'Hips','spine_01':'Spine','spine_03':'Spine1','spine_05':'Spine2','neck_01':'Neck','head':'Head'}
for side,word in [('l','Left'),('r','Right')]:
    for dst,src in [('clavicle','Shoulder'),('upperarm','Arm'),('lowerarm','ForeArm'),('hand','Hand'),
                    ('thigh','UpLeg'),('calf','Leg'),('foot','Foot'),('ball','ToeBase')]:MAP[dst+'_'+side]=word+src

def smooth(x):
    x=np.clip(x,0.,1.);return x*x*x*(10+x*(-15+6*x))

def converted(data):
    a=np.asarray(data).copy();a[...,:3]=a[...,:3]@M
    shape=a[...,3:7].shape
    a[...,3:7]=R.from_matrix(M@R.from_quat(a[...,3:7].reshape(-1,4)).as_matrix()@M).as_quat().reshape(shape)
    return a

def donor(role,t):
    raw=json.loads((OUT/(role+'-source.json')).read_text());ix={n:i for i,n in enumerate(raw['names'])}
    ref=converted(raw['reference_world']);f=converted(raw['frames']);length=t[-1]
    if role=='Slash1':
        # Cross Attack includes three cuts. Use its first two complete cuts;
        # the third, overhead finisher belongs to a different combo role.
        keys=[0.,.12,.357,.48,.66,.85,1.03,1.24,length]
        values=[0.,.23,.73,.90,1.28,1.65,1.86,2.05,2.05]
        path_times=[0.,.95,2.05];end=2.05
    else:
        keys=[0.,.12,.38,.50,.90,1.20,length]
        values=[0.,.23,.73,.88,1.14,1.50,raw['duration']]
        path_times=[0.,raw['duration']];end=raw['duration']
    times=PchipInterpolator(keys,values)(t)
    world=np.array([c.sample(f,float(s),raw['rate']) for s in times])
    # In-place conversion removes the source's metre-scale advance. Capsule
    # movement remains authoritative; retain the lateral sway and height.
    hip=ix['Hips'];path=np.array([c.sample(f,s,raw['rate'])[hip,:2] for s in path_times])
    travel=PchipInterpolator(path_times,path)(np.minimum(times,end))
    world[...,:2]-=travel[:,None,:]
    if role=='Slash2':
        # The source downcut is nearly simultaneous. Delay the entire LEFT
        # shoulder-to-hand chain in chest space to the existing offhand hit.
        left_t=np.maximum(0.,t-.50)
        left_time=PchipInterpolator(keys,values)(left_t)
        left_world=np.array([c.sample(f,float(s),raw['rate']) for s in left_time])
        chest=ix['Spine2']
        src_chest=R.from_quat(left_world[:,chest,3:7]);dst_chest=R.from_quat(world[:,chest,3:7])
        transport=dst_chest*src_chest.inv()
        for name,i in ix.items():
            if not name.startswith('Left') or any(z in name for z in ('UpLeg','Leg','Foot','Toe')):continue
            world[:,i,:3]=world[:,chest,:3]+transport.apply(left_world[:,i,:3]-left_world[:,chest,:3])
            world[:,i,3:7]=(transport*R.from_quat(left_world[:,i,3:7])).as_quat()
    return world,ref,ix,raw,dict(target_seconds=keys,source_seconds=values,source_end=end,offhand_delay=.5 if role=='Slash2' else 0.)

def rotation(body,name,world,ref,ix):
    i,j=body.ix[name],ix[MAP[name]]
    if name.startswith('hand_'):
        word='Left' if name.endswith('_l') else 'Right';side=name[-1]
        a=c.frame(ref[ix[word+'HandMiddle1'],:3]-ref[j,:3],ref[ix[word+'HandIndex1'],:3]-ref[ix[word+'HandPinky1'],:3])
        b=c.frame(body.tp[body.ix['middle_01_'+side]]-body.tp[i],body.tp[body.ix['index_01_'+side]]-body.tp[body.ix['pinky_01_'+side]])
    else:
        pairs={'pelvis':('Spine','spine_01'),'spine_01':('Spine1','spine_03'),
               'spine_03':('Spine2','spine_05'),'spine_05':('Neck','neck_01'),
               'neck_01':('Head','head'),'head':('HeadTop_End','head')}
        if name in pairs:source_child,target_child=pairs[name]
        else:
            target_child=body.axis_child(name);source_child=MAP[target_child]
        av=ref[ix[source_child],:3]-ref[j,:3]
        bv=body.tp[body.ix[target_child]]-body.tp[i]
        if name=='head':bv=np.array([0.,0.,1.])
        secondary=np.array([0.,1.,0.])
        if abs(c.unit(av)@secondary)>.92:secondary=np.array([0.,0.,1.])
        target_secondary=np.array([0.,1.,0.])
        if abs(c.unit(bv)@target_secondary)>.92:target_secondary=np.array([0.,0.,1.])
        a,b=c.frame(av,secondary),c.frame(bv,target_secondary)
    mount=R.from_quat(ref[j,3:7]).inv()*a*b.inv()*R.from_quat(body.tq[i])
    return R.from_quat(world[:,j,3:7])*mount

def build(body,role,t):
    world,ref,ix,raw,clock=donor(role,t);n=len(t)
    f=np.repeat(body.ref[None],n,axis=0)
    # Keep all native segment lengths, bind translations, scale and helpers.
    desired={body.ix[name]:rotation(body,name,world,ref,ix) for name in MAP if name in body.ix}
    for name,a,b in [('spine_02','spine_01','spine_03'),('spine_04','spine_03','spine_05')]:
        desired[body.ix[name]]=R.from_quat(c.slerp(desired[body.ix[a]].as_quat(),desired[body.ix[b]].as_quat(),.5))
    if 'neck_02' in body.ix:
        q=desired[body.ix['neck_01']]*R.from_quat(body.tq[body.ix['neck_01']]).inv()*R.from_quat(body.tq[body.ix['neck_02']])
        desired[body.ix['neck_02']]=q
    cbody=body.ix['pelvis']
    scale=np.mean([sum(np.linalg.norm(body.tp[body.ix[b+'_'+s]]-body.tp[body.ix[a+'_'+s]]) for a,b in [('thigh','calf'),('calf','foot')])/
        sum(np.linalg.norm(ref[ix[MAP[b+'_'+s]],:3]-ref[ix[MAP[a+'_'+s]],:3]) for a,b in [('thigh','calf'),('calf','foot')]) for s in 'lr'])
    floor=np.mean([body.tp[body.ix['ball_'+s],2]-ref[ix[MAP['ball_'+s]],2]*scale for s in 'lr'])
    cbody_origin=np.array([0.,0.,floor]);f[:,cbody,:3]=world[:,ix['Hips'],:3]*scale+cbody_origin
    body.set_world_rotations(f,desired)
    goals={s:world[:,ix[MAP['foot_'+s]],:3]*scale+cbody_origin for s in 'lr'}
    poles={s:world[:,ix[MAP['calf_'+s]],:3]*scale+cbody_origin for s in 'lr'}
    base.rig.old.steps.fit_legs(body,f,goals,{s:desired[body.ix['foot_'+s]] for s in 'lr'},poles)
    # Fit each complete source arm onto the actual native shoulder. The IK
    # correction only reconciles limb proportions, keeping donor axial roll.
    for side in 'lr':
        p,q=body.world(f);ui,ei,hi=[body.ix[k+'_'+side] for k in ('upperarm','lowerarm','hand')]
        su,se,sh=[ix[MAP[k+'_'+side]] for k in ('upperarm','lowerarm','hand')]
        length=np.linalg.norm(body.ref[ei,:3])+np.linalg.norm(body.ref[hi,:3])
        donor_length=np.linalg.norm(ref[se,:3]-ref[su,:3])+np.linalg.norm(ref[sh,:3]-ref[se,:3])
        goal=p[:,ui]+(world[:,sh,:3]-world[:,su,:3])*length/donor_length
        pole=p[:,ui]+(world[:,se,:3]-world[:,su,:3])*length/donor_length
        relative=R.from_quat(q[:,ei]).inv()*R.from_quat(q[:,hi])
        body.solve(f,[k+'_'+side for k in ('upperarm','lowerarm','hand')],goal,pole,R.from_quat(q[:,hi]))
        _,q=body.world(f);body.set_world_rotations(f,{hi:R.from_quat(q[:,ei])*relative})
        for i,name in enumerate(body.names):
            if name.endswith('_'+side) and name.startswith(('thumb_','index_','middle_','ring_','pinky_')):f[:,i]=body.idle[i]
    # Short native carry boundaries; the attack interior is the source take.
    enter=smooth(t/.16);leave=smooth((t-(t[-1]-.46))/.46);weight=enter*(1-leave)
    f=c.blend(np.repeat(body.idle[None],n,axis=0),f,weight[:,None,None])
    old.helpers(body,f);f[0]=body.idle;f[-1]=body.idle
    return carry.continuous(f),raw,clock

def main():
    inputs=json.loads((old.OUT/'inputs.json').read_text())
    cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    report=dict(version='Free3D source dual combo V1',bodies={},first_person_changed=False,runtime_tested=False)
    for label,source in inputs.items():
        data=base.rig.DATA[label];body=c.Body(data);body.idle=np.array(source['clips']['Dual.Idle']['frames'][0])
        active=cfg if label=='jason' else cfg['body_variants'][label];clips={}
        for role,fpname in [('Slash1','DualAttack'),('Slash2','DualAttack2')]:
            fp=old.fps_source(fpname);t=np.arange(len(fp['p']))/RATE
            f,raw,clock=build(body,role,t)
            prior=json.loads((old.OUT/(label+'-actions.json')).read_text())['clips']['Dual.'+role]
            clips['Dual.'+role]={**prior,'frames':f.tolist(),'source':raw['source'],
                'source_clock':clock,'adaptation':'Free3D full body source; native anatomical bind and chain proportions, original grip digits, in-place travel and FPS dual contact clock; second-stage offhand delayed in source chest space'}
            print('FREE3D_AUTHORED',label,role,len(f),flush=True)
        (OUT/(label+'-actions.json')).write_text(json.dumps(dict(mesh=data['mesh'],names=body.names,parents=body.parents,clips=clips),separators=(',',':')))
        report['bodies'][label]=dict(previous_roles={r:active['clips']['Kukri.FullBody.'+r] for r in clips},native_reference=data['authoring_reference_source'])
    (OUT/'authoring.json').write_text(json.dumps(report,indent=2))

if __name__=='__main__':main()
