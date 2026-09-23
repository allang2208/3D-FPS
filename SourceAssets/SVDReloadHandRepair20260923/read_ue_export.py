import bpy,json
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(O/'UE_Mesh.fbx'))
row={'objects':[]}
for ob in bpy.data.objects:
 entry={'name':ob.name,'type':ob.type,'matrix':[list(r) for r in ob.matrix_world]}
 if ob.type=='MESH': entry.update(vertices=len(ob.data.vertices),groups=[g.name for g in ob.vertex_groups])
 if ob.type=='ARMATURE':entry.update(bones=len(ob.data.bones),rest={b.name:[list(r) for r in b.matrix_local] for b in ob.data.bones})
 row['objects'].append(entry)
bpy.ops.import_scene.fbx(filepath=str(O/'UE_Reload.fbx'))
row['actions']=[{'name':a.name,'frames':list(a.frame_range)} for a in bpy.data.actions]
row['armatures']=[{'name':ob.name,'action':ob.animation_data.action.name if ob.animation_data and ob.animation_data.action else None} for ob in bpy.data.objects if ob.type=='ARMATURE']
(O/'ue_blender_inputs.json').write_text(json.dumps(row))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'UE_Readback.blend'))
print('UE_FBX_INPUTS',json.dumps({k:v for k,v in row.items() if k!='objects'}))
for o in row['objects']:print('UE_OBJECT',o['name'],o['type'],o.get('vertices'),o.get('bones'))
