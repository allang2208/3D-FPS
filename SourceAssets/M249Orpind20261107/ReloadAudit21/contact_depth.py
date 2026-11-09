from pathlib import Path
import numpy as np,json
from mathutils.bvhtree import BVHTree
from mathutils import Vector
r=Path(__file__).resolve().parent;folder=r/'completed/box_empty_base_left';meta=json.loads((folder/'geometry.json').read_text());j=json.loads((folder/'review.json').read_text());dom=np.fromfile(folder/'dominant.bin',np.uint32);names=meta['bones'];onright=np.array([n.endswith('_r') for n in names])[dom]
for source,slot in [(.057,'M249_Factory_Receiver'),(.057,'M249_Factory_RearGrip'),(4.35,'M249_OpticalHousing'),(1.,'M249_Factory_Cover')]:
 row=min(j['frames'],key=lambda x:abs(x['source']-source));stem=folder/Path(row['file']).stem;v=np.fromfile(stem.with_suffix('.vertices'),np.float32).reshape(-1,3);f=np.fromfile(stem.with_suffix('.indices'),np.uint32).reshape(-1,3);m=np.fromfile(stem.with_suffix('.materials'),np.uint32);arm=f[np.isin(m,[7,8,9])];keep=onright[arm].all(1) if source!=1 else (~onright[arm]).all(1);arm=arm[keep];obs=f[m==meta['slots'].index(slot)];a=BVHTree.FromPolygons(v.tolist(),arm.tolist(),all_triangles=True);b=BVHTree.FromPolygons(v.tolist(),obs.tolist(),all_triangles=True);pairs=a.overlap(b);ids=np.unique(arm[np.unique([x for x,y in pairs])]) if pairs else [];depth=[]
 for i in ids:
  p,n,idx,dist=b.find_nearest(Vector(v[i]));depth.append(float(dist)*(-1 if (Vector(v[i])-p).dot(n)<0 else 1))
 print(source,row['source'],slot,'tri',len(set(a for a,b in pairs)),'signed nearest cm',np.percentile(depth,[0,10,50,90,100]).tolist() if depth else [])
