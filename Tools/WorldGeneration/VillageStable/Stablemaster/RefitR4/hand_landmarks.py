"""Extract the actual glove branches on the fingerless Meshy rig for wrist aiming."""
from pathlib import Path
import bpy,numpy as np,json
rig=bpy.data.objects['Armature'];body=bpy.data.objects['SK_Stablemaster_Body']
out={}
for side in ('Left','Right'):
    n=side+'Hand';g=body.vertex_groups[n].index
    points=np.array([v.co[:] for v in body.data.vertices if any(i.group==g and i.weight>.8 for i in v.groups)])
    wrist=np.array(rig.data.bones[n].head_local)
    far=points[np.linalg.norm(points-wrist,axis=1)>np.percentile(np.linalg.norm(points-wrist,axis=1),87)]
    center=np.median(far,axis=0);out[n]=((center-wrist)*np.array([1.,-1.,1.])).tolist()
(Path(bpy.data.filepath).parent/'palms.json').write_text(json.dumps(out,indent=2))
