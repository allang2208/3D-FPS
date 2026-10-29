"""Native dual carry, preserving the primary hand and sharing its idle with the spin."""
import importlib.util,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
spec=importlib.util.spec_from_file_location('dual_supported',ROOT/'SourceAssets/KukriDualWhirlwindRepair20261026/author.py')
dual=importlib.util.module_from_spec(spec);spec.loader.exec_module(dual)
base,c=dual.base,dual.c
ROLES=('Dual.Idle','Dual.Whirlwind.Start','Dual.Whirlwind.Loop','Dual.Whirlwind.End')

def left_bone(name):
    return name.endswith('_l') and name.startswith(('clavicle_','upperarm_','lowerarm_','hand_',
        'thumb_','index_','middle_','ring_','pinky_'))

def make_guard(body):
    f=body.idle[None].copy();ip,iq=body.world(body.idle)
    chest=body.ix['spine_05'];ci=body.ix['clavicle_l']
    torso=R.from_quat(iq[chest])*R.from_quat(body.tq[chest]).inv()
    # A low, forward-ready offhand. The elbow hangs outside the ribcage, while
    # the grip remains in front of the torso instead of folding across it.
    shoulder=torso*R.from_euler('y',-2.,degrees=True)*R.from_quat(body.tq[ci])
    body.set_world_rotations(f,{ci:R.from_quat(shoulder.as_quat()[None])})
    p,_=body.world(f);ui,ei,hi=[body.ix[k+'_l'] for k in ('upperarm','lowerarm','hand')]
    length=np.linalg.norm(body.ref[ei,:3])+np.linalg.norm(body.ref[hi,:3])
    goal=p[:,ui]+torso.apply([.26,.55,-.48])*length
    pole=p[:,ui]+torso.apply([.28,.10,-.60])*length
    axis,fq=dual.limb(body,f,'l',('upperarm','lowerarm','hand'),goal,pole)
    grip,mp,mq=dual.v1.left_grip(body)
    tip=c.unit(np.asarray(json.loads((ROOT/'SourceAssets/Kukri20261020/model.json').read_text())['tip_cm']))
    desired=torso.apply(c.unit(np.array([.28,.86,.42])))
    candidates=[]
    for bank in np.linspace(-50.,50.,201):
        fore=R.from_rotvec(axis[0]*np.radians(bank))*fq[0]
        hand=fore*R.from_quat(body.ref[hi,3:7])
        vector=(hand*mq).apply(tip)
        angle=np.degrees(np.arccos(np.clip(np.dot(vector,desired),-1.,1.)))
        candidates.append((angle*angle+.025*bank*bank,bank))
    bank=min(candidates)[1]
    fq=R.from_rotvec(axis*np.radians(bank))*fq
    hand=fq*R.from_quat(body.ref[hi,3:7])
    vector=(hand[0]*mq).apply(tip)
    swing=c.align(vector,desired).as_rotvec()
    wrist=np.linalg.norm(swing)
    swing*=min(1.,np.radians(12.)/max(1e-8,wrist))
    hand=R.from_rotvec(swing)*hand
    body.set_world_rotations(f,{ei:fq,hi:hand})
    for i,name in enumerate(body.names):
        if name.endswith('_l') and name.startswith(('thumb_','index_','middle_','ring_','pinky_')):f[:,i]=grip[i]
    derived=f.copy();base.native.native_twists(body,derived)
    for i,name in enumerate(body.names):
        if name.endswith('_l') and name.startswith(('upperarm_twist_','lowerarm_twist_')):f[:,i]=derived[:,i]
    return f[0],dict(forearm_bank_degrees=bank,wrist_swing_degrees=float(np.degrees(np.linalg.norm(swing))),
                    blade_direction_body=torso.inv().apply((hand[0]*mq).apply(tip)).tolist(),
                    hand_offset_arm_lengths=[.26,.55,-.48])

def carry_loop(body,original,guard):
    f=original.copy()
    for i,name in enumerate(body.names):
        if not left_bone(name):continue
        if name.startswith(('thumb_','index_','middle_','ring_','pinky_')):
            f[:,i]=guard[i]
        elif '_twist_' not in name:
            # Preserve the original idle's small local changes and its torso
            # breathing. Only the resting left-arm offset changes.
            delta=R.from_quat(original[0,i,3:7]).inv()*R.from_quat(guard[i,3:7])
            f[:,i,3:7]=(R.from_quat(original[:,i,3:7])*delta).as_quat()
    derived=f.copy();base.native.native_twists(body,derived)
    for i,name in enumerate(body.names):
        if name.endswith('_l') and name.startswith(('upperarm_twist_','lowerarm_twist_')):f[:,i]=derived[:,i]
    return f

def continuous(frames):
    for k in range(1,len(frames)):
        frames[k,:,3:7]*=np.where(np.sum(frames[k-1,:,3:7]*frames[k,:,3:7],axis=1)<0.,-1.,1.)[:,None]
    return frames

def clip(frames,source,adaptation):
    return dict(rate_num=120,rate_den=1,frames=continuous(frames).tolist(),contact=0.,release=.999,
                source=source,adaptation=adaptation)

def main():
    inputs=json.loads((OUT/'inputs.json').read_text())
    tuning=base.effective_tuning();times,cuts,_,_=base.timeline(tuning)
    report=dict(version='Third-person dual idle V1 and matched dual whirlwind V3',bodies={},
                first_person_changed=False,runtime_tested=False,rendered=False,tuning=tuning)
    for label,data in base.rig.DATA.items():
        source=inputs[label];body=c.Body(data);original=np.asarray(source['frames'])
        body.idle=original[0].copy()
        guard,info=make_guard(body)
        idle=carry_loop(body,original,guard)
        # Author the spin against exactly this new carry boundary. Do not put
        # a second late wrist correction on the old End clip.
        body.idle=idle[0].copy()
        motion,_=dual.make(body,label,tuning,times)
        clips={'Dual.Idle':clip(idle,source['asset'],
            'Original carry breathing and primary arm; native low forward offhand guard, bent elbow and stable knife grip')}
        for role,(a,b) in zip(ROLES[1:],cuts):
            clips[role]=clip(motion[a:b].copy(),'Dual V2 supported full-body spin',
                'Same support and weapon reach, authored from and back to the new dual carry with continuous elbow transport')
        (OUT/(label+'-actions.json')).write_text(json.dumps(dict(mesh=data['mesh'],names=body.names,parents=body.parents,clips=clips),separators=(',',':')))
        report['bodies'][label]=dict(mesh=data['mesh'],previous_roles=source['previous_roles'],
            source_idle=source['asset'],idle_duration=source['duration'],**info)
        print('DUAL_IDLE_AUTHORED',label,info,flush=True)
    (OUT/'authoring.json').write_text(json.dumps(report,indent=2))

if __name__=='__main__':main()
