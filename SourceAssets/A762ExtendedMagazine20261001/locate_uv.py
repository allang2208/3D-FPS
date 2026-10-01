import bpy,numpy as np
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'A762_ExtMag_Continuous07.blend'))
me=bpy.data.objects['A762_ContinuousMagazineShell'].data;me.calc_loop_triangles()
for t in me.loop_triangles:
 uv=np.array([me.uv_layers[0].data[l].uv[:] for l in t.loops]);a=uv[1]-uv[0];b=uv[2]-uv[0]
 if abs(a[0]*b[1]-a[1]*b[0])<2e-12:print('COLLAPSED',t.polygon_index,'area',t.area,'vertices',[me.vertices[i].co[:] for i in t.vertices],'uv',uv.tolist(),flush=True)
