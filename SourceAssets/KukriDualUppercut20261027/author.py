"""Dual third-person uppercut: native offhand clearance and matched dual carry."""
import importlib.util,json,hashlib
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.interpolate import CubicSpline

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
spec=importlib.util.spec_from_file_location('native_dual_carry',ROOT/'SourceAssets/KukriDualIdleThirdPerson20261027/author.py')
carry=importlib.util.module_from_spec(spec);spec.loader.exec_module(carry)
dual,base,c=carry.dual,carry.base,carry.c
ROLE='Dual.Uppercut'

def spline(keys,values,times):
    values=np.asarray(values,dtype=float)
    return CubicSpline(keys,values,bc_type=((1,np.zeros(values.shape[1:])),(1,np.zeros(values.shape[1:]))))(times)

def author(body,original,idle,rate):
    frames=original.copy();body.idle=idle.copy()
    n=len(frames);times=np.arange(n)/rate;duration=times[-1]
    weight=base.smooth(times/.16)*(1.-base.smooth((times-.86)/(duration-.86)))
    # The current dual carry is the actual boundary on both sides. Outside the
    # offhand chain the existing Meshy uppercut remains the performance source.
    boundary=base.smooth(times/.10)*(1.-base.smooth((times-.94)/(duration-.94)))
    frames=c.blend(np.repeat(idle[None],n,axis=0),frames,boundary[:,None,None])
    for i,name in enumerate(body.names):
        if carry.left_bone(name):frames[:,i]=idle[i]
    ip,iq=body.world(idle);p,q=body.world(frames)
    chest=body.ix['spine_05'];clavicle=body.ix['clavicle_l']
    torso=R.from_quat(q[:,chest])*R.from_quat(body.tq[chest]).inv()
    idle_torso=R.from_quat(iq[chest])*R.from_quat(body.tq[chest]).inv()
    transported=torso*idle_torso.inv()*R.from_quat(iq[clavicle])
    # Small scapular participation carries the elbow outside the ribcage.
    delta=R.from_euler('z',(-3.*weight)[:,None],degrees=True)
    body.set_world_rotations(frames,{clavicle:torso*delta*torso.inv()*transported})
    p,_=body.world(frames)
    ui,ei,hi=[body.ix[k+'_l'] for k in ('upperarm','lowerarm','hand')]
    length=np.linalg.norm(body.ref[ei,:3])+np.linalg.norm(body.ref[hi,:3])
    hand0=idle_torso.inv().apply(ip[hi]-ip[ui])/length
    elbow0=idle_torso.inv().apply(ip[ei]-ip[ui])/length
    # Load outboard before the main blade rises. The offhand then follows the
    # body's lift on its own side, without adding a second damage/contact beat.
    keys=[0.,.16,.29,.35,.433,.64,.90,duration]
    values=[hand0,[.34,.42,-.52],[.42,.34,-.50],[.48,.42,-.34],
            [.46,.44,-.26],[.38,.45,-.35],[.29,.51,-.45],hand0]
    local=spline(keys,values,times)*length
    goals=p[:,ui]+torso.apply(local)
    origin=p[:,ui]
    initial_axis=c.unit(torso.apply(np.tile(hand0,(n,1))))
    reach=c.unit(goals-origin)
    initial_bend=torso.apply(np.tile(elbow0,(n,1)))
    initial_bend=c.unit(initial_bend-initial_axis*np.sum(initial_bend*initial_axis,axis=1)[:,None])
    transported_bend=c.align(initial_axis,reach).apply(initial_bend)
    wanted=torso.apply(np.tile([.36,.12,-.58],(n,1)))
    wanted=c.unit(wanted-reach*np.sum(wanted*reach,axis=1)[:,None])
    roll=np.unwrap(np.arctan2(np.sum(reach*np.cross(transported_bend,wanted),axis=1),
                            np.sum(transported_bend*wanted,axis=1)))
    bend=R.from_rotvec(reach*(roll*weight)[:,None]).apply(transported_bend)
    _,forearm=dual.limb(body,frames,'l',('upperarm','lowerarm','hand'),goals,origin+bend*length)
    # The new carry already has a supported forearm bank and bounded wrist.
    # Keep that same local wrist and closed grip throughout the counter-motion.
    body.set_world_rotations(frames,{hi:forearm*R.from_quat(idle[hi,3:7])})
    for i,name in enumerate(body.names):
        if name.endswith('_l') and name.startswith(('thumb_','index_','middle_','ring_','pinky_')):frames[:,i]=idle[i]
    derived=frames.copy();base.native.native_twists(body,derived)
    seed=idle[None].copy();base.native.native_twists(body,seed)
    for i,name in enumerate(body.names):
        if name.endswith('_l') and name.startswith(('upperarm_twist_','lowerarm_twist_')):
            offset=R.from_quat(idle[i,3:7])*R.from_quat(seed[0,i,3:7]).inv()
            correction=R.from_quat(c.slerp([0.,0.,0.,1.],offset.as_quat(),(1.-weight)[:,None]))
            frames[:,i,3:7]=(correction*R.from_quat(derived[:,i,3:7])).as_quat()
    frames[0]=idle;frames[-1]=idle
    for k in range(1,n):
        frames[k,:,3:7]*=np.where(np.sum(frames[k-1,:,3:7]*frames[k,:,3:7],axis=1)<0.,-1.,1.)[:,None]
    return frames

