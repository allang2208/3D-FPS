import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
O=Path(__file__).parent
d=json.loads((O/'geometry.json').read_text()); rest={n:np.array(m) for n,m in d['rest'].items()};ri={n:np.linalg.inv(m) for n,m in rest.items()}
source=json.loads((O/'source_poses.json').read_text())
mesh=d['meshes']['Super90_V7_M4_BareArmsV6'];v=np.array(mesh['positions']);weights=mesh['weights']
groups={}
for n in rest:
    ids=np.array([i for i,w in enumerate(weights) if w.get(n,0)>1e-5])
    if len(ids):groups[n]=(ids,np.array([weights[i][n] for i in ids]))
fore=np.array([i for i,w in enumerate(weights) if sum(a for n,a in w.items() if n.startswith('lowerarm') and n.endswith('_l'))>.5])
def angle(a,b):return float(np.rad2deg(R.from_matrix(a[:3,:3]@b[:3,:3].T).magnitude()))
rows=[]
for branch,frames in [('normal',[0,85,92,100,110,118,126,136,144]),('empty',[138,145,150,153,156,160,165,174]),('cycle',[25,32,38,45])]:
    for f in frames:
        p={n:np.array(m) for n,m in source[branch][f].items()};skin={n:p[n]@ri[n] for n in rest};blended=np.zeros((len(v),3,3))
        for n,(ids,w) in groups.items():blended[ids]+=skin[n][:3,:3]*w[:,None,None]
        sv=np.linalg.svd(blended[fore],compute_uv=False)
        arm=['upperarm_l','lowerarm_l','lowerarm_aux_l','lowerarm_twist_02_l','lowerarm_twist_01_l','hand_l']
        row=dict(branch=branch,frame=f,fore_min_singular=np.percentile(sv[:,-1],[0,5,50]).tolist(),
            rotation_from_main={n:round(angle(skin[n],skin['lowerarm_l']),2) for n in arm},
            joints={n:p[n][:3,3].tolist() for n in ('upperarm_l','lowerarm_l','hand_l')})
        rows.append(row);print(branch,f,'compression',np.round(row['fore_min_singular'],3),'angles',row['rotation_from_main'])
(O/'diagnosis.json').write_text(json.dumps(rows,indent=2))
