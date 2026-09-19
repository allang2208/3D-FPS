import bpy,json,math
import numpy as np
from pathlib import Path
O=Path(__file__).parent;P=O.parent/'ExtMagPattern20260919';params=json.loads((P/'parameters.json').read_text());r={}
for gun in ['M4','AKM','QBZ']:
 bpy.ops.wm.open_mainfile(filepath=str(P/(gun+'_ExtMag_Editable.blend')));m=next(o.data for o in bpy.context.scene.objects if o.type=='MESH')
 cos=np.array([m.corner_normals[i].vector.dot(p.normal) for p in m.polygons for i in p.loop_indices]);r[gun]={'normal_dot_face_quantiles':np.quantile(cos,[0,.01,.1,.5,.9,1]).tolist(),'backward_corner_normals':int((cos<0).sum())}
 print(gun,r[gun])
(O/'diagnosis.json').write_text(json.dumps(r,indent=2))
