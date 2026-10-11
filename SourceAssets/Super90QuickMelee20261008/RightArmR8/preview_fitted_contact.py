"""Inspect the reported poses once their parameter fit is authored."""
from pathlib import Path
O=Path(__file__).parent
ns={}
exec((O/'author_motion.py').read_text(encoding='utf-8').split('result=copy.deepcopy(D)')[0],ns)
source,_=ns['decode']('base')
frames=[27,40,49]
np,j=ns['np'],ns['json']
parameters=np.array(j.loads((O/'fit_parameters_base.json').read_text()))[frames]
ns['blend']=ns['blend'][frames]
selected=[source[f] for f in frames]
gripped,_=ns['hand_motion'](selected,parameters)
poses={}
for i,f in enumerate(frames):
    q=ns['solve_arm'](selected[i],gripped[i],parameters[i,3],ns['blend'][i])
    poses[str(f)]={n:m.tolist() for n,m in q.items()}
(O/'preview_poses.json').write_text(j.dumps(poses))