def main():
    cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    upper_dir=ROOT/'SourceAssets/KukriMeshyUppercut20261025'
    carry_dir=ROOT/'SourceAssets/KukriDualIdleThirdPerson20261027'
    upper_receipt=json.loads((upper_dir/'assets-saved.json').read_text())
    carry_receipt=json.loads((carry_dir/'assets-saved.json').read_text())
    report=dict(version='Dual uppercut V1',bodies={},runtime_tested=False,rendered=False,
                first_person_changed=False,gameplay_changed=False)
    for label,data in base.rig.DATA.items():
        active=cfg if label=='jason' else cfg['body_variants'][label]
        sources={}
        for directory,receipt,role in [(upper_dir,upper_receipt,'Uppercut'),(carry_dir,carry_receipt,'Dual.Idle')]:
            raw=(directory/(label+'-actions.json')).read_bytes();record=receipt['bodies'][label]
            if hashlib.sha256(raw).hexdigest()!=record['source_sha256'] or active['clips']['Kukri.FullBody.'+role]!=record['clips']['Kukri.FullBody.'+role]:
                raise RuntimeError('Active source changed: '+label+' '+role)
            source=json.loads(raw)
            if source['names']!=data['names'] or source['mesh']!=active['body_mesh']:raise RuntimeError('Native body source mismatch')
            sources[role]=source['clips'][role]
        original=sources['Uppercut'];idle=np.asarray(sources['Dual.Idle']['frames'][0])
        body=c.Body(data);frames=author(body,np.asarray(original['frames']),idle,original['rate'])
        clip=dict(rate_num=original['rate'],rate_den=1,frames=frames.tolist(),contact=original['contact'],release=original['release'],
            source='User Meshy Charged_Upward_Slash uppercut V5 and current native dual carry',
            adaptation='Main rising slash and original contact clock; offhand blade clears outboard, follows torso lift, retains native grip and returns continuously to dual carry')
        (OUT/(label+'-actions.json')).write_text(json.dumps(dict(mesh=data['mesh'],names=body.names,parents=body.parents,clips={ROLE:clip}),separators=(',',':')))
        report['bodies'][label]=dict(mesh=data['mesh'],previous_roles={ROLE:active['clips'].get('Kukri.FullBody.'+ROLE)},
            source_uppercut=active['clips']['Kukri.FullBody.Uppercut'],source_idle=active['clips']['Kukri.FullBody.Dual.Idle'],
            frames=len(frames),rate=original['rate'],contact=original['contact'],release=original['release'])
        print('DUAL_UPPERCUT_AUTHORED',label,len(frames),flush=True)
    (OUT/'authoring.json').write_text(json.dumps(report,indent=2))

if __name__=='__main__':main()
