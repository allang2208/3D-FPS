"""Inspect authoring poses before saving; these are not native runtime samples."""
import json,numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation as R
p=Path(__file__).resolve().parent;d=json.loads((p/'Before/frames-120.json').read_text(encoding='utf-8-sig'));poses=json.loads((p/'authored-poses.json').read_text());out=[];C=np.diag([1,-1,1])
for i,pose in enumerate(poses):
 f=dict(d['frames'][0]);f['age']=f['time']=i/120;f['bones']={};f['landed']=False
 for n,k in pose.items():
  q=R.from_matrix(C@R.from_quat(np.roll(k['q'],-1)).as_matrix()@C).as_quat();f['bones'][n]={'p':list(C@k['p']*100),'q':list(np.roll(q,1)),'s':k['s']}
 out.append(f)
d['frames']=out;(p/'Draft').mkdir(exist_ok=True);(p/'Draft/frames-120.json').write_text(json.dumps(d))
