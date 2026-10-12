"""Quantify the requested V2/V3 arm regression at corresponding source samples."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

root = Path('D:/FPS3D/FPSGAME/SourceAssets')
out = root/'ThirdPersonMeleeRegression20261010'
rig = json.loads((root/'ThirdPersonSwordKwang20261006/retargeted-poses.json').read_text())
accepted = json.loads((root/'ThirdPersonSwordKwang20261006/adapted-actions.json').read_text())
v3 = json.loads((root/'ThirdPersonSwordGrip20261007/adapted-actions.json').read_text())
recovery = json.loads((out/'adapted-actions.json').read_text())
names, parents = rig['names'], rig['parents']
index = {n:i for i,n in enumerate(names)}

def worlds(frames):
    m = np.zeros((*frames.shape[:2], 4, 4)); m[:,:,3,3] = 1
    m[:,:,:3,:3] = R.from_quat(frames[:,:,3:7].reshape(-1,4)).as_matrix().reshape(*frames.shape[:2],3,3)*frames[:,:,None,7:10]
    m[:,:,:3,3] = frames[:,:,:3]
    for i,p in enumerate(parents):
        if p >= 0: m[:,i] = m[:,p] @ m[:,i]
    return m

report = {'comparison': 'Corresponding source samples; not a gameplay test', 'clips': {}}
for name,clip in accepted['clips'].items():
    a = np.asarray(clip['frames']); b = np.asarray(v3['clips'][name]['frames'])[::2]
    restored = np.asarray(recovery['clips'][name]['frames'])
    wa,wb = worlds(a),worlds(b)
    row = {'arms': {}, 'restored_max_component_error': float(np.max(np.abs(a-restored))),
           'rate': recovery['clips'][name]['rate']}
    for side in ('r','l'):
        e = index['lowerarm_'+side]
        distance = np.linalg.norm(wa[:,e,:3,3]-wb[:,e,:3,3],axis=1)
        ids = [index[p+side] for p in ('upperarm_','lowerarm_','hand_','upperarm_twist_01_','upperarm_twist_02_','lowerarm_twist_01_','lowerarm_twist_02_')]
        rotation = np.degrees(2*np.arccos(np.clip(np.abs(np.sum(a[:,ids,3:7]*b[:,ids,3:7],axis=2)),0,1)))
        row['arms'][side] = {'v3_max_elbow_displacement_cm': float(distance.max()),
                            'v3_max_local_rotation_change_degrees': float(rotation.max())}
    body = [i for i,n in enumerate(names) if n in ('root','pelvis') or n.startswith(('spine_','thigh_','calf_','foot_'))]
    row['v3_body_max_component_error'] = float(np.max(np.abs(a[:,body]-b[:,body])))
    report['clips'][name] = row
(out/'source-regression-measurements.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
