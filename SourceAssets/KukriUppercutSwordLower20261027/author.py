"""Two-handed uppercut lower body with the existing single/dual blade arms.

Read the currently connected native donor poses, align contact/release clocks,
use the donor's forward-stride source between its real foot contacts, and keep
the torso upright without changing hand-relative forearm/finger articulation.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.spatial.transform import Rotation as R

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
spec=importlib.util.spec_from_file_location('upper_native',ROOT/'SourceAssets/KukriDualUppercut20261027/author.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
base,c,dual=previous.base,previous.c,previous.dual
RATE=120


def heading(body,rotations,index):
    delta=R.from_quat(rotations[:,index])*R.from_quat(body.tq[index]).inv()
    direction=delta.apply(np.tile([0.,1.,0.],(len(rotations),1)))
    return np.unwrap(np.arctan2(-direction[:,0],direction[:,1]))


def lower_bones(body):
    result=[]
    for i in range(len(body.names)):
        ancestry=[];j=i
        while j>=0:
            ancestry.append(body.names[j]);j=body.parents[j]
        if 'pelvis' in ancestry and 'spine_01' not in ancestry:result.append(i)
    return result


def build(body,original,sword,stride):
    frames=np.asarray(original['frames'],dtype=float).copy()
    idle=frames[0].copy();body.idle=idle.copy()
    n=len(frames);times=np.arange(n)/RATE;length=times[-1]
    contact=original['contact']*length;release=original['release']*length
    # Keep the existing Kukri release, 120 cm lunge and weapon contact clock.
    clock=PchipInterpolator([0.,.24,contact,release,length],
        [0.,.16,sword['markers']['Contact'],sword['markers']['Release'],sword['duration']])(times)
    donor=np.array([c.sample(np.asarray(sword['frames']),float(t),sword['rate']) for t in clock])
    donor[:,0]=idle[0]
    sf=np.asarray(stride['frames'])
    # Use one real R -> L footfall from the same native source that the
    # two-handed uppercut uses; do not compress its entire multi-step take.
    right=stride['markers']['R'];left=stride['markers']['L']
    if left<=right:left+=stride['duration']
    phase=base.smooth((times-.24)/(.37-.24))
    stride_times=(right+(left-right)*phase)%stride['duration']
    travel=np.array([c.sample(sf,float(t),stride['rate']) for t in stride_times])
    travel[:,0]=idle[0]  # Capsule movement owns translation, not the donor root.
    stride_weight=base.smooth((times-.19)/.05)*(1.-base.smooth((times-.37)/.16))
    ids=lower_bones(body)
    donor[:,ids]=c.blend(donor[:,ids],travel[:,ids],stride_weight[:,None,None])
    dp,dq=body.world(donor);ip,iq=body.world(idle)
    original_p,original_q=body.world(frames)
    enter=base.smooth(times/.17);leave=1.-base.smooth((times-.88)/(length-.88))
    weight=enter*leave
    frames[:,ids]=c.blend(np.repeat(idle[None],n,axis=0)[:,ids],donor[:,ids],weight[:,None,None])

    # Take the donor's compression/rise while centering the hips above its
    # support base. Level the pelvis and distribute axial turn up the spine.
    hip_yaw=heading(body,dq,body.hip)
    hip_yaw=np.radians(8.)*np.tanh(hip_yaw/np.radians(8.))
    chest=body.ix['spine_05']
    chest_yaw=heading(body,original_q,chest)
    chest_yaw=np.radians(18.)*np.tanh(chest_yaw/np.radians(18.))
    source_axis=original_p[:,chest]-original_p[:,body.hip]
    forward_pitch=-np.arctan2(source_axis[:,1],source_axis[:,2])
    forward_pitch=np.radians(4.)*np.tanh(forward_pitch/np.radians(4.))
    centre=.5*(dp[:,body.ix['foot_l'],0]+dp[:,body.ix['foot_r'],0])
    frames[:,body.hip,0]=ip[body.hip,0]+(centre-ip[body.hip,0])*weight
    desired={}
    axial=[('pelvis',0.),('spine_01',.18),('spine_02',.36),('spine_03',.57),
           ('spine_04',.78),('spine_05',1.),('neck_01',.45),('neck_02',.3),('head',.2)]
    for name,amount in axial:
        if name not in body.ix:continue
        index=body.ix[name]
        yaw=hip_yaw+(chest_yaw-hip_yaw)*amount
        pitch=forward_pitch*amount
        rotation=R.from_euler('z',yaw[:,None])*R.from_euler('x',pitch[:,None])*R.from_quat(body.tq[index])
        desired[index]=R.from_quat(c.slerp(iq[index],rotation.as_quat(),weight[:,None]))
        if name!='pelvis':
            frames[:,index,:3]=idle[index,:3]+(body.ref[index,:3]-idle[index,:3])*weight[:,None]
    body.set_world_rotations(frames,desired)

    # Keep both feet on their donor paths while the levelled hips and upright
    # spine change the knee origins. Entry/recovery footfalls are staggered.
    goals,rotations,poles={},{},{}
    for side,arrive,depart in [('l',(.0,.17),(.85,1.06)),('r',(.035,.21),(.98,length))]:
        fi,ki=body.ix['foot_'+side],body.ix['calf_'+side]
        a=base.smooth((times-arrive[0])/(arrive[1]-arrive[0]))
        z=base.smooth((times-depart[0])/(depart[1]-depart[0]))
        w=a*(1.-z)
        goals[side]=ip[fi]+(dp[:,fi]-ip[fi])*w[:,None]
        goals[side][:,2]+=(3.*np.sin(np.pi*a)**2+3.*np.sin(np.pi*z)**2)*(body.scale/94.)
        poles[side]=ip[ki]+(dp[:,ki]-ip[ki])*w[:,None]
        rotations[side]=R.from_quat(c.slerp(iq[fi],dq[:,fi],w[:,None]))
    base.old.steps.fit_legs(body,frames,goals,rotations,poles)
    dual.leg_helpers(body,frames)
    # The source arm chains and all wrist/finger locals stay attached to the
    # corrected chest. They are transported together, not independently bent.
    frames[0]=idle;frames[-1]=np.asarray(original['frames'][-1])
    for k in range(1,n):
        frames[k,:,3:7]*=np.where(np.sum(frames[k-1,:,3:7]*frames[k,:,3:7],axis=1)<0.,-1.,1.)[:,None]
    return frames,dict(source_times=clock.tolist(),stride_times=stride_times.tolist(),
                       stride_weight=stride_weight.tolist(),upright_weight=weight.tolist())


def main():
    cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    sword=json.loads((OUT/'sword-lower-inputs.json').read_text())
    stride=json.loads((OUT/'sword-stride-inputs.json').read_text())
    sources={'Uppercut':'KukriMeshyUppercut20261025','Dual.Uppercut':'KukriDualUppercut20261027'}
    report=dict(version='Sword lower body / upright V1',bodies={},runtime_tested=False,rendered=False,
                first_person_changed=False,gameplay_changed=False)
    for label,data in base.rig.DATA.items():
        active=cfg if label=='jason' else cfg['body_variants'][label]
        if active['body_mesh']!=data['mesh'] or sword[label]['names']!=data['names']:
            raise RuntimeError('Native body input changed: '+label)
        if active['clips']['Melee.FullBody.Uppercut']!=sword[label]['asset'] or active['clips']['Unarmed.Jog.Fwd']!=stride[label]['asset']:
            raise RuntimeError('Active donor changed: '+label)
        clips={};record=dict(mesh=data['mesh'],previous_roles={},source_sword=sword[label]['asset'],
                            source_stride=stride[label]['asset'],clock={})
        for role,directory in sources.items():
            folder=ROOT/'SourceAssets'/directory
            raw=(folder/(label+'-actions.json')).read_bytes()
            saved=json.loads((folder/'assets-saved.json').read_text())['bodies'][label]
            key='Kukri.FullBody.'+role
            if hashlib.sha256(raw).hexdigest()!=saved['source_sha256'] or active['clips'][key]!=saved['clips'][key]:
                raise RuntimeError('Current authored arm source changed: '+label+' '+role)
            source=json.loads(raw)
            if source['names']!=data['names']:raise RuntimeError('Native track order mismatch')
            original=source['clips'][role]
            rate=original.get('rate_num',original.get('rate'))/original.get('rate_den',1)
            if rate!=RATE:raise RuntimeError('Unexpected uppercut clock')
            frames,clock=build(c.Body(data),original,sword[label],stride[label])
            clips[role]=dict(rate_num=RATE,rate_den=1,frames=frames.tolist(),contact=original['contact'],release=original['release'],
                source='Current native two-handed sword uppercut and its forward stride; existing Kukri arm chains',
                adaptation='Contact-aligned sword lower body, one R-to-L stride, level pelvis, upright spine, original native wrist/finger grip')
            record['previous_roles'][role]=active['clips'][key];record['clock'][role]=clock
            print('UPRIGHT_UPPERCUT_AUTHORED',label,role,len(frames),flush=True)
        (OUT/(label+'-actions.json')).write_text(json.dumps(dict(mesh=data['mesh'],names=data['names'],parents=data['parents'],clips=clips),separators=(',',':')))
        report['bodies'][label]=record
    (OUT/'authoring.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__':main()
