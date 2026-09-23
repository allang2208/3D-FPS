import bpy,json,pathlib
from mathutils import Vector
O=pathlib.Path(__file__).parent
report={}
for source,clips in [('PKM_Gameplay_Editable.blend',['PKM_Game_idle','PKM_Reload_Normal']),('../Animation03/PKM_Manny_Reload_Editable.blend',['PKM_Idle'])]:
 bpy.ops.wm.open_mainfile(filepath=str(O/source));r=bpy.data.objects['PKM_Manny_Rig'];s=bpy.context.scene
 rows={}
 for name in clips:
  a=bpy.data.actions[name];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
  for frame in [0,60,180]:
   s.frame_set(frame);bpy.context.view_layer.update();bones={}
   for n in ['WPN_root','PKM_Cover','PKM_Box','PKM_BoxLid','New_PKM_Box','PKM_Belt_00','New_PKM_Belt_00']:
    b=r.pose.bones[n];bones[n]={'basis':[list(v) for v in b.matrix_basis],'world':[list(v) for v in b.matrix],'rest':[list(v) for v in b.bone.matrix_local]}
   rows[name+':'+str(frame)]={'bones':bones,'objects':{}}
   dep=bpy.context.evaluated_depsgraph_get()
   for ob in s.objects:
    if ob.type!='MESH' or ob.get('source_part_id') not in [43,47,61]:continue
    ev=ob.evaluated_get(dep);points=[ev.matrix_world@Vector(c) for c in ev.bound_box]
    rows[name+':'+str(frame)]['objects'][ob.name]={'bone':ob.get('mechanical_bone'),'matrix':[list(v) for v in ob.matrix_world],'lo':[min(v[i] for v in points) for i in range(3)],'hi':[max(v[i] for v in points) for i in range(3)]}
 report[source]=rows
(O/'idle_source_inspection.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('PKM_IDLE_SOURCE_INSPECTED')
