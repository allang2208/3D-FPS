"""Check the upper/lower arm material boundary, not merely joint angles."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from collections import defaultdict
HERE=Path(__file__).resolve().parent
d=json.loads((HERE/'Input/Bare.json').read_text());v=np.array(d['positions']);t=np.array(d['triangles']);m=np.array(d['triangle_materials']);w=d['weights'];normals=np.array(d['normals'])
left=np.array([sum(x for n,x in ws.items() if n.endswith('_l'))>.99 for ws in w]);report={}
for a,b,label in [(0,1,'elbow_upper_lower'),(1,2,'wrist_lower_hand')]:
    ia=np.array(sorted({i for f in t[m==a] for i in f if left[i]}));ib=np.array(sorted({i for f in t[m==b] for i in f if left[i]}))
    distance,j=cKDTree(v[ib]).query(v[ia]);pairs=[(int(i),int(ib[k])) for i,k,x in zip(ia,j,distance) if x<1.e-4]
    mismatch=[sum(abs(w[i].get(n,0)-w[k].get(n,0)) for n in set(w[i])|set(w[k])) for i,k in pairs]
    report[label]={'paired_vertices':len(pairs),'unique_seam_positions':len({tuple(v[i]) for i,k in pairs}),
        'maximum_weight_difference':max(mismatch),'maximum_reference_gap_cm':max(float(np.linalg.norm(v[i]-v[k])) for i,k in pairs),
        'same_position_and_same_weights_for_every_pose':all(x==0 for x in mismatch) and all(np.array_equal(v[i],v[k]) for i,k in pairs)}
(HERE/'body_seam_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
