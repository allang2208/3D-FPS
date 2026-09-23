import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;R=O.parent
bpy.ops.wm.open_mainfile(filepath=str(R/'HandReload10/PKM_ReloadHands_Editable.blend'))
r=bpy.data.objects['PKM_Manny_Rig'];a=bpy.data.actions['PKM_Game_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
bpy.context.scene.frame_set(0);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
rows={}
for ob in bpy.context.scene.objects:
 if ob.type!='MESH' or 'source_part_id' not in ob or ob.name.startswith('New_'):continue
 ev=ob.evaluated_get(dg);me=ev.to_mesh();points=[ev.matrix_world@v.co for v in me.vertices]
 # Blender rig coordinates -> UE FBX component cm -> 90 degree yaw camera anchor.
 camera=[Vector((p.y*100+6,p.x*100+7,p.z*100-7)) for p in points]
 rows[ob.name]={'id':ob['source_part_id'],'materials':[s.material.name for s in ob.material_slots if s.material],
   'camera_bounds':[[min(p[i] for p in camera) for i in range(3)],[max(p[i] for p in camera) for i in range(3)]],
   'points':[[round(v,6) for v in p] for p in camera]}
 ev.to_mesh_clear()
(O/'handle_geometry.json').write_text(json.dumps({'parts':rows,'root':[list(v) for v in r.pose.bones['WPN_root'].matrix]},separators=(',',':')))
print('PKM11_SOURCE_GEOMETRY_READ')
