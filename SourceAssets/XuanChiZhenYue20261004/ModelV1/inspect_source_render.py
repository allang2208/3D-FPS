"""Source-only geometry views requested by the user for usability assessment."""
import bpy, math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'XuanChi_Original_Editable.blend'))
source=next(o for o in bpy.context.scene.objects if o.type=='MESH')
for x,angle in [(-.40,0),(0,math.pi/2),(.40,math.pi)]:
    obj=source.copy();obj.data=source.data;bpy.context.scene.collection.objects.link(obj);obj.location.x=x;obj.rotation_mode='XYZ';obj.rotation_euler.z=angle
source.hide_render=True
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True
scene.render.resolution_x=1200;scene.render.resolution_y=1600;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('AssessmentWorld');scene.world.color=(.3,.3,.3);scene.view_settings.view_transform='AgX';scene.view_settings.exposure=-1
cam_data=bpy.data.cameras.new('AssessmentCamera');cam=bpy.data.objects.new('AssessmentCamera',cam_data);scene.collection.objects.link(cam)
cam.location=(0,-5,0);cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat('-Z','Y').to_euler();cam_data.type='ORTHO';cam_data.ortho_scale=2.13;scene.camera=cam
for name,pos,power,size in [('Key',(-2,-3,3),550,4),('Fill',(2,-2,0),350,3),('Top',(0,1,3),400,2)]:
    data=bpy.data.lights.new(name,'AREA');obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=pos;data.energy=power;data.shape='DISK';data.size=size;obj.rotation_euler=(-obj.location).to_track_quat('-Z','Y').to_euler()
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(P/'source_assessment.png');bpy.ops.render.render(write_still=True)
