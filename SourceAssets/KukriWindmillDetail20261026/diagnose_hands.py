"""Focused blade direction and recovery-chain measurements requested by user."""
import json,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
import author as a

OUT=Path(__file__).resolve().parent
compressed='--compressed' in sys.argv
saved=json.loads((OUT/'preview-compressed.json').read_text()) if compressed else None
report={'source':'UE compressed V17 assets' if compressed else 'V17 authored tracks','bodies':{}}
for label,data in a.rig.DATA.items():
    body=a.c.Body(data)
    authored=json.loads((OUT/(label+'-actions.json')).read_text())
    clips={}
    for role,clip in authored['clips'].items():
        if compressed:
            world=np.asarray(saved[label]['clips'][role]['world'])
            p,q=world[:,:,:3],world[:,:,3:7]
            f=world.copy()
            for i,par in enumerate(body.parents):
                if par>=0:f[:,i,3:7]=(R.from_quat(q[:,par]).inv()*R.from_quat(q[:,i])).as_quat()
        else:
            f=np.asarray(clip['frames']);p,q=body.world(f)
        clips[role]=(f,p,q)
    f,p,q=clips['Whirlwind.Loop']
    u,e,h=[body.ix[n+'_r'] for n in ('upperarm','lowerarm','hand')]
    _,mount=a.native.blade_mount(body)
    tip=a.c.unit(np.asarray(json.loads((a.ROOT/'SourceAssets/Kukri20261020/model.json').read_text())['tip_cm']))
    axis=(R.from_quat(q[:,h])*mount).apply(np.tile(tip,(len(f),1)))
    full=a.old.arms.phase(np.linspace(0.,1.,len(f)))*720.>=110.
    tilt=np.degrees(np.arcsin(np.clip(axis[full,2],-1.,1.)))
    wrist=np.degrees((R.from_quat(f[full,h,3:7])*R.from_quat(body.ref[h,3:7]).inv()).magnitude())
    local=R.from_quat(f[full,e,3:7]);ref=R.from_quat(body.ref[e,3:7]);fore_axis=a.c.unit(body.ref[h,:3])
    swing=a.c.align(np.tile(ref.apply(fore_axis),(sum(full),1)),local.apply(np.tile(fore_axis,(sum(full),1))))
    elbow=np.degrees((ref.inv()*swing.inv()*local).magnitude())
    end,ep,eq=clips['Whirlwind.End']
    chain=('clavicle_l','upperarm_l','lowerarm_l','hand_l','upperarm_twist_01_l','lowerarm_twist_01_l')
    changes={n:float(np.degrees((R.from_quat(end[1:,body.ix[n],3:7])*R.from_quat(end[:-1,body.ix[n],3:7]).inv()).magnitude()).max()) for n in chain}
    allq=np.concatenate([clips[role][0][:-1,:,3:7] for role in a.ROLES[:-1]]+[end[:,:,3:7]])
    right_steps={n:float(np.degrees((R.from_quat(allq[1:,body.ix[n]])*R.from_quat(allq[:-1,body.ix[n]]).inv()).magnitude()).max()) for n in ('upperarm_r','lowerarm_r','hand_r')}
    report['bodies'][label]=dict(blade_tilt_deg=[float(tilt.min()),float(tilt.max())],
        wrist_from_bind_deg=[float(wrist.min()),float(wrist.max())],elbow_axial_max_deg=float(elbow.max()),
        recovery_samples=len(end),recovery_left_max_sample_step_deg=changes,right_max_sample_step_deg=right_steps)
    print(label,json.dumps(report['bodies'][label]),flush=True)
(OUT/('hands-compressed.json' if compressed else 'pose-diagnosis.json')).write_text(json.dumps(report,indent=2))
