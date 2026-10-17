"""Read the published hammer carry and inspect the previous cast's elbow plane.

This is source-pose diagnosis, not an in-game capture or visual acceptance.
"""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

root = Path(__file__).resolve().parents[2]
out = root/'SourceAssets/WarhammerCastArm20261017/DirectionV2'
out.mkdir(parents=True, exist_ok=True)
mesh = json.loads((root/'SourceAssets/JasonPlayer20261003/Jason.json').read_text())
data = json.loads((root/'SourceAssets/WarhammerThirdPersonSevarog20261016/SourceGripV16/adapted-actions.json').read_text())
names = data['names']
ix = {n:i for i,n in enumerate(names)}
refs = {b['name']:b for b in mesh['bones']}
parents = [ix[mesh['bones'][refs[n]['parent']]['name']] if refs[n]['parent'] >= 0 else -1 for n in names]
samples = []
for label, clip in data['clips'].items():
    frame = np.array(clip['frames'][0])
    world = frame.copy()
    for i, parent in enumerate(parents):
        if parent < 0:
            continue
        q = R.from_quat(world[parent,3:7])
        world[i,:3] = world[parent,:3] + q.apply(frame[i,:3])
        world[i,3:7] = (q*R.from_quat(frame[i,3:7])).as_quat()
    chest = R.from_quat(world[ix['spine_05'],3:7])*R.from_matrix(np.array(refs['spine_05']['axes']).T).inv()
    shoulder, elbow, hand = [world[ix[n],:3] for n in ('upperarm_l','lowerarm_l','hand_l')]
    l1,l2 = np.linalg.norm(elbow-shoulder),np.linalg.norm(hand-elbow)
    row = {'clip':label, 'shoulder':shoulder.tolist(), 'anatomical_axes':chest.as_matrix().tolist(), 'old_targets':[]}
    # Native CastHand fallback is exact. Camera gather is a representative
    # level-view mapping of the configured (33,-24,-26) camera-centimetre goal.
    for target_label,target in [('native_fallback',np.array([32.,40.,136.])),('level_view_example',np.array([24.,33.,134.]))]:
        v = target-shoulder
        axis = v/np.linalg.norm(v)
        distance = np.clip(np.linalg.norm(v),abs(l1-l2)+.05,(l1+l2)*.955)
        along = (l1*l1-l2*l2+distance*distance)/(2*distance)
        radius = np.sqrt(max(0,l1*l1-along*along))
        bend = np.array([40.,8.,-32.])
        bend -= axis*np.dot(axis,bend)
        bend /= np.linalg.norm(bend)
        solved_elbow = shoulder+axis*along+bend*radius
        row['old_targets'].append({'target':target_label, 'wrist_shoulder_anatomical':chest.inv().apply(target-shoulder).tolist(),
                                   'elbow_shoulder_anatomical':chest.inv().apply(solved_elbow-shoulder).tolist()})
    samples.append(row)
report = {'kind':'published_source_pose_diagnosis', 'axis_order':['left','front','up'], 'samples':samples}
(out/'source-basis-diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
for row in samples:
    print(row['clip'], [(r['target'],round(r['wrist_shoulder_anatomical'][1],2),round(r['elbow_shoulder_anatomical'][1],2)) for r in row['old_targets']])
