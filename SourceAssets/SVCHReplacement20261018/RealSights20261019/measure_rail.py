import bpy, json
import numpy as np
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'SightsR2/SVCH_SightsR2_ElbowFit_Editable.blend'),load_ui=False)
ob=bpy.data.objects['SVCH_New_KVInhibitor']
p=np.array([tuple(ob.matrix_world@v.co) for v in ob.data.vertices])*[100,-100,100]
# Actual rail vertices used for fitting the visual attachment, in component cm.
rail=p[(p[:,2]>-.8)&(p[:,2]<.15)&(abs(p[:,0]-6.07)<1.7)]
np.save(O/'rail_vertices_cm.npy',rail)
from mathutils.bvhtree import BVHTree
from mathutils import Vector
trees=[]
for ob in bpy.context.scene.objects:
 if ob.type!='MESH' or not ob.name.startswith('SVCH_New_'):continue
 pts=[ob.matrix_world@v.co for v in ob.data.vertices]
 trees.append(BVHTree.FromPolygons(pts,[p.vertices[:] for p in ob.data.polygons]))
def ray(x,y):
 hits=[t.ray_cast(Vector((x*.01,-y*.01,.1)),Vector((0,0,-1))) for t in trees]
 return round(max([h[0].z*100 for h in hits if h[0] is not None],default=-99),5)
samples={str(y):[ray(6.07+x,y) for x in [0,-.75,.75,-1,1]] for y in np.arange(-16,-10,.2).round(3).tolist()+np.arange(-64,-57,.2).round(3).tolist()}
(O/'rail_samples.json').write_text(json.dumps(samples,indent=2))
for k,v in samples.items():print(k,v)
