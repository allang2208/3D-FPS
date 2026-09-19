import bpy,numpy as np
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'Canted_Natural.blend'))
v=[];f=[];dg=bpy.context.evaluated_depsgraph_get()
for ob in [o for o in bpy.context.scene.objects if o.name.startswith('CG_')]:
 e=ob.evaluated_get(dg);m=e.to_mesh();m.calc_loop_triangles();off=len(v);v.extend(list(e.matrix_world@x.co) for x in m.vertices);f.extend(tuple(i+off for i in t.vertices) for t in m.loop_triangles);e.to_mesh_clear()
np.savez(O/'grip_surface.npz',vertices=v,faces=f)
