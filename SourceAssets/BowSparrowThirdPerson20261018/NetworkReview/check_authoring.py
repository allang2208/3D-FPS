"""Offline checks of the saved authoring inputs; no rendering or UE launch."""
import sys,json,re
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bow_math import read,fk,R,compose,inverse,rot

task=Path(__file__).resolve().parents[1]
root=task.parents[1]
data=read('retargeted.json.gz');a=read('authored.json.gz');ix={n:i for i,n in enumerate(data['names'])}
ref=np.asarray(data['reference']);rows=[]
for role,clip in a['clips'].items():
    frames=np.asarray(clip['frames']);bones=[ix[n+'_'+s] for s in ('l','r') for n in ('lowerarm','hand')]
    lengths=np.linalg.norm(frames[:,bones,:3],axis=-1);base=np.linalg.norm(ref[bones,:3],axis=-1)
    delta=np.max(np.abs(lengths-base))
    norms=np.linalg.norm(frames[:,:,3:7],axis=-1)
    fingers=[i for n,i in ix.items() if n.startswith(('thumb_','index_','middle_','ring_','pinky_')) and '_half_' not in n]
    q=frames[:,fingers,3:7];dots=np.clip(np.abs(np.sum(q[1:]*q[:-1],axis=-1)),0,1)
    step=float(np.degrees(2*np.arccos(dots)).max()) if len(frames)>1 else 0.
    arms=[ix[n+'_'+s] for s in ('l','r') for n in ('upperarm','lowerarm','hand')]
    aq=frames[:,arms,3:7];arm_angle=np.degrees(2*np.arccos(np.clip(np.abs(np.sum(aq[1:]*aq[:-1],axis=-1)),0,1)))
    arm_step=float(arm_angle.max()) if len(frames)>1 else 0.
    rows.append(dict(clip=role,finite=bool(np.isfinite(frames).all()),arm_length_error_cm=float(delta),
        quaternion_norm_error=float(np.max(np.abs(norms-1))),max_adjacent_finger_rotation_degrees=step,
        max_adjacent_arm_rotation_degrees=arm_step,frames=len(frames)))

published=json.loads((task/'published.json').read_text(encoding='utf-8-sig'))['clips']
config=json.loads((root/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))['clips']
ini=(root/'Config/DefaultGame.ini').read_text(encoding='utf-8-sig')
directories=re.findall(r'^\+DirectoriesToAlwaysCook=\(Path="([^"]+)"\)',ini,re.M)
assets=[]
for key,path in published.items():
    package=path.split('.')[0]
    assets.append(dict(key=key,configured=config.get(key)==path,exists=(root/'Content'/(package.removeprefix('/Game/')+'.uasset')).exists(),
        explicit_cook_coverage=any(package.startswith(d.rstrip('/')+'/') for d in directories)))
last=np.asarray(a['clips']['Release']['frames'][-1]);carry=np.asarray(a['clips']['Carry']['frames'][0])
join_angle=float(np.degrees(2*np.arccos(np.clip(np.abs(np.sum(last[:,3:7]*carry[:,3:7],axis=-1)),0,1))).max())
result=dict(clips=rows,assets=assets,release_to_carry_joint_error_degrees=join_angle,scope='Authoring coordinates and packaging configuration, not runtime skin or visual acceptance.')
result['passed']=join_angle<.01 and all(r['finite'] and r['arm_length_error_cm']<.02 and r['quaternion_norm_error']<.001 and r['max_adjacent_finger_rotation_degrees']<30 and r['max_adjacent_arm_rotation_degrees']<60 for r in rows) and all(all(r[k] for k in ('configured','exists','explicit_cook_coverage')) for r in assets)
(task/'NetworkReview/authoring-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
sys.exit(0 if result['passed'] else 1)
