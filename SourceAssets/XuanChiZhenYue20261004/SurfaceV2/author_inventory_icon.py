"""Production inventory artwork using the current V2 assembly and PBR sources."""
import bpy,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'XuanChi_SurfaceV2_Editable.blend'))
scene=bpy.context.scene
names=['SM_XuanChi_Guard_V2','SM_XuanChi_Blade_V2','SM_XuanChi_Grip_V2','SM_XuanChi_Pommel_V2','SM_XuanChi_Tassel']
for obj in scene.objects:
    if obj.type=='MESH':obj.hide_render=obj.name not in names
points=[bpy.data.objects[name].matrix_world@Vector(c) for name in names for c in bpy.data.objects[name].bound_box]
lo=Vector(tuple(min(p[i] for p in points) for i in range(3)));hi=Vector(tuple(max(p[i] for p in points) for i in range(3)));center=(lo+hi)*.5
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True;scene.render.threads_mode='FIXED';scene.render.threads=3
scene.render.resolution_x=384;scene.render.resolution_y=768;scene.render.resolution_percentage=100;scene.render.film_transparent=True
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.view_settings.view_transform='AgX'
scene.world=bpy.data.worlds.new('InventoryStudio');scene.world.color=(.25,.25,.25)
cd=bpy.data.cameras.new('InventoryCamera');cam=bpy.data.objects.new('InventoryCamera',cd);scene.collection.objects.link(cam);scene.camera=cam
cd.type='ORTHO';cd.ortho_scale=(hi.z-lo.z)/.91;cam.location=center+Vector((0,-5,0));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
for name,where,power,size in [('Key',(-2,-3,3),480,3),('Fill',(2,-2,.3),230,2),('Rim',(.5,1,2),350,2)]:
    ld=bpy.data.lights.new(name,'AREA');obj=bpy.data.objects.new(name,ld);scene.collection.objects.link(obj);obj.location=center+Vector(where);obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler();ld.energy=power;ld.size=size
scene.render.filepath=str(P/'ue_xuanchi_zhenyue_v2.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'XuanChi_InventoryIconV2.blend'))
print('XUANCHI_V2_INVENTORY_ARTWORK_SAVED')
