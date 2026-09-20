import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;S=O.parent
out={}
jobs=[('m4','ExtMagContact20260919/A_M4_ExtContact_reload.blend',None),('m4_empty','ExtMagContact20260919/A_M4_ExtContact_reload_empty.blend',None),('m16','M16Gameplay20260919/M16_Manny_Editable.blend','M16_reload'),('m16_idle','M16Gameplay20260919/M16_Manny_Editable.blend','M16_idle')]
for label,file,action in jobs:
 bpy.ops.wm.open_mainfile(filepath=str(S/file),use_scripts=False);r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
 if action:r.animation_data.action=bpy.data.actions[action];r.animation_data.action_slot=r.animation_data.action.slots[0]
 d={'file':file,'action':r.animation_data.action.name,'meshes':[o.name for o in s.objects if o.type=='MESH'],'rest':{b.name:[list(row) for row in b.matrix_local] for b in r.data.bones},'frames':{}}
 frames=[0,43,54,61,70,76,80,88,95,108,111,126]
 for f in frames:
  s.frame_set(f);bpy.context.view_layer.update();p={b.name:b.matrix.copy() for b in r.pose.bones};wi=p['WPN_root'].inverted()
  d['frames'][f]={n:[list(row) for row in (wi@p[n])] for n in ['WPN_SOCKET_Magazine','hand_l']};d['frames'][f]['root']=[list(row) for row in p['WPN_root']]
 out[label]=d
 if label not in ['m4','m16']:continue
 for o in s.objects:
  if o.type=='MESH':
   visible=o.name=='SK_Manny_Arms_Export' or (o.name.startswith('M4_') and o.name.endswith('_Export')) if label=='m4' else o.name=='SK_Manny_Arms_Export' or o.name.startswith('M16A2_')
   o.hide_render=not visible
   if o.name in bpy.context.view_layer.objects:o.hide_set(not visible)
   o.color=(.22,.40,.57,1) if o.name=='SK_Manny_Arms_Export' else (.73,.47,.13,1) if 'Magazine' in o.name else (.30,.32,.34,1)
  elif o.type=='ARMATURE':o.hide_render=True
 if not s.world:s.world=bpy.data.worlds.new('DiagnosticWorld')
 s.world.color=(.10,.10,.10);s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT';s.display.shading.show_cavity=True;s.display.shading.background_type='WORLD'
 s.render.resolution_x=720;s.render.resolution_y=540;s.render.resolution_percentage=100;s.render.use_compositing=False;s.render.use_sequencer=False
 c=bpy.data.objects.new('InsertSourceCamera',bpy.data.cameras.new('InsertSourceCamera'));s.collection.objects.link(c);s.camera=c;c.data.type='ORTHO';c.data.ortho_scale=.53
 for f in ([61,76,88,95,108] if label=='m4' else [76,95,126]):
  s.frame_set(f);bpy.context.view_layer.update();W=r.matrix_world@r.pose.bones['WPN_root'].matrix
  center=W@Vector((0,-.11,-.035));c.location=center+W.to_quaternion()@Vector((-.65,.22,.08));c.rotation_euler=(center-c.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/f'{label}_{f}.png');bpy.ops.render.render(write_still=True)
(O/'source_geometry.json').write_text(json.dumps(out,indent=2))
print('SOURCE_INSPECTION_COMPLETE',flush=True)
