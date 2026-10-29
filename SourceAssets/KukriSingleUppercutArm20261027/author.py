"""Rebuild only the single-hand uppercut's right shoulder/elbow/wrist chain.

The installed FPS uppercut supplies the low-right load, rising stroke and held
follow-through. A native two-bone hinge and a continuous forearm bank adapt it
to the full body. Hand, fingers and blade remain one grip; the wrist is never
independently forced to satisfy the camera-space blade direction.
"""
import importlib.util
import json
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.spatial.transform import Rotation as R

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
spec=importlib.util.spec_from_file_location('upper_lower',ROOT/'SourceAssets/KukriUppercutSwordLower20261027/author.py')
lower=importlib.util.module_from_spec(spec);spec.loader.exec_module(lower)
base,c=lower.base,lower.c
RATE=120
INPUT=json.loads((OUT/'inputs.json').read_text())
SOURCE=INPUT['native'];SI={name:i for i,name in enumerate(SOURCE['names'])}
SF=np.asarray(SOURCE['uppercut']['frames']);S0=np.asarray(SOURCE['idle']['frames'][0])
FORWARD=R.from_euler('z',180.,degrees=True)


def solve_chain(body,origin,goal,bend,beta,bank,ip,iq):
    ui,ei,hi=[body.ix[name+'_r'] for name in ('upperarm','lowerarm','hand')]
    l1=np.linalg.norm(body.ref[ei,:3]);l2=np.linalg.norm(body.ref[hi,:3])
    axis=c.unit(goal-origin)
    distance=np.linalg.norm(goal-origin,axis=-1)
    along=(l1*l1-l2*l2+distance*distance)/(2.*distance)
    rotated=R.from_rotvec(axis*beta[...,None]).apply(bend)
    elbow=origin+axis*along[...,None]+rotated*np.sqrt(np.maximum(0.,l1*l1-along*along))[...,None]
    upper=elbow-origin;fore=goal-elbow
    ru=ip[ei]-ip[ui];rf=ip[hi]-ip[ei]
    uq=c.frame(upper,fore)*c.frame(ru,rf).inv()*R.from_quat(iq[ui])
    fq=c.frame(fore,upper)*c.frame(rf,ru).inv()*R.from_quat(iq[ei])
    fq=R.from_rotvec(c.unit(fore)*bank[...,None])*fq
    return elbow,uq,fq


def choose_support(body,origin,goal,bend,desired,torso,ip,iq,weight):
    """Jointly choose elbow plane and forearm roll on one continuous path."""
    betas,banks=np.meshgrid(np.radians(np.arange(-50.,51.,10.)),np.radians(np.arange(-70.,71.,10.)),indexing='ij')
    candidates=np.c_[betas.ravel(),banks.ravel()]
    n=len(goal);count=len(candidates);costs=np.empty((n,count))
    hi=body.ix['hand_r'];wrist=R.from_quat(body.idle[hi,3:7])
    for k in range(n):
        aa=np.repeat(origin[k][None],count,axis=0)
        gg=np.repeat(goal[k][None],count,axis=0)
        bb=np.repeat(bend[k][None],count,axis=0)
        elbow,upper,fore=solve_chain(body,aa,gg,bb,candidates[:,0]*weight[k],candidates[:,1]*weight[k],ip,iq)
        # A comfortable native wrist is preferred; the blade follows the same
        # hand transform. Extra elbow/forearm rotation is paid for explicitly.
        residual=(fore*wrist).inv()*desired[k]
        local_elbow=torso[k].inv().apply(elbow-aa)
        inside=np.maximum(0.,local_elbow[:,0]-2.)/10.
        above=np.maximum(0.,local_elbow[:,2]-5.)/10.
        costs[k]=residual.magnitude()**2+.14*candidates[:,0]**2+.055*candidates[:,1]**2+2.*inside**2+1.5*above**2
    # Global path selection avoids choosing a different elbow branch whenever
    # the fast rising stroke makes two local solutions momentarily similar.
    transition=2.*np.sum((candidates[:,None]-candidates[None])**2,axis=2)
    back=np.zeros((n,count),dtype=np.int32);score=costs[0].copy()
    for k in range(1,n):
        options=score[:,None]+transition
        back[k]=np.argmin(options,axis=0)
        score=costs[k]+options[back[k],np.arange(count)]
    states=np.empty(n,dtype=np.int32);states[-1]=int(np.argmin(score))
    for k in range(n-1,0,-1):states[k-1]=back[k,states[k]]
    angles=gaussian_filter1d(candidates[states],1.5,axis=0,mode='nearest')*weight[:,None]
    return angles


