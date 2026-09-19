import json,numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation
O=Path(__file__).parent;fit=json.loads((O/'fit_final.json').read_text());out=[]
for k in range(37):
 t=k/36;x=min(1,t*1.5);opening=x*x*(3-2*x);e={'u':t,'basis':{}}
 for n,b in fit['basis'].items():
  if not n.endswith('_l'):continue
  r=Rotation.from_matrix(np.array(b)[:3,:3])
  if not n.startswith('thumb') and any(s in n for s in ['_01_','_02_','_03_']):r=Rotation.from_rotvec(r.as_rotvec()*(1-opening))
  q=r.as_quat();e['basis'][n]=[q[3],q[0],q[1],q[2]]
 out.append(e)
(O/'release_profile.json').write_text(json.dumps(out,indent=2))
