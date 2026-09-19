import bpy
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'grip_fitted.blend'));r=bpy.data.objects['SK_M4_Infima'];h=bpy.data.objects['SK_Manny_Arms_Export'];mag=bpy.data.objects['M4_Magazine Light.003_Export'];bpy.context.scene.frame_set(0);bpy.context.view_layer.update();inv=r.pose.bones['WPN_SOCKET_Magazine'].matrix.inverted();dg=bpy.context.evaluated_depsgraph_get();ev=mag.evaluated_get(dg);m=ev.to_mesh();tree=BVHTree.FromPolygons([inv@ev.matrix_world@v.co for v in m.vertices],[list(p.vertices) for p in m.polygons]);ev.to_mesh_clear();ev=h.evaluated_get(dg);m=ev.to_mesh()
for digit in ['index','middle','ring','pinky','thumb']:
 ids=[v.index for v in h.data.vertices if any(h.vertex_groups[g.group].name==digit+'_03_l' and g.weight>.8 for g in v.groups)];vs=[inv@ev.matrix_world@m.vertices[i].co for i in ids];p=min(vs,key=lambda v:tree.find_nearest(v)[3]);near=tree.find_nearest(p)[0];print(digit,'mean',list(sum(vs,Vector())/len(vs)),'gapvector',list((near-p)*1000))
ev.to_mesh_clear()
