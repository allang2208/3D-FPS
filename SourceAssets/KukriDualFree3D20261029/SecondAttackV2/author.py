"""Refine only the second dual slash: anticipate, alternate, then recover.

Reuse Free3D's complete arm chains with independent preparation clocks. Keep
the existing two contact times, native fingers, knife mounts and clip length.
"""
import importlib.util,json
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.spatial.transform import Rotation as R

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]
spec=importlib.util.spec_from_file_location('free3d_v1',OUT.parent/'author.py')
v1=importlib.util.module_from_spec(spec);spec.loader.exec_module(v1)
c,old,base,carry=v1.c,v1.old,v1.base,v1.carry
RATE=120

def curve(t,keys,values):
    return PchipInterpolator(keys,values)(t)

def donor(role,t):
    raw=json.loads((OUT.parent/'Slash2-source.json').read_text())
    ix={n:i for i,n in enumerate(raw['names'])}
    ref=v1.converted(raw['reference_world']);frames=v1.converted(raw['frames']);end=t[-1]
    # Sustain the loaded stance through the second cut. Stop before the
    # source's straight-legged rest, then let native carry blending recover.
    body_keys=[0.,.12,.38,.50,.66,.86,1.08,1.30,end]
    body_values=[0.,.23,.73,.88,.94,1.00,1.08,1.16,1.16]
    body_time=curve(t,body_keys,body_values)
    world=np.array([c.sample(frames,float(s),raw['rate']) for s in body_time])
    hip,chest=ix['Hips'],ix['Spine2']
    path=np.array([frames[0,hip,:2],frames[-1,hip,:2]])
    travel=curve(body_time,[0.,raw['duration']],path)
    world[...,:2]-=travel[:,None,:]
    # Both arms prepare from the beginning. The left holds a supported high
    # guard while the right cuts, instead of remaining frozen at rest for .5s.
    clocks={
        'Right':([0.,.12,.28,.38,.50,.65,.84,1.10,1.30,end],
                 [0.,.23,.58,.73,.90,1.14,1.32,1.40,1.40,1.40]),
        'Left': ([0.,.12,.28,.48,.62,.74,.88,1.02,1.20,1.30,end],
                 [0.,.20,.36,.40,.45,.60,.77,.91,1.10,1.22,1.22])}
    dst=R.from_quat(world[:,chest,3:7])
    for side,(keys,values) in clocks.items():
        times=curve(t,keys,values)
        sampled=np.array([c.sample(frames,float(s),raw['rate']) for s in times])
        transport=dst*R.from_quat(sampled[:,chest,3:7]).inv()
        for name,i in ix.items():
            if not name.startswith(side) or any(z in name for z in ('UpLeg','Leg','Foot','Toe')):continue
            world[:,i,:3]=world[:,chest,:3]+transport.apply(sampled[:,i,:3]-sampled[:,chest,:3])
            world[:,i,3:7]=(transport*R.from_quat(sampled[:,i,3:7])).as_quat()
    return world,ref,ix,raw,{'body':dict(target_seconds=body_keys,source_seconds=body_values),
        'arms':{k:dict(target_seconds=a,source_seconds=b) for k,(a,b) in clocks.items()},
        'contact_seconds':{'right':.38,'left':.88},'constant_offhand_delay_removed':True}

