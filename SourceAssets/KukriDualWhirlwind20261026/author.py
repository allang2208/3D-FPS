"""Third-person dual kukri whirlwind on the accepted lowering/spin timeline.

Both native weapon arms extend at the turn, retain fixed anatomical grips,
and return on the existing recovery clock. First-person motion is read-only.
"""
import importlib.util
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
spec=importlib.util.spec_from_file_location('dual_spin_base',ROOT/'SourceAssets/KukriWindmillDetail20261026/author.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
c=base.c
DUAL_SOURCE=ROOT/'SourceAssets/DualKukriIdle20261025/Clips/DualIdle.json'
ROLES=tuple('Dual.'+r for r in base.ROLES)


def native_left():
    source=c.INPUT['native'];names=source['names'];parents=source['parents']
    clip=json.loads(DUAL_SOURCE.read_text());local=clip['frames'][0]
    world=np.zeros((len(names),10));world[:,6]=1.;world[:,7:]=1.
    for i,name in enumerate(names):
        p,q,s=local[name];q=R.from_quat([q[1],q[2],q[3],q[0]])
        par=parents[i]
        if par>=0:
            parent=R.from_quat(world[par,3:7]);p=world[par,:3]+parent.apply(np.asarray(p)*world[par,7:])
            q=parent*q;s=np.asarray(s)*world[par,7:]
        world[i]=np.r_[p,q.as_quat(),s]
    rel=json.loads((DUAL_SOURCE.parents[1]/'left_kukri.json').read_text())['rel_to_hand_l']
    q=rel['rotation_wxyz']
    return source,world,np.asarray(rel['location']),R.from_quat([q[1],q[2],q[3],q[0]])


SOURCE,HOLD,BLADE_POS,BLADE_ROT=native_left()
SI={n:i for i,n in enumerate(SOURCE['names'])};SR=np.asarray(SOURCE['reference_world'])


def left_grip(body):
    """Match FFPSBodyGripRig's native palm registration and finite digit IK."""
    hi=SI['hand_l'];hand=body.ix['hand_l'];target=R.from_quat(body.tq[hand])
    sh=R.from_quat(SR[hi,3:7]);hp=HOLD[hi,:3];hr=R.from_quat(HOLD[hi,3:7])
    a=np.array([sh.inv().apply(SR[SI[d+'_01_l'],:3]-SR[hi,:3]) for d in ('index','middle','pinky')])
    b=np.array([target.inv().apply(body.tp[body.ix[d+'_01_l']]-body.tp[hand]) for d in ('index','middle','pinky')])
    mount=c.frame(b[1],b[0]-b[2])*c.frame(a[1],a[0]-a[2]).inv()
    offset=b.mean(0)-mount.apply(a.mean(0))
    transfer=target*mount*hr.inv();desired={};frame=body.ref[None].copy()
    for digit in ('thumb','index','middle','ring','pinky'):
        names=[f'{digit}_{j:02d}_l' for j in (1,2,3)]
        for j,name in enumerate(names):
            ia,ib=(j,j+1) if j<2 else (1,2)
            src=R.from_quat(SR[SI[name],3:7]).inv().apply(SR[SI[names[ib]],:3]-SR[SI[names[ia]],:3])
            dst=R.from_quat(body.tq[body.ix[name]]).inv().apply(body.tp[body.ix[names[ib]]]-body.tp[body.ix[names[ia]]])
            desired[body.ix[name]]=transfer*R.from_quat(HOLD[SI[name],3:7])*c.align(dst,src)
    body.set_world_rotations(frame,{i:R.from_quat(q.as_quat()[None]) for i,q in desired.items()})
    for digit in ('thumb','index','middle','ring','pinky'):
        names=[f'{digit}_{j:02d}_l' for j in (1,2,3)]
        points=[body.tp[hand]+target.apply(mount.apply(hr.inv().apply(HOLD[SI[n],:3]-hp))+offset) for n in names]
        body.solve(frame,names,np.asarray(points[2])[None],np.asarray(points[1])[None],R.from_quat(desired[body.ix[names[2]]].as_quat()[None]))
    for i,name in enumerate(body.names):
        par=body.parents[i]
        if name.endswith('_l') and '_half_' in name and par in desired:
            delta=R.from_quat(body.ref[par,3:7]).inv()*R.from_quat(frame[0,par,3:7])
            frame[0,i,3:7]=(R.from_rotvec(-.5*delta.as_rotvec())*R.from_quat(body.ref[i,3:7])).as_quat()
    return frame[0],mount.apply(BLADE_POS)+offset,mount*BLADE_ROT


def weapon_arm(body,frames,goals,poles,hand):
    """Native left elbow supports its own palm; no copied right local axes."""
    p,_=body.world(frames);ui,ei,hi=[body.ix[n+'_l'] for n in ('upperarm','lowerarm','hand')]
    origin=p[:,ui];l1=np.linalg.norm(body.ref[ei,:3]);l2=np.linalg.norm(body.ref[hi,:3])
    axis=c.unit(goals-origin);distance=np.clip(np.linalg.norm(goals-origin,axis=1),abs(l1-l2)+.02,(l1+l2)*.98)
    support=hand*R.from_quat(body.ref[hi,3:7]).inv()
    preferred=support.apply(np.tile(c.unit(body.ref[hi,:3]),(len(frames),1)))
    projection=np.sum(axis*preferred,axis=1)
    reach=l2*projection+np.sqrt(np.maximum(0.,l1*l1-l2*l2*(1-projection*projection)))
    distance+=np.clip(reach-distance,-2.*body.scale/94.,0.)
    bend=poles-origin;bend=c.unit(bend-axis*np.sum(bend*axis,axis=1)[:,None])
    neutral=c.unit(-preferred+axis*projection[:,None]);bend=c.unit(.2*bend+.8*neutral)
    along=(l1*l1-l2*l2+distance*distance)/(2*distance)
    elbow=origin+axis*along[:,None]+bend*np.sqrt(np.maximum(0.,l1*l1-along*along))[:,None]
    upper=elbow-origin;fore=origin+axis*distance[:,None]-elbow
    fq=c.align(support.apply(np.tile(body.ref[hi,:3],(len(frames),1))),fore)*support
    support_upper=fq*R.from_quat(body.ref[ei,3:7]).inv()
    uq=c.align(support_upper.apply(np.tile(body.ref[ei,:3],(len(frames),1))),upper)*support_upper
    body.set_world_rotations(frames,{ui:uq,ei:fq,hi:hand})


def make(body,label,tuning,times,keys,poses):
    frames=base.make_body(body,label,tuning,times,keys,poses)
    original=frames.copy();count=len(times);ready,spin,recover=[tuning[k] for k in ('readySeconds','spinSeconds','recoverSeconds')]
    stop=ready+spin;u=np.clip((times-ready)/spin,0.,1.)
    grid=np.linspace(0.,1.,4097)
    deploy_u=np.interp(110./abs(tuning['turnDegrees']),base.old.arms.phase(grid),grid)
    release=base.smooth(u/deploy_u)
    p,_,chest=base.old.arms.chest(body,frames)
    forward=chest.apply(np.tile([0.,1.,0.],(count,1)))
    heading=R.from_euler('z',np.arctan2(-forward[:,0],forward[:,1])[:,None])
    ui,ei,hi=[body.ix[n+'_l'] for n in ('upperarm','lowerarm','hand')]
    length=np.linalg.norm(body.ref[ei,:3])+np.linalg.norm(body.ref[hi,:3])
    ip,iq=body.world(body.idle)
    idle_chest=R.from_quat(iq[body.ix['spine_03']])*R.from_quat(body.tq[body.ix['spine_03']]).inv()
    idle_right=idle_chest.inv().apply(ip[body.ix['hand_r']]-ip[body.ix['upperarm_r']])/length
    values=[idle_right if k['right'] is None else np.asarray(k['right']) for k in poses]
    # Opposite radial reach; both blades lead in the same rotation direction.
    local=base.spline(keys,values,times)*np.array([-1.,-1.,1.])*length
    goals=p[:,ui]+heading.apply(local)
    pole=p[:,ui]+heading.apply(np.tile([.48,.30,-.04],(count,1))*length)
    held,mount_pos,mount_rot=left_grip(body)
    tip=c.unit(np.asarray(json.loads((ROOT/'SourceAssets/Kukri20261020/model.json').read_text())['tip_cm']))
    sign=np.sign(tuning['turnDegrees'])
    direction=heading.apply(np.tile([np.cos(np.radians(40)),sign*np.sin(np.radians(40)),0.],(count,1)))
    # Either face has a horizontal long axis. Choose the single bank whose
    # native left palm points down the extended forearm; reflecting the right
    # blade and then reversing its lead can otherwise fold the left wrist.
    axis=c.unit(goals-p[:,ui]);spin_frames=(times>=ready+.25*spin)&(times<=stop)
    banks=[]
    for face in (-1.,1.):
        candidate=c.frame(direction,np.tile([0.,0.,face],(count,1)))*c.frame(tip,np.array([0.,1.,0.])).inv()
        hand=candidate*mount_rot.inv()
        fore=(hand*R.from_quat(body.ref[hi,3:7]).inv()).apply(np.tile(c.unit(body.ref[hi,:3]),(count,1)))
        banks.append((float(np.mean(np.sum(axis[spin_frames]*fore[spin_frames],axis=1))),face,candidate))
    _,face,blade=max(banks,key=lambda item:item[0])
    weapon_arm(body,frames,goals,pole,blade*mount_rot.inv())
    start=int(np.searchsorted(times,ready-1e-8));full=int(np.flatnonzero(release>=1.-1e-8)[0]);end=int(np.searchsorted(times,stop-1e-8))
    for i,name in enumerate(body.names):
        if not name.endswith('_l') or not name.startswith(('clavicle_','upperarm_','lowerarm_','hand_')):continue
        if '_twist_' in name:continue
        frames[:start,i]=original[:start,i]
        frames[start:full+1,i,3:7]=c.slerp(original[start,i,3:7],frames[full,i,3:7],release[start:full+1,None])
        frames[end:,i,3:7]=c.slerp(frames[end,i,3:7].copy(),body.idle[i,3:7],base.smooth((times[end:]-stop)/recover)[:,None])
    # Closed grip for the entire take, including windup/recovery. The weapon
    # remains fixed to this same palm mount at runtime.
    for i,name in enumerate(body.names):
        if name.endswith('_l') and name.startswith(('thumb_','index_','middle_','ring_','pinky_')):frames[:,i]=held[i]
    base.native.native_twists(body,frames)
    idle=body.idle[None].copy();base.native.native_twists(body,idle)
    amount=release*(1.-base.smooth((times-stop)/recover))
    for i,name in enumerate(body.names):
        if not name.startswith(('upperarm_twist_','lowerarm_twist_')):continue
        if name.endswith('_r'):frames[:,i]=original[:,i];continue
        offset=R.from_quat(body.idle[i,3:7])*R.from_quat(idle[0,i,3:7]).inv()
        correction=R.from_quat(c.slerp([0.,0.,0.,1.],offset.as_quat(),(1.-amount)[:,None]))
        frames[:,i,3:7]=(correction*R.from_quat(frames[:,i,3:7])).as_quat()
    for i,name in enumerate(body.names):
        if name.endswith('_l') and name.startswith(('clavicle_','upperarm_','lowerarm_','hand_')):
            frames[[0,-1],i]=body.idle[i]
    return frames,dict(left_blade_translation_cm=mount_pos.tolist(),left_blade_rotation_xyzw=mount_rot.as_quat().tolist(),left_sweep_face=face)


def export_grip():
    lines=['#pragma once','#include "CoreMinimal.h"','',
        '// Generated by SourceAssets/KukriDualWhirlwind20261026/author.py.',
        '// Accepted DualIdle native left fist; world-space donor, centimetres.',
        'namespace FPSBodyKukriDualGripData','{','struct FBone { FName Name; FTransform Transform; };','inline const FBone Bones[]={']
    def numbers(a):return ','.join(f'{float(v):.12g}' for v in a)
    for name,i in SI.items():
        if not (name=='hand_l' or (name.endswith('_l') and name.startswith(('thumb_','index_','middle_','ring_','pinky_')))):continue
        t=HOLD[i]
        lines.append(f'    {{TEXT("{name}"),FTransform(FQuat({numbers(t[3:7])}),FVector({numbers(t[:3])}),FVector({numbers(t[7:])}))}},')
    lines+=['};',f'inline const FTransform BladeInHand(FQuat({numbers(BLADE_ROT.as_quat())}),FVector({numbers(BLADE_POS)}));','}']
    (ROOT/'Source/FPSGAME/Characters/FPSBodyKukriDualGripData.h').write_text('\n'.join(lines)+'\n')
    (OUT/'native-left-grip.json').write_text(json.dumps({'source':str(DUAL_SOURCE),'bones':{n:HOLD[i].tolist() for n,i in SI.items() if n.endswith('_l')},'blade_position_cm':BLADE_POS.tolist(),'blade_rotation_xyzw':BLADE_ROT.as_quat().tolist()},indent=2))


def main():
    cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    tuning=base.effective_tuning();times,cuts,keys,poses=base.timeline(tuning)
    report={'version':'Dual whirlwind V1','base':'KukriWindmillDetail20261026 V17','tuning':tuning,'runtime_tested':False,'rendered':False,'first_person_changed':False,'bodies':{}}
    for label,data in base.rig.DATA.items():
        active=cfg if label=='jason' else cfg['body_variants'][label]
        if active['body_mesh']!=data['mesh']:raise RuntimeError('Body mesh changed: '+label)
        body=c.Body(data);frames,mount=make(body,label,tuning,times,keys,poses)
        for j in range(1,len(frames)):
            frames[j,:,3:7]*=np.where(np.sum(frames[j-1,:,3:7]*frames[j,:,3:7],axis=1)<0,-1.,1.)[:,None]
        clips={role:dict(rate_num=base.RATE,rate_den=1,frames=frames[start:end].tolist(),contact=0.,release=.999,
            source='Accepted dual-kukri fist plus V17 native-body whirlwind timeline',
            adaptation='Both weapon arms deploy with actor turn; horizontal outboard blades on native palms; native left elbow solve, fixed fingers, progressive lowering and continuous recovery') for role,(start,end) in zip(ROLES,cuts)}
        (OUT/f'{label}-actions.json').write_text(json.dumps({'mesh':data['mesh'],'names':body.names,'parents':body.parents,'clips':clips},separators=(',',':')))
        report['bodies'][label]={'mesh':data['mesh'],'previous_roles':{r:active['clips'].get('Kukri.FullBody.'+r) for r in ROLES},**mount}
        print('DUAL_WHIRLWIND_AUTHORED '+label,flush=True)
    export_grip()
    (OUT/'authoring.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__':main()
