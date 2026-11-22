from pathlib import Path
import json,gzip,numpy as np
from mathutils.bvhtree import BVHTree
from mathutils import Vector
b=Path(__file__).resolve().parent
src=Path(json.loads((b/'inputs.json').read_text())['project'])/'SourceAssets/SkeletonSniperStock20261031/Review20261031'
d=json.load(gzip.open(b/'SVCH_after.json.gz','rt'))
f=np.array(d['triangles']);v=np.array(d['positions']);ids=np.array(d['material_ids'])
mount=np.array(json.loads((src/'fit_metrics.json').read_text())['SVCH']['stock_component_matrix'])
v=v@mount[:3,:3].T+mount[:3,3]
t0=f[ids==0];t1=f[ids==1];p0,inv=np.unique(t0,return_inverse=True);p1,j=np.unique(t1,return_inverse=True)
s=BVHTree.FromPolygons(v[p0].tolist(),inv.reshape(-1,3).tolist(),all_triangles=True)
v1=v[p1]; span=np.ptp(v1[:,1]); offset=0
for fraction in (0,.06,-.06,.12,-.12,.18,-.18,.25,-.25,.35,-.35,.5,-.5,.75,-.75,1.,-1.):
    disp=np.array([0,fraction*span,0]);trim=BVHTree.FromPolygons((v1-disp).tolist(),j.reshape(-1,3).tolist(),all_triangles=True)
    count=len(s.overlap(trim));print('render fraction',fraction,'overlap',count,flush=True)
    if count>20:offset=float(disp[1]);break
if not offset:raise RuntimeError('No continuous mesh overlap using the native trim')
(b/'visual_offset.json').write_text(json.dumps({'host_y':offset,'reference':'native trim depth','fraction':fraction}))
