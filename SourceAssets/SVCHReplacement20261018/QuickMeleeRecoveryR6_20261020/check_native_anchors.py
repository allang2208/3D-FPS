"""Saved real Gunplay integer keys must retain the entire R5 pose."""
from diagnose_recovery import O,R5,s
from scipy.spatial.transform import Rotation as R
import json,numpy as np
a=json.loads((R5/'native-saved-glove.json').read_text());b=json.loads((O/'native-saved-glove.json').read_text());rows=[]
for old,new in zip(a['families'],b['families']):
    assert old['names']==new['names'];position=0.;angle=0.;scale=0.;matrix=0.
    for x,y in zip(old['frames'],new['frames']):
        assert x['frame']==y['frame'];p=s.matrices(x['bones']);q=s.matrices(y['bones'])
        position=max(position,float(np.linalg.norm(p[:,:3,3]-q[:,:3,3],axis=1).max()))
        angle=max(angle,float(np.degrees((R.from_matrix(s.rigid(p)[:,:3,:3])*R.from_matrix(s.rigid(q)[:,:3,:3]).inv()).magnitude()).max()))
        scale=max(scale,float(abs(np.linalg.norm(p[:,:3,:3],axis=1)-np.linalg.norm(q[:,:3,:3],axis=1)).max()))
        matrix=max(matrix,float(abs(p-q).max()))
    rows.append({'family':new['family'],'samples':len(new['frames']),'max_bone_position_difference_cm':position,
        'max_bone_rotation_difference_degrees':angle,'max_scale_difference':scale,'max_matrix_difference':matrix})
passed=all(r['max_bone_position_difference_cm']<.003 and r['max_bone_rotation_difference_degrees']<.002 for r in rows)
(O/'native-anchor-preservation.json').write_text(json.dumps({'passed':passed,'rows':rows},indent=2));print(json.dumps({'passed':passed,'rows':rows}),flush=True)
if not passed:raise SystemExit(1)
