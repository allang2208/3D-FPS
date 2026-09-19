import bpy
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'M4_DrumThrow_Editable.blend'));s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima']
s.render.resolution_x=900;s.render.resolution_y=650;s.render.resolution_percentage=100
for clip,frame in [('reload',15),('reload',76),('reload',106),('reload_empty',38),('reload_empty',126)]:
 for label,prefix in [('before','BeforeThrow_'),('after','A_M4_DrumThrow_')]:
  a=bpy.data.actions[prefix+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(frame);bpy.context.view_layer.update()
  focus=r.pose.bones['hand_l'].head.lerp(r.pose.bones['lowerarm_l'].head,.25);cam=s.camera;cam.data.type='ORTHO';cam.data.ortho_scale=.48;cam.location=focus+Vector((-.65,-.45,.15));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/f'{label}_{clip}_{frame}.png');bpy.ops.render.render(write_still=True)