def hand_lanes(body,f,t):
    """Separate the complete chains, retain bent elbows and share wrist roll."""
    n=len(t);ip,iq=body.world(body.idle)
    p,q=body.world(f);chest=body.ix['spine_05']
    torso=R.from_quat(q[:,chest])*R.from_quat(body.tq[chest]).inv()
    active=v1.smooth(t/.16)*(1.-v1.smooth((t-1.12)/(t[-1]-1.12)))
    for side in ('r','l'):
        p,q=body.world(f);ui,ei,hi=[body.ix[k+'_'+side] for k in ('upperarm','lowerarm','hand')]
        length=np.linalg.norm(body.ref[ei,:3])+np.linalg.norm(body.ref[hi,:3]);size=length/60.
        if side=='l':
            key=[0.,.12,.28,.50,.66,.76,.88,1.02,1.20,t[-1]]
            offsets=np.array([[0,0,0],[6,5,0],[18,8,0],[22,9,0],[24,9,0],[20,8,0],[8,5,0],[3,3,0],[0,0,0],[0,0,0]])
            move=curve(t,key,offsets)*active[:,None]*size
            elbow=np.array([9.,5.,0.])[None]*active[:,None]*size
        else:
            key=[0.,.12,.28,.38,.50,.65,.84,1.1,t[-1]]
            offsets=np.array([[0,0,0],[-3,6,0],[-3,6,0],[-4,5,-2],[-8,5,-5],[-6,4,-3],[-3,3,0],[0,0,0],[0,0,0]])
            move=curve(t,key,offsets)*active[:,None]*size
            elbow=np.array([-4.,4.,0.])[None]*active[:,None]*size
        goal=p[:,hi]+torso.apply(move)
        pole=p[:,ei]+torso.apply(elbow)
        reach=goal-p[:,ui];dist=np.linalg.norm(reach,axis=1)
        goal=p[:,ui]+reach*np.minimum(1.,length*.965/np.maximum(dist,1e-9))[:,None]
        relative=R.from_quat(q[:,ei]).inv()*R.from_quat(q[:,hi])
        body.solve(f,[k+'_'+side for k in ('upperarm','lowerarm','hand')],goal,pole,R.from_quat(q[:,hi]))
        _,q=body.world(f)
        fore=R.from_quat(q[:,ei]);wanted=fore*relative
        neutral=R.from_quat(body.idle[hi,3:7]);axis=c.unit(body.ref[hi,:3])
        delta=(relative*neutral.inv()).as_quat()
        twist=c.unit(np.c_[(delta[:,:3]@axis)[:,None]*axis,delta[:,3]])
        angle=np.unwrap(2*np.arctan2(twist[:,:3]@axis,twist[:,3]))
        angle-=2*np.pi*round(float(angle[0])/(2*np.pi))
        # Axial forearm roll leaves the elbow and hand positions unchanged;
        # carry most of the turn here instead of twisting the wrist alone.
        share=np.radians(42.)*np.tanh(.70*angle/np.radians(42.))*active
        fore=fore*R.from_rotvec(axis[None]*share[:,None])
        residual=(fore.inv()*wanted*neutral.inv()).as_quat()
        tw=c.unit(np.c_[(residual[:,:3]@axis)[:,None]*axis,residual[:,3]])
        ta=np.unwrap(2*np.arctan2(tw[:,:3]@axis,tw[:,3]))
        ta-=2*np.pi*round(float(ta[0])/(2*np.pi))
        # Only soften the excess; retain small source wrist articulation.
        limit=np.radians(30.)
        limited=np.sign(ta)*np.where(abs(ta)<=limit,abs(ta),limit+np.radians(10.)*np.tanh((abs(ta)-limit)/np.radians(10.)))
        ta=ta+(limited-ta)*active
        swing=(R.from_quat(residual)*R.from_quat(tw).inv()).as_rotvec()
        amount=np.linalg.norm(swing,axis=1);bend_limit=np.radians(32.)
        capped=np.where(amount<=bend_limit,amount,bend_limit+np.radians(8.)*np.tanh((amount-bend_limit)/np.radians(8.)))
        bend=amount+(capped-amount)*active
        sw=R.from_rotvec(swing*(bend/np.maximum(amount,1e-9))[:,None])
        hand=fore*sw*R.from_rotvec(axis[None]*ta[:,None])*neutral
        body.set_world_rotations(f,{ei:fore,hi:hand})
    old.helpers(body,f);f[0]=body.idle;f[-1]=body.idle
    return carry.continuous(f)

def main():
    inputs=json.loads((old.OUT/'inputs.json').read_text())
    cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    report=dict(version='Free3D second dual attack V2',bodies={},rendered=False,runtime_tested=False,first_person_changed=False)
    v1.donor=donor
    for label in ('jason','kaitlin'):
        data=base.rig.DATA[label];body=c.Body(data)
        body.idle=np.array(inputs[label]['clips']['Dual.Idle']['frames'][0])
        prior=json.loads((OUT.parent/(label+'-actions.json')).read_text())['clips']['Dual.Slash2']
        t=np.arange(len(prior['frames']))/RATE
        f,raw,clock=v1.build(body,'Slash2',t);f=hand_lanes(body,f,t)
        clip={**prior,'frames':f.tolist(),'source_clock':clock,
            'adaptation':'Second attack V2: shared anticipation, staggered cuts, separate arm lanes, distributed wrist/forearm rotation, supported direct carry recovery'}
        (OUT/(label+'-actions.json')).write_text(json.dumps(dict(mesh=data['mesh'],names=body.names,parents=body.parents,clips={'Dual.Slash2':clip}),separators=(',',':')))
        active=cfg if label=='jason' else cfg['body_variants'][label]
        report['bodies'][label]=dict(previous_roles={'Dual.Slash2':active['clips']['Kukri.FullBody.Dual.Slash2']},native_reference=data['authoring_reference_source'])
        print('SECOND_ATTACK_V2_AUTHORED',label,len(f),flush=True)
    (OUT/'authoring.json').write_text(json.dumps(report,indent=2))

if __name__=='__main__':main()
