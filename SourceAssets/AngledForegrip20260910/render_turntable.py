import bpy,math
from pathlib import Path
from mathutils import Vector
p=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(p/'AngledForegrip_M4_Editable.blend'))
s=bpy.context.scene;s.render.engine='BLENDER_EEVEE';s.render.resolution_x=960;s.render.resolution_y=640
folder=p/'Turntable';folder.mkdir(exist_ok=True)
for i in range(48):
 a=2*math.pi*i/48
 s.camera.location=(math.sin(a)*4,-math.cos(a)*4,1.3)
 s.camera.rotation_euler=(Vector((0,0,-.025))-s.camera.location).to_track_quat('-Z','Y').to_euler()
 s.render.filepath=str(folder/f'{i:03d}.png');bpy.ops.render.render(write_still=True)
print('TURNTABLE_RENDER_OK')
