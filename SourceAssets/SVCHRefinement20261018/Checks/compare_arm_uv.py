import json,gzip,itertools
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
O=Path(__file__).parent
source=json.load(gzip.open(O.parent.parent/'SVCHSketchfab20261017/Donor/vm.json.gz','rt',encoding='utf-8'))
saved=json.loads((O/'arm_surface.json').read_text())
faces=np.array([source['slots'][i] in ('MI_Manny_01','MI_Manny_02') for i in source['material']])
xyz=np.array(source['positions']).reshape(-1,3)
tri=np.array(source['triangles']).reshape(-1,3)[faces]
srcp=xyz[tri];srcuv=np.array(source['uv0']).reshape(-1,3,2)[faces]
dstp=np.array([r['p'] for r in saved['arms']]);dstuv=np.array([r['uv'] for r in saved['arms']])
distance,nearest=cKDTree(srcp.mean(1)).query(dstp.mean(1))
paired=srcp[nearest];uv=srcuv[nearest]
orders=list(itertools.permutations(range(3)))
cost=np.array([np.linalg.norm(dstp-paired[:,p],axis=2).sum(1) for p in orders])
best=cost.argmin(0)
ordered=np.empty_like(uv)
for i,order in enumerate(orders):ordered[best==i]=uv[best==i][:,order]
flipped=dstuv.copy();flipped[:,:,1]=1-flipped[:,:,1]
err=np.linalg.norm(dstuv-ordered,axis=2)
mirrorerr=np.linalg.norm(flipped-ordered,axis=2)
report={'triangles':len(tri),'saved_triangles':len(dstp),'max_centroid_error_cm':float(distance.max()),
        'winding_matches_native':int(sum(tuple(orders[i]) in ((0,1,2),(1,2,0),(2,0,1)) for i in best)),
        'uv_error_mean':float(err.mean()),'uv_error_max':float(err.max()),
        'v_flipped_uv_error_mean':float(mirrorerr.mean()),'v_flipped_uv_error_max':float(mirrorerr.max()),
        'material_paths':saved['materials'],'normal_dots':saved['normal_dots']}
(O/'arm_uv_comparison.json').write_text(json.dumps(report,indent=1))
print(json.dumps(report,indent=1))
