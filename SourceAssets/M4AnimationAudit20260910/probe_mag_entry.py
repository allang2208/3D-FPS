import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Hand_MAT_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];a=bpy.data.actions['M4_MAT_reload'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(95);bpy.context.view_layer.update();inv=r.pose.bones['WPN_root'].matrix.inverted();dg=bpy.context.evaluated_depsgraph_get();body=bpy.data.objects['M4_M4 Body_Export'];mag=bpy.data.objects['M4_Magazine Light.003_Export'];ev=body.evaluated_get(dg);m=ev.to_mesh();tree=BVHTree.FromPolygons([inv@ev.matrix_world@v.co for v in m.vertices],[list(p.vertices) for p in m.polygons]);ev.to_mesh_clear();ev=mag.evaluated_get(dg);m=ev.to_mesh();ps=[inv@ev.matrix_world@v.co for v in m.vertices];ev.to_mesh_clear();top=max(v.z for v in ps);tip=[v for v in ps if v.z>top-.018];report=[]
for d in [0,.012,.025,.040,.050,.055,.060,.065,.070,.075,.080]:
 ds=[tree.find_nearest(v-Vector((0,0,d)))[3]*1000 for v in tip];report.append({'offset_m':d,'nearest_tip_body_mm':min(ds),'tip_top_z_m':top-d})
print(report);(O/'mag_entry_geometry.json').write_text(json.dumps(report,indent=2))
