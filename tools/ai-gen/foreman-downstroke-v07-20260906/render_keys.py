import bpy
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(R/'foreman-downstroke-v07.blend'))
a=bpy.data.objects['ForemanRig'];s=bpy.context.scene
s.render.engine='CYCLES';s.cycles.samples=12;s.render.resolution_x=960;s.render.resolution_y=800;s.render.resolution_percentage=100
a.animation_data.action=bpy.data.actions['Attack'];cam=s.camera;cam.data.ortho_scale=3.65
for light in [o for o in s.objects if o.type=='LIGHT']:light.data.energy*=1.4
for t in [0,.24,.35,.42,.50,.59625,.71,.91,1.20,1.5]:
 s.frame_set(int(t*s.render.fps),subframe=t*s.render.fps%1);bpy.context.view_layer.update()
 cam.location=(-4,-6,2.7);cam.rotation_euler=(Vector((0,0,1.38))-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(R/f'key-{t:.3f}.png');bpy.ops.render.render(write_still=True)
 if t in [0,.35,.59625]:
  target=a.pose.bones['hand.R'].matrix.translation;cam.data.ortho_scale=.65;cam.location=target+Vector((-1,-2,.5));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(R/f'grip-{t:.3f}.png');bpy.ops.render.render(write_still=True);cam.data.ortho_scale=3.65
