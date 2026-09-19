import bpy,math
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'grip_fitted.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;s.frame_set(0);bpy.context.view_layer.update()
# Shared review lighting/cameras, fixed contact pose.
for o in s.objects:o.hide_render=o.type!='MESH' or o.parent!=r
s.world.color=(.1,.1,.1)
for pos in [(-.7,-.3,.8),(.8,.5,.8)]:
 d=bpy.data.lights.new('Review','AREA');d.energy=95;d.size=1;o=bpy.data.objects.new('Review',d);s.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector((0,.2,-.1))-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('ReviewCam');cam=bpy.data.objects.new('ReviewCam',d);s.collection.objects.link(cam);s.camera=cam;d.clip_start=.005;s.render.engine='BLENDER_EEVEE';s.eevee.taa_render_samples=16;s.render.resolution_x=800;s.render.resolution_y=600;s.render.resolution_percentage=100
focus=r.pose.bones['hand_l'].head.copy()+Vector((0,0,.025))
for i,off in enumerate([(-.35,-.3,.25),(.35,-.3,.25),(0,.4,.2)]):
 d.type='ORTHO';d.ortho_scale=.34;cam.location=focus+Vector(off);cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/f'grip_fitted_{i}.png');bpy.ops.render.render(write_still=True)
