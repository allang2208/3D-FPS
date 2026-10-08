from pathlib import Path
import json,numpy as np,trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006/TentacleRepairV2')
d=np.load(ROOT/'diagnostic_surface.npz');v=d['vertices'];t=d['triangles']
m=trimesh.Trimesh(v,t,process=False)
report=[]
for z in np.arange(.37,-.535,-.025):
    section=m.section(plane_origin=[0,0,z],plane_normal=[0,0,1]);row={'z':float(z),'contours':[]}
    if section:
        for path in section.discrete:
            c=path.mean(0);lo=path.min(0);hi=path.max(0)
            if -.24<c[0]<.14 and c[1]<.02:
                row['contours'].append({'c':np.round(c,5).tolist(),'lo':np.round(lo,5).tolist(),'hi':np.round(hi,5).tolist(),'closed':bool(np.linalg.norm(path[0]-path[-1])<1e-5)})
    report.append(row)
(ROOT/'sections.json').write_text(json.dumps(report,indent=2))
for r in report:print(round(r['z'],3),r['contours'])
