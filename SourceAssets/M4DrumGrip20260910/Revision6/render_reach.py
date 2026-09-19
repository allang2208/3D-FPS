import bpy
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M4_DrumThrow_Editable.blend'))
s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima']
s.render.resolution_x=900;s.render.resolution_y=700;s.render.resolution_percentage=100
for clip,frames in [('reload',[20,27,34,36,40,44,50]),('reload_empty',[23,29,31,35,38,43])]:
 a=bpy.data.actions['A_M4_DrumThrow_'+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
 for frame in frames:
  s.frame_set(frame);bpy.context.view_layer.update()
  cam=s.camera;focus=Vector((-.12,-.10,-.30));cam.data.type='ORTHO';cam.data.ortho_scale=1.45;cam.location=focus+Vector((-1,-.10,.27));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler()
  s.render.filepath=str(O/f'reach_{clip}_{frame}.png');bpy.ops.render.render(write_still=True)
