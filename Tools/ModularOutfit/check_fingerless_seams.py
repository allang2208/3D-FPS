"""Measure saved-asset opening correspondence, including generated distance LODs."""
import json
from pathlib import Path
from collections import Counter
import numpy as np
from scipy.spatial import cKDTree
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2/ClearanceAfter';rows=[]
def read(p):return json.loads(p.read_text())
for f in sorted(R.glob('*_glove*.json')):
    d=read(f);s=read(f.with_name(f.name.replace('_glove','_skin')));p=np.asarray(d['positions']);t=np.asarray(d['triangles'])
    _,unique,mapping=np.unique(np.round(p,5),axis=0,return_index=True,return_inverse=True);t=mapping[t];edges=Counter(tuple(sorted((int(a),int(b)))) for face in t for a,b in zip(face,np.roll(face,-1)))
    boundary=np.array(sorted({v for edge,n in edges.items() if n==1 for v in edge}));points=p[unique[boundary]]
    dist,_=cKDTree(np.asarray(s['positions'])).query(points)
    row=dict(mesh=f.stem,boundary_vertices=len(boundary),max_gap_mm=float(dist.max()*10),p99_gap_mm=float(np.percentile(dist,99)*10));rows.append(row)
    print('SAVED_OPENING',f.stem,round(row['max_gap_mm'],6),flush=True)
(R/'opening-seams.json').write_text(json.dumps(rows,indent=2))
