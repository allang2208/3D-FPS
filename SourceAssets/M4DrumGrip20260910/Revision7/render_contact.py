import bpy
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'M4_DrumMatch_Editable.blend'));s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima']

with bpy.data.libraries.load(str(O.parent.parent/'M4Drum20260909/M4_Drum_Optimized.blend'),link=False) as (src,dst): dst.objects=['SM_M4_LargeDrum']
drum=dst.objects[0];s.collection.objects.link(drum);drum.parent=r;drum.hide_render=False
for mod in drum.modifiers:
 if mod.type=='ARMATURE':mod.object=r
for obj in s.objects:
 if obj.type=='MESH' and 'Magazine' in obj.name:obj.hide_render=True
s.render.resolution_x=900;s.render.resolution_y=650;s.render.resolution_percentage=100
for clip,frame in [('reload_empty',116)]:
 for label,prefix in [('after','A_M4_DrumMatch_')]:
  a=bpy.data.actions[prefix+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(frame);bpy.context.view_layer.update()
  focus=r.pose.bones['hand_l'].head.lerp(r.pose.bones['lowerarm_l'].head,.25);cam=s.camera;cam.data.type='ORTHO';cam.data.ortho_scale=.48;cam.location=focus+Vector((-.65,-.45,.15));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/f'{label}_{clip}_{frame}.png');bpy.ops.render.render(write_still=True)
