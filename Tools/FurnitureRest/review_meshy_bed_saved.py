"""Check native compressed stage joins and retain the limited offline receipt."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

OUT=Path(__file__).resolve().parents[2]/'SourceAssets/FurnitureRest20261022'/globals().get('FURNITURE_REVISION','MeshyBed20261024')
data=json.loads((OUT/'native_saved_samples.json').read_text())
report={}
def error(a,b):
    a,b=np.asarray(a),np.asarray(b)
    return {'position_cm':float(np.linalg.norm(a[...,:3]-b[...,:3],axis=-1).max()),
            'rotation_degrees':float(np.degrees((R.from_quat(a[...,3:7].reshape(-1,4))*R.from_quat(b[...,3:7].reshape(-1,4)).inv()).magnitude()).max())}
for variant,spec in data.items():
    clips={role.split('.')[-1]:np.asarray(take['world']) for role,take in spec['clips'].items()}
    enter,idle,leave=(clips[k] for k in ('Enter','Idle','Exit'))
    joins={'enter_idle':error(enter[-1],idle[0]),'idle_exit':error(idle[-1],leave[0]),
           'idle_loop':error(idle[0],idle[-1]),'exit_stand':error(leave[-1],enter[0])}
    report[variant]={'mesh':spec['mesh'],'stage_joins':joins,
                     'exit_reverse':error(enter[::-1],leave[:len(enter)])}
    if any(v['position_cm']>.05 or v['rotation_degrees']>.25 for v in joins.values()):
        raise RuntimeError('Compressed stage seam: '+variant)
(OUT/'native_stage_review.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