def rebuild(body,original):
    frames=original.copy();idle=frames[0].copy();body.idle=idle.copy()
    n=len(frames);times=np.arange(n)/RATE;duration=times[-1]
    weight=base.smooth(times/.15)*(1.-base.smooth((times-.86)/(duration-.86)))
    ip,iq=body.world(idle);p,q=body.world(frames)
    chest=body.ix['spine_05'];clavicle=body.ix['clavicle_r']
    ui,ei,hi=[body.ix[name+'_r'] for name in ('upperarm','lowerarm','hand')]
    torso=R.from_quat(q[:,chest])*R.from_quat(body.tq[chest]).inv()
    idle_torso=R.from_quat(iq[chest])*R.from_quat(body.tq[chest]).inv()
    lift=base.smooth((times-.27)/.16)*(1.-base.smooth((times-.65)/.23))*weight
    scapula=R.from_euler('y',(5.*lift)[:,None],degrees=True)*R.from_euler('z',(-4.*lift)[:,None],degrees=True)
    cq=torso*scapula*idle_torso.inv()*R.from_quat(iq[clavicle])
    # Use native translations and helper bases throughout the complete arm.
    for i,name in enumerate(body.names):
        if name.endswith('_r') and name.startswith(('clavicle_','upperarm_','lowerarm_','hand_')):
            frames[:,i,:3]=body.ref[i,:3]
            frames[:,i,7:]=body.ref[i,7:]
    body.set_world_rotations(frames,{clavicle:cq})
    p,_=body.world(frames);origin=p[:,ui]
    length=np.linalg.norm(body.ref[ei,:3])+np.linalg.norm(body.ref[hi,:3])
    source_length=np.mean(np.linalg.norm(SF[:,SI['lowerarm_r'],:3]-SF[:,SI['upperarm_r'],:3],axis=1)+
                          np.linalg.norm(SF[:,SI['hand_r'],:3]-SF[:,SI['lowerarm_r'],:3],axis=1))
    source=np.array([c.sample(SF,float(t),SOURCE['uppercut']['rate']) for t in times])
    hand=FORWARD.apply(source[:,SI['hand_r'],:3]-source[:,SI['upperarm_r'],:3])*length/source_length
    # Keep the FPS phrasing, but place the load in front of the hip and the
    # follow-through in front of the shoulder instead of behind the torso.
    local=np.c_[.70*hand[:,0]-.12*length,.55*hand[:,1]+.36*length,1.15*hand[:,2]-.26*length]
    load=base.smooth(times/.10)*(1.-base.smooth((times-.24)/.08))
    local[:,2]-=.34*length*load
    local0=idle_torso.inv().apply(ip[hi]-ip[ui])
    local=local0+(local-local0)*weight[:,None]
    # Leave elbow flexion at the largest reach. Do not stretch native bones.
    reach=np.linalg.norm(local,axis=1)
    local*=np.minimum(1.,.94*length/np.maximum(reach,1e-6))[:,None]
    goal=origin+torso.apply(local)
    initial_axis=c.unit(torso.apply(np.tile(local0,(n,1))))
    initial_bend=torso.apply(np.tile(idle_torso.inv().apply(ip[ei]-ip[ui]),(n,1)))
    initial_bend=c.unit(initial_bend-initial_axis*np.sum(initial_bend*initial_axis,axis=1)[:,None])
    bend=c.align(initial_axis,c.unit(goal-origin)).apply(initial_bend)
    fps_delta=FORWARD*R.from_quat(source[:,SI['hand_r'],3:7])*R.from_quat(S0[SI['hand_r'],3:7]).inv()*FORWARD.inv()
    local_hand=idle_torso.inv()*R.from_quat(iq[hi])
    guided=R.from_quat(c.slerp(local_hand.as_quat(),(fps_delta*local_hand).as_quat(),weight[:,None]))
    desired=torso*guided
    angles=choose_support(body,origin,goal,bend,desired,torso,ip,iq,weight)
    elbow,upper,fore=solve_chain(body,origin,goal,bend,angles[:,0],angles[:,1],ip,iq)
    # Forearm rotation carries most of the blade turn. Only a small continuous
    # residual is allowed at the wrist relative to its supported native carry.
    baseline=R.from_quat(idle[hi,3:7]);relative=(fore.inv()*desired*baseline.inv()).as_quat()
    axis=c.unit(body.ref[hi,:3])
    twist=c.unit(np.c_[(relative[:,:3]@axis)[:,None]*axis,relative[:,3]])
    angle=np.unwrap(2.*np.arctan2(twist[:,:3]@axis,twist[:,3]))
    angle-=2.*np.pi*round(float(angle[0])/(2.*np.pi))
    limited_twist=R.from_rotvec(axis[None]*(np.radians(15.)*np.tanh(angle/np.radians(15.))*weight)[:,None])
    swing=R.from_quat(relative)*R.from_quat(twist).inv();v=swing.as_rotvec();a=np.linalg.norm(v,axis=1)
    limit=np.radians(12.)
    limited_swing=R.from_rotvec(v*(limit*np.tanh(a/limit)/np.maximum(a,1e-9)*weight)[:,None])
    final_hand=fore*limited_swing*limited_twist*baseline
    body.set_world_rotations(frames,{ui:upper,ei:fore,hi:final_hand})
    # Rebuild only this arm's twist helpers and preserve their native carry
    # offsets. No corrective rotation is copied onto the free left hand.
    derived=frames.copy();base.native.native_twists(body,derived)
    seed=idle[None].copy();base.native.native_twists(body,seed)
    for i,name in enumerate(body.names):
        if name.endswith('_r') and name.startswith(('upperarm_twist_','lowerarm_twist_')):
            offset=R.from_quat(idle[i,3:7])*R.from_quat(seed[0,i,3:7]).inv()
            frames[:,i,3:7]=(offset*R.from_quat(derived[:,i,3:7])).as_quat()
    frames[0]=original[0];frames[-1]=original[-1]
    for k in range(1,n):
        frames[k,:,3:7]*=np.where(np.sum(frames[k-1,:,3:7]*frames[k,:,3:7],axis=1)<0.,-1.,1.)[:,None]
    return frames,dict(elbow_plane_degrees=np.degrees(angles[:,0]).tolist(),forearm_bank_degrees=np.degrees(angles[:,1]).tolist(),
                       native_arm_length_cm=float(length),source_arm_length_cm=float(source_length),
                       wrist_residual_swing_limit_degrees=12,wrist_residual_twist_limit_degrees=15)


