"""Register the RSH grip to the native 715 grasp without rewriting fingers."""
import json,numpy as np
from scipy.spatial import cKDTree
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from pathlib import Path
O=Path(__file__).parent
d=json.loads((O/'single_grip_input.json').read_text())
src=np.array(d['rsh_grip']);dst=np.array(d['donor_grip'])
# Work around the trigger anchor. Match the grip's palm/finger region, not
# the heel or the receiver junction, whose silhouettes differ between guns.
t0=np.array(d['donor_trigger'])-np.array(d['rsh_trigger'])
src=src+t0
src=src[(src[:,2]>-.077)&(src[:,2]<-.008)]
dst=dst[(dst[:,2]>-.077)&(dst[:,2]<-.008)]
src=src[::2];dst=dst[::3];tree=cKDTree(dst)
anchor=np.array(d['donor_trigger'])
def moved(x,p):
    R=Rotation.from_euler('x',x[2]).as_matrix()
    return (p-anchor)@R.T+anchor+np.array([0,x[0],x[1]])
def residual(x):
    p=moved(x,src);dist,idx=tree.query(p)
    # Bounded rigid registration; the trigger anchor prevents the skin-only
    # minimum moving the entire gun out of the original trigger finger.
    return np.r_[(p-dst[idx]).ravel(),x[:2]*5,x[2]*.015]
fit=least_squares(residual,[.006,0,0],bounds=([-.005,-.008,-.14],[.016,.008,.14]),loss='soft_l1',f_scale=.003,max_nfev=160)
R=Rotation.from_euler('x',fit.x[2]).as_matrix()
reg=np.eye(4);reg[:3,:3]=R
# This matrix is post-multiplied by the original trigger registration.
source_anchor=np.array(d['rsh_trigger'])
reg[:3,3]=source_anchor-R@source_anchor+np.array([0,fit.x[0],fit.x[1]])
out=dict(registration=reg.tolist(),translation_m=fit.x[:2].tolist(),pitch_degrees=float(np.degrees(fit.x[2])),
         source='native 715 grip surface and trigger anchor',native_hand_tracks_preserved=True,
         runtime_tested=False)
(O/'grip_registration.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print('NATIVE_GRIP_REGISTRATION_SAVED',out['translation_m'],out['pitch_degrees'])
