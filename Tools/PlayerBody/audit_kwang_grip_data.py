"""Offline contact/continuity probe for the 20261007 grip authoring output."""
import json
import argparse
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/ThirdPersonSwordGrip20261007'
parser=argparse.ArgumentParser()
parser.add_argument('--input',default='adapted-actions.json')
parser.add_argument('--output',default='grip-data-audit.json')
parser.add_argument('--require-fixed',action='store_true')
args=parser.parse_args()
recipe=OUT/'refine_kwang_grip.py'
# Only load the recipe's geometry helpers; do not execute its asset generation.
ctx={'__file__':str(recipe)}
exec(compile(recipe.read_text().split('\nclips={}')[0],str(recipe),'exec'),ctx)
fk,compose,inverse,axis,grips,ix,ref=(ctx[k] for k in ('fk','compose','inverse','axis','grips','ix','ref'))
data=json.loads((OUT/args.input).read_text())
original=json.loads((OUT.parent/'ThirdPersonSwordKwang20261006/adapted-actions.json').read_text())
results={}
for label,c in data['clips'].items():
    f=np.array(c['frames']);w=np.array([fk(p) for p in f]);old=np.array(original['clips'][label]['frames'])
    # Compare shared original sample times when contact is baked more densely.
    stride=(len(f)-1)//(len(old)-1);shared=f[::stride]
    rolls=np.array(c['curves']['SwordGripRoll'])
    contact=[]
    for i,p in enumerate(w):
        weapon=compose(compose(p[ix['hand_r'],:7],inverse(grips['r'])),np.r_[0.,0.,0.,axis([0,0,1],-np.radians(rolls[i]))])
        left=compose(compose(inverse(weapon),p[ix['hand_l'],:7]),inverse(grips['l']))
        contact.append(np.linalg.norm(left[:3]))
    arms={}
    for side in ('r','l'):
        a,b,h=[ix[k+'_'+side] for k in ('upperarm','lowerarm','hand')]
        along=w[:,h,:3]-w[:,b,:3];along/=np.linalg.norm(along,axis=1)[:,None]
        desired=R.from_quat(w[:,h,3:7]).apply(R.from_quat(ref[h,3:7]).inv().apply(ref[h,:3]/np.linalg.norm(ref[h,:3])))
        swing=np.degrees(np.arccos(np.clip(np.sum(along*desired,axis=1),-1,1)))
        jumps=R.from_quat(f[1:,b,3:7])*R.from_quat(f[:-1,b,3:7]).inv()
        helpers=[ix[k+side] for k in ('lowerarm_twist_01_','lowerarm_twist_02_','upperarm_twist_01_','upperarm_twist_02_')]
        helper_steps=[float(np.degrees((R.from_quat(f[1:,j,3:7])*R.from_quat(f[:-1,j,3:7]).inv()).magnitude()).max()) for j in helpers]
        arms[side]={'max_wrist_swing_deg':float(max(swing)),'p95_wrist_swing_deg':float(np.percentile(swing,95)),
                    'max_lowerarm_step_deg':float(np.degrees(jumps.magnitude()).max()),
                    'max_twist_helper_step_deg':max(helper_steps),
                    'max_elbow_step_cm':float(np.linalg.norm(np.diff(w[:,b,:3],axis=0),axis=1).max())}
    core=[i for i,n in enumerate(data['names']) if not any(k in n for k in ('upperarm','lowerarm','hand_'))]
    results[label]={'frames':len(f),'finite':bool(np.isfinite(f).all()),
        'quat_norm_error':float(np.max(np.abs(np.linalg.norm(f[:,:,3:7],axis=2)-1))),
        'unchanged_translation_scale':bool(np.allclose(shared[:,:,:3],old[:,:,:3],atol=1e-7) and np.allclose(shared[:,:,7:],old[:,:,7:],atol=1e-7)),
        'body_unchanged':bool(np.allclose(shared[:,core],old[:,core],atol=1e-7)),
        'max_pair_contact_cm':float(max(contact)),
        'roll_range_deg':[float(min(rolls)),float(max(rolls))],
        'roll_max_step_deg':float(np.abs(np.diff(rolls)).max()),'arms':arms}
joins={}
for a,b in [('Whirlwind.Start','Whirlwind.Loop'),('Whirlwind.Loop','Whirlwind.End')]:
    x,y=data['clips'][a],data['clips'][b]
    joins[a+'->'+b]={'pose_identical':x['frames'][-1]==y['frames'][0],
                    'curve_difference':x['curves']['SwordGripRoll'][-1]-y['curves']['SwordGripRoll'][0]}
endpoints={}
for label,end in [('Uppercut','Uppercut'),('Overhead','Overhead'),('Whirlwind.Start','Whirlwind.End')]:
    start=np.array(data['clips'][label]['frames'][0]);last=np.array(data['clips'][end]['frames'][-1])
    degrees=np.degrees((R.from_quat(start[:,3:7])*R.from_quat(last[:,3:7]).inv()).magnitude())
    endpoints[label]={'max_rotation_difference_deg':float(max(degrees)),
                      'bones_over_one_degree':[data['names'][i] for i,x in enumerate(degrees) if x>1.]}
report={'clips':results,'joins':joins,'endpoints':endpoints}
(OUT/args.output).write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
if args.require_fixed:
    for label,c in results.items():
        assert c['finite'] and c['quat_norm_error']<1e-5,label+' invalid transform'
        assert c['unchanged_translation_scale'] and c['body_unchanged'],label+' changed body/bone length'
        assert c['max_pair_contact_cm']<.001,label+' separated hands'
        assert c['roll_max_step_deg']<25,label+' grip roll jump'
    assert all(j['pose_identical'] and abs(j['curve_difference'])<1e-6 for j in joins.values()),'whirlwind seam'
    assert all(e['max_rotation_difference_deg']<.001 for e in endpoints.values()),'ready pose did not close'
    print('KWANG_GRIP_DATA_CHECKS_PASSED')
