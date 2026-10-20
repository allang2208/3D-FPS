"""Lower the rigid grasp along the magazine spine to clear the seated receiver."""
import json
from pathlib import Path
import numpy as np
O=Path(__file__).parent;R9=O.parent/'R9ReloadGrip'
env={'__file__':str(R9/'author_reload_grip.py')}
exec(compile((R9/'author_reload_grip.py').read_text().split("report={'method'")[0],str(R9/'author_reload_grip.py'),'exec'),env)
globals().update({k:v for k,v in env.items() if k not in ('O','__file__','__builtins__')})
poses={f:comp(matrices(motion['clips']['reload']['frames'][f])) for f in (170,220,240)}
root_positions=[(np.linalg.inv(rigid(poses[f][ROOT]))@rigid(poses[f][MAG]))[:3,3] for f in (170,240)]
up=np.linalg.inv(rigid(poses[220][MAG]))[:3,:3]@rigid(poses[220][ROOT])[:3,:3]@(root_positions[1]-root_positions[0])
axis=Shell(mag['svch'][0],up).axis
path=O/'contact_refinement.json';report=json.loads(path.read_text())
delta=np.asarray(report['delta_magazine_local']);shift=-axis*2.3
delta[:3,3]+=shift-np.asarray(report.get('receiver_clearance_shift_magazine_cm',[0.,0.,0.]))
report['delta_magazine_local']=delta.tolist();report['receiver_clearance_shift_magazine_cm']=shift.tolist()
report['receiver_grip_height_lowering_cm']=2.3
path.write_text(json.dumps(report,indent=2));print('RECEIVER_CLEARANCE_SHIFT',shift.tolist(),flush=True)
