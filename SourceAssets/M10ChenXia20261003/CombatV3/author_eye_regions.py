"""Place front eye hit regions from the original textured surface coordinates."""
from pathlib import Path
import json,numpy as np
from scipy.spatial import ConvexHull
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent/'RigV1'
d=np.load(BASE/'source_geometry.npz');v=d['vertices'];w=np.load(BASE/'authored_weights.npz')
# Nine visible irises, excluding the lower restraint's metal rivets.
locations=[(-.500,.374,.024,.023),(-.427,.423,.032,.038),(-.320,.488,.025,.028),(-.235,.550,.036,.035),(.005,.573,.030,.023),(.237,.550,.036,.035),(.322,.488,.025,.028),(.429,.423,.032,.038),(.503,.374,.024,.023)]
regions=[]
for i,(y,z,ry,rz) in enumerate(locations):
    ids=np.flatnonzero((v[:,0]>1.3)&((v[:,1]-y)**2+(v[:,2]-z)**2<.009**2))
    if not len(ids):raise RuntimeError('No surface for eye '+str(i))
    x=float(np.quantile(v[ids,0],.95))
    regions.append({'eye':i+1,'blender_center_m':[x,y,z],'ue_reference_center_cm':[x*100,-y*100,z*100],'radii_cm':[8.,ry*100,rz*100]})
(ROOT/'eye_regions.json').write_text(json.dumps({'eyes':regions,'count':len(regions),'region_frame':'reference component space, X forward, cm','query_depth_note':'Front face projection permits up to 16 cm of existing convex-head query padding; lateral/vertical radii follow iris size. Side and rear entries are rejected.','source':'Meshy original surface and BaseColor, geometric authoring only','runtime_tested':False},indent=2),encoding='utf-8')
print(json.dumps(regions))
