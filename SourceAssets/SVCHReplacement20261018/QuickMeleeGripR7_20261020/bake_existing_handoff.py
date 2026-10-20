"""Bake the existing R6 visible entry/recovery, retaining gun and left-arm motion.

The right support follows the same gun transform as one rigid group. Its new
idle grip and wrist angles remain intact. This allows one authored pose owner
without re-blending local arm chains at runtime. No timeline is changed.
"""
from diagnose_grip import O,R6,s
import json,numpy as np
from scipy.spatial.transform import Rotation as R
prior=json.loads((R6/'native-saved-glove.json').read_text());source=np.load(O/'poses.npz')
root=s.ids['WPN_root'];right=[j for j,n in enumerate(s.names) if n.endswith('_r') and n.startswith(('clavicle','upperarm','lowerarm','hand','thumb','index','middle','ring','pinky'))]
digits=[j for j,n in enumerate(s.names) if n.endswith('_r') and n.startswith(('thumb','index','middle','ring','pinky'))]
out={};locals_={};report={}
for family in prior['families']:
    name=family['family'];order=[family['names'].index(n) for n in s.names];rows={r['frame']:r for r in family['frames']};poses=[];local=[];immutable=0.
    for i,authored in enumerate(source[name]):
        old=s.matrices(np.array(rows[i]['bones'])[order]);p=old.copy()
        group=old[root]@np.linalg.inv(authored[root])
        for j in right:p[j]=group@authored[j]
        for j in digits:p[j]=p[s.parents[j]]@s.relative(old[s.parents[j]],old[j])
        poses.append(p);keys=[]
        for j,par in enumerate(s.parents):
            m=s.relative(p[par],p[j]) if par>=0 else p[j]
            keys.append(np.r_[m[:3,3],R.from_matrix(s.rigid(m)[:3,:3]).as_quat(),np.linalg.norm(m[:3,:3],axis=0)])
        local.append(keys)
        fixed=[j for j in range(len(s.names)) if j not in right];immutable=max(immutable,float(abs(p[fixed]-old[fixed]).max()))
    out[name]=np.array(poses);locals_[name]=np.array(local);report[name]={'non_right_component_difference_from_R6_runtime':immutable}
np.savez_compressed(O/'poses-with-native-blend.npz',**{f:source[f] for f in source.files})
np.savez_compressed(O/'poses.npz',**out);np.savez_compressed(O/'desired-local-120.npz',**locals_)
(O/'handoff-bake.json').write_text(json.dumps({'clock_seconds':.9,'method':'Bake R6 native visible entry/recovery; rigidly carry right contact group with unchanged gun',
    'families':report},indent=2));print('R7_EXISTING_HANDOFF_BAKED',report,flush=True)
