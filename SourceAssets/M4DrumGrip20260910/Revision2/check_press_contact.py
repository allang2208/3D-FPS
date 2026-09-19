import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent;bpy.ops.wm.open_mainfile(filepath=str(O/'M4_DrumGrip_Rebuilt.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;hm=bpy.data.objects['SK_Manny_Arms_Export']
a=bpy.data.actions['A_M4_DrumGrip_reload_empty'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(130);bpy.context.view_layer.update()
group=hm.vertex_groups['index_03_l'].index;ids=[v.index for v in hm.data.vertices if any(g.group==group and g.weight>.8 for g in v.groups)]
ev=hm.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();T=r.pose.bones['WPN_root'].matrix.inverted()@ev.matrix_world
points=sorted([T@mesh.vertices[i].co for i in ids],key=lambda p:p.x);pad=sum(points[:10],Vector())/10;ev.to_mesh_clear()
target=Vector((.0195,-.0934,.055));report={'frame':130,'index_tip_in_gun':list(pad),'target_in_gun':list(target),'error_mm':(pad-target).length*1000,'pass':(pad-target).length<.003}
(O/'release_contact.json').write_text(json.dumps(report,indent=2));print(report)
assert report['pass']
