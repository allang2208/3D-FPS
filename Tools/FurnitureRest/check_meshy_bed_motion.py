"""Measure continuity in the fitted native bed clip, including the entry join."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'SourceAssets/FurnitureRest20261022/MeshyBed20261024'
ns={'__file__':str(ROOT/'Tools/FurnitureRest/refine.py')}
exec((ROOT/'Tools/FurnitureRest/refine.py').read_text().split('specs=')[0],ns)
data=json.loads((OUT/'authored.json').read_text());f=np.array(data['clips']['Rest.Bed.Enter']['frames']);world=np.array([ns['fk'](p) for p in f]);report={}
for name in ('pelvis','spine_03','head','upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r','thigh_l','calf_l','foot_l','thigh_r','calf_r','foot_r'):
    i=ns['ix'][name];q=R.from_quat(f[:,i,3:7]);turn=np.degrees((q[1:]*q[:-1].inv()).magnitude());move=np.linalg.norm(np.diff(world[:,i,:3,3],axis=0),axis=1)
    report[name]={'max_local_step_degrees':float(turn.max()),'rotation_time':float((turn.argmax()+1)/30),
                  'max_world_step_cm':float(move.max()),'position_time':float((move.argmax()+1)/30)}
(OUT/'motion_review.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
