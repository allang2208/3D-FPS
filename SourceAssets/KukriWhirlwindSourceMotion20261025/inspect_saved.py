"""Focused checks requested for the whirlwind arm and phase continuity."""
import json
import numpy as np
from scipy.spatial.transform import Rotation as R
import author as a
saved=json.loads((a.OUT/'saved-compressed.json').read_text())
report=dict(scope='Six third-person native whirlwind packages, source/decoded motion and phase joins',runtime_tested=False,bodies={})
for label,clips in saved.items():
    body=a.c.Body(a.DATA[label]);actions=json.loads((a.OUT/(label+'-actions.json')).read_text())['clips'];result={'clips':{}}
    decoded={}
    for role,clip in clips.items():
        f=np.asarray(actions[role]['frames']);p,q=body.world(f);w=np.asarray(clip['world']);ids=[body.ix[n] for n in clip['bones']]
        if len(f)!=len(w):raise RuntimeError('Saved key count changed '+label+' '+role)
        decoded[role]=w
        difference=np.linalg.norm(w[:,:,:3]-p[:,ids],axis=2)
        angular=np.degrees((R.from_quat(w[:,:,3:7].reshape(-1,4))*R.from_quat(q[:,ids].reshape(-1,4)).inv()).magnitude()).reshape(len(w),-1)
        errors=dict(position_cm=float(difference.max()),rotation_degrees=float(angular.max()))
        if errors['position_cm']>.1 or errors['rotation_degrees']>.25:raise RuntimeError('Decoded native motion differs '+str(errors))
        if not np.isfinite(w).all():raise RuntimeError('Non-finite saved transform')
        result['clips'][role]=dict(asset=clip['asset'],seconds=clip['duration'],source_decode_max_error=errors)
    joins=[]
    for left,right in [('Whirlwind.Start','Whirlwind.Loop'),('Whirlwind.Loop','Whirlwind.End')]:
        end,start=decoded[left][-1],decoded[right][0]
        distance=float(np.linalg.norm(end[:,:3]-start[:,:3],axis=1).max())
        angle=float(np.degrees((R.from_quat(end[:,3:7])*R.from_quat(start[:,3:7]).inv()).magnitude()).max())
        joins.append(dict(left=left,right=right,max_position_error_cm=distance,max_rotation_error_degrees=angle))
        # Independent sequence compression may vary a helper by a fraction of
        # a degree even when the authored boundary keys are exactly identical.
        if distance>.02 or angle>.25:raise RuntimeError('Phase join changed beyond compression tolerance')
    loop=decoded['Whirlwind.Loop'];bones=clips['Whirlwind.Loop']['bones'];ix={n:i for i,n in enumerate(bones)}
    torso=R.from_quat(loop[:,ix['spine_03'],3:7])*R.from_quat(body.tq[body.ix['spine_03']]).inv()
    mid=(loop[:,ix['upperarm_l'],:3]+loop[:,ix['upperarm_r'],:3])*.5
    hand=torso.inv().apply(loop[:,ix['hand_l'],:3]-mid)
    result['decoded_left_hand_chest_range_cm']=np.ptp(hand,axis=0).tolist()
    result['phase_joins']=joins
    result['loop_closure_position_error_cm']=float(np.linalg.norm(loop[-1,:,:3]-loop[0,:,:3],axis=1).max())
    report['bodies'][label]=result
report['complete']=True
(a.OUT/'inspection.json').write_text(json.dumps(report,indent=2))
print('WHIRLWIND_NATIVE_INSPECTION_COMPLETE')
