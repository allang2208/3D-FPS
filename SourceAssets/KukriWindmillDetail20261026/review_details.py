"""Scoped comparison for the user-requested wrist and free-hand review."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
import author as a
OUT=Path(__file__).resolve().parent
baseline=OUT.parent/'KukriWindmillGrip20261026'
times=a.timeline(a.effective_tuning())[0]
report={'source':'Native authored V16 versus V17 tracks','runtime_tested':False,'bodies':{}}
def frames(path):
    clips=json.loads(path.read_text())['clips']
    return np.concatenate([np.asarray(clips[r]['frames'])[:-1] for r in a.ROLES[:-1]]+[np.asarray(clips[a.ROLES[-1]]['frames'])])
def angles(q1,q2):
    shape=q1.shape[:-1]
    return np.degrees((R.from_quat(q1.reshape(-1,4))*R.from_quat(q2.reshape(-1,4)).inv()).magnitude()).reshape(shape)
for label,data in a.rig.DATA.items():
    body=a.c.Body(data);before=frames(baseline/(label+'-actions.json'));after=frames(OUT/(label+'-actions.json'))
    bp,bq=body.world(before);ap,aq=body.world(after)
    fingers=[i for i,n in enumerate(body.names) if n.endswith('_r') and n.startswith(('thumb_','index_','middle_','ring_','pinky_'))]
    core=[body.ix[n] for n in ('pelvis','spine_01','spine_02','spine_03','thigh_l','calf_l','foot_l','thigh_r','calf_r','foot_r')]
    left=[body.ix[n+'_l'] for n in ('clavicle','upperarm','lowerarm','hand')]
    wrist=body.ix['hand_r'];ref=R.from_quat(body.ref[wrist,3:7]);axis=a.c.unit(body.ref[wrist,:3])
    def wrist_bend(f):
        d=R.from_quat(f[:,wrist,3:7])*ref.inv()
        return np.degrees(np.arccos(np.clip(d.apply(np.tile(axis,(len(f),1)))@axis,-1.,1.)))
    spin=(times>=.65)&(times<=sum(a.effective_tuning()[k] for k in ('readySeconds','spinSeconds'))+1e-8)
    def speed(f):
        peak=angles(f[1:,wrist,3:7],f[:-1,wrist,3:7])/np.diff(times)
        return float(peak.max())
    report['bodies'][label]={
        'right_spin_wrist_bend_before_deg':[float(wrist_bend(before)[spin].min()),float(wrist_bend(before)[spin].max())],
        'right_spin_wrist_bend_after_deg':[float(wrist_bend(after)[spin].min()),float(wrist_bend(after)[spin].max())],
        'right_local_wrist_peak_speed_deg_s_before_after':[speed(before),speed(after)],
        'right_finger_local_rotation_change_deg':float(angles(before[:,fingers,3:7],after[:,fingers,3:7]).max()),
        'approved_core_local_rotation_change_deg':float(angles(before[:,core,3:7],after[:,core,3:7]).max()),
        'approved_core_translation_change_cm':float(np.abs(before[:,core,:3]-after[:,core,:3]).max()),
        'left_chain_local_rotation_change_deg':float(angles(before[:,left,3:7],after[:,left,3:7]).max()),
        'left_wrist_position_change_cm':float(np.linalg.norm(bp[:,body.ix['hand_l']]-ap[:,body.ix['hand_l']],axis=1).max()),
        'right_wrist_position_adjustment_cm':float(np.linalg.norm(bp[spin,wrist]-ap[spin,wrist],axis=1).max()),
        'bone_scale_change':float(np.abs(before[:,:,7:]-after[:,:,7:]).max()),
        'first_last_pose_rotation_change_deg':float(angles(before[[0,-1],:,3:7],after[[0,-1],:,3:7]).max())}
(OUT/'detail-comparison.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
