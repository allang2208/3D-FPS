"""Produce the catalog fallback icon from the selected, textured rifle."""
import bpy
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M24_CustomScope_Native_Editable.blend'),use_scripts=False)
s=bpy.context.scene;s.frame_set(1)
parts=[o for o in s.objects if o.type=='MESH' and o.name!='M24_SourceNativeArms']
for ob in list(bpy.data.objects):
    if ob.type=='MESH' and ob not in parts:bpy.data.objects.remove(ob,do_unlink=True)
points=[o.matrix_world@v.co for o in parts for v in o.data.vertices]
lo=Vector(tuple(min(v[i] for v in points) for i in range(3)));hi=Vector(tuple(max(v[i] for v in points) for i in range(3)))
center=(lo+hi)*.5
camera_data=bpy.data.cameras.new('M24_CatalogCamera');camera=bpy.data.objects.new('M24_CatalogCamera',camera_data)
s.collection.objects.link(camera);s.camera=camera
camera.location=center+Vector((-2.3,0,.13));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
camera_data.type='ORTHO';camera_data.ortho_scale=max(hi.y-lo.y,(hi.z-lo.z)*2.4)/.90
for name,offset,power,size in [('Key',(-1.,-.5,1.1),35,1.5),('Fill',(-1.,.9,.25),22,1.4),('Edge',(.7,.3,.8),45,1.2)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    ob=bpy.data.objects.new(name,data);s.collection.objects.link(ob);ob.location=center+Vector(offset)
    ob.rotation_euler=(center-ob.location).to_track_quat('-Z','Y').to_euler()
s.world=bpy.data.worlds.new('M24_IconWorld');s.world.use_nodes=True
s.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.35
s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=True
s.render.resolution_x=768;s.render.resolution_y=320;s.render.resolution_percentage=100
s.render.film_transparent=True;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA'
s.render.use_compositing=False;s.render.use_sequencer=False
s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';s.view_settings.exposure=.3
s.render.filepath=str(O.parents[1]/'Content/ColdSteelData/Icons/ue_m24.png')
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_CatalogIcon_Editable.blend'))
bpy.ops.render.render(write_still=True)
print('M24_CATALOG_ICON_SAVED',flush=True)