def main():
    cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    report=dict(version='Single uppercut native arm V1',source=SOURCE['uppercut']['asset'],bodies={},
                first_person_changed=False,dual_changed=False,runtime_tested=False,rendered=False)
    for label,data in base.rig.DATA.items():
        active=cfg if label=='jason' else cfg['body_variants'][label]
        captured=INPUT['targets'][label]
        if data['names']!=captured['names'] or active['body_mesh']!=captured['mesh'] or active['clips']['Kukri.FullBody.Uppercut']!=captured['previous']['asset']:
            raise RuntimeError('Current single uppercut input changed: '+label)
        original=captured['previous'];frames,detail=rebuild(c.Body(data),np.asarray(original['frames']))
        duration=(len(frames)-1)/RATE
        clip=dict(rate_num=RATE,rate_den=1,frames=frames.tolist(),contact=original['markers']['Contact']/duration,
                  release=original['markers']['Release']/duration,source=SOURCE['uppercut']['asset'],
                  adaptation='Native right arm from installed FPS uppercut phrasing; continuous elbow plane and forearm bank, supported wrist, unchanged grip and upright sword lower body')
        (OUT/(label+'-actions.json')).write_text(json.dumps(dict(mesh=data['mesh'],names=data['names'],parents=data['parents'],clips={'Uppercut':clip}),separators=(',',':')))
        report['bodies'][label]=dict(mesh=data['mesh'],previous_roles={'Uppercut':original['asset']},
                                   source_idle=captured['idle_asset'],frames=len(frames),**detail)
        print('SINGLE_UPPERCUT_ARM_AUTHORED',label,len(frames),flush=True)
    (OUT/'authoring.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__':main()
