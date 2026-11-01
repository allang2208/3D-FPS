import bpy,json
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(O.parent/'M24CustomScope20261026/Donor/Source/source/arms@sniper.fbx'))
r=bpy.data.objects['Armature'];skin=bpy.data.objects['armmesh'];bpy.context.scene.frame_set(30);bpy.context.view_layer.update()
ev=skin.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
for n in ('R_wrist','L_wrist','R_middle1','L_middle1','R_point1','R_pink1'):
 g=skin.vertex_groups.get(n);pts=[ev.matrix_world@me.vertices[v.index].co for v in skin.data.vertices if g and any(x.group==g.index and x.weight>.5 for x in v.groups)]
 print(n,'bone',list(r.matrix_world@r.pose.bones[n].head),'tail',list(r.matrix_world@r.pose.bones[n].tail),'skinmean',list(sum(pts,Vector())/len(pts)) if pts else None,'skin_count',len(pts),flush=True)
for n in ('Armature','armmesh','sniper','base','bolt'):
 o=bpy.data.objects[n];print('OBJ',n,[list(v) for v in o.matrix_world],flush=True)
ev.to_mesh_clear()
print('Modifiers',[(m.type,m.object.name if hasattr(m,'object') and m.object else None) for m in skin.modifiers],flush=True)
