"""Scoped source intersection inspection requested for the sleeve repair."""
import json
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/GarmentSleeveRepair20261018'
inventory=json.loads((R/'inventory.json').read_text())
results=[]
for item,profile in [(r['item'],r['profile']) for r in inventory['rows'] if r['item'] in ('ue_field_sweater','ue_field_sweater_charcoal')]:
    row=next(x for x in inventory['rows'] if x['item']==item and x['profile']==profile)
    d=json.loads(Path(row['file']).read_text());p=np.array(d['positions']);f=np.array(d['triangles']);m=np.array(d['triangle_materials'])
    wp,ix,remap=np.unique(np.round(p,5),axis=0,return_index=True,return_inverse=True);wf=remap[f];wp=p[ix]
    tree=BVHTree.FromPolygons([Vector(x) for x in wp],wf.tolist(),all_triangles=True,epsilon=0)
    candidates=tree.overlap(tree)
    pairs=[(a,b) for a,b in candidates if a<b and not set(wf[a])&set(wf[b])]
    bymat={}
    for a,b in pairs:
        key=str(sorted([int(m[a]),int(m[b])]))
        bymat[key]=bymat.get(key,0)+1
    details=[]
    for a,b in pairs:
        details.append(dict(faces=[a,b],materials=[int(m[a]),int(m[b])],center=p[f[[a,b]]].mean((0,1)).tolist()))
    out=dict(item=item,profile=profile,nonadjacent_intersections=len(pairs),by_material=bymat,details=details)
    results.append(out);print(item,profile,len(pairs),bymat,flush=True)
(R/'intersection_diagnosis.json').write_text(json.dumps(results,indent=2))
