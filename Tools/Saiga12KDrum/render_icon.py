"""Render actual authored drum as the production inventory-icon input."""
import bpy,math
from mathutils import Vector
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME/SourceAssets/Saiga12KDrum20261018');bpy.ops.wm.open_mainfile(filepath=str(P/'Authoring/Saiga12K_Drum20_Editable.blend'));s=bpy.context.scene
for o in bpy.data.objects:o.hide_render=True
ob=bpy.data.objects['SM_Saiga12K_Drum20'];ob.hide_render=False;ob.hide_set(False)
for m in ob.data.materials:
 b=m.node_tree.nodes.get('Principled BSDF');c=b.inputs['Base Color'].default_value;v=.2126*c[0]+.7152*c[1]+.0722*c[2];b.inputs['Base Color'].default_value=(v,v,v,1)
s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=True;s.render.resolution_x=1024;s.render.resolution_y=1024;s.render.resolution_percentage=100;s.render.film_transparent=True;s.world=bpy.data.worlds.new('Icon studio');s.world.color=(.3,.3,.3)
target=Vector((0,-12.0,-8.3));bpy.ops.object.camera_add(location=(29,-63,14));cam=bpy.context.object;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=30;s.camera=cam
for loc,power,size in [((10,-40,35),110000,35),((-25,-28,10),75000,24),((15,0,20),125000,22)]:
 bpy.ops.object.light_add(type='AREA',location=loc);a=bpy.context.object;a.data.energy=power;a.data.shape='DISK';a.data.size=size;a.rotation_euler=(target-a.location).to_track_quat('-Z','Y').to_euler()
s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.filepath=str(P/'Icons/drum_actual_icon_source.png');bpy.ops.render.render(write_still=True);print('SAIGA_DRUM_ICON_SOURCE_RENDERED',flush=True)
