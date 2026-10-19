"""Actual ordinary tactical game-stock render for its inventory icon."""
import bpy,math
from pathlib import Path
from mathutils import Vector
O=Path('D:/FPS3D/FPSGAME/SourceAssets/S12KStockReference20261018')
bpy.ops.wm.open_mainfile(filepath=str(O/'Authoring/Saiga12K_SpecialStock_Editable.blend'));s=bpy.context.scene
for ob in bpy.data.objects:ob.hide_render=True
ob=bpy.data.objects['SM_Saiga12K_SpecialStock'];ob.hide_render=False;ob.hide_set(False)
normal=bpy.data.images.load(str(O/'Textures/T_Saiga12K_SpecialStock_N.png'));normal.colorspace_settings.name='Non-Color'
for mat in ob.data.materials:
 bs=mat.node_tree.nodes.get('Principled BSDF');c=bs.inputs['Base Color'].default_value;v=.16+.45*max(0.,.2126*c[0]+.7152*c[1]+.0722*c[2])**.25;bs.inputs['Base Color'].default_value=(v,v,v,1)
 tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=normal;n=mat.node_tree.nodes.new('ShaderNodeNormalMap');n.uv_map='UV0';mat.node_tree.links.new(tex.outputs['Color'],n.inputs['Color']);mat.node_tree.links.new(n.outputs['Normal'],bs.inputs['Normal'])
s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=True;s.render.resolution_x=1024;s.render.resolution_y=1024;s.render.resolution_percentage=100;s.render.film_transparent=True;s.world=bpy.data.worlds.new('Neutral icon studio');s.world.color=(.26,.26,.26)
target=Vector((.08,19.7,.1));bpy.ops.object.camera_add(location=(65,19.7,.1));cam=bpy.context.object;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=29;s.camera=cam
for loc,power,size in [((20,6,28),15000,30),((17,40,8),10000,24),((-20,22,18),17000,23)]:
 bpy.ops.object.light_add(type='AREA',location=loc);a=bpy.context.object;a.data.energy=power;a.data.shape='DISK';a.data.size=size;a.rotation_euler=(target-a.location).to_track_quat('-Z','Y').to_euler()
s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.filepath=str(O/'Icons/stock_actual_source.png');bpy.ops.wm.save_as_mainfile(filepath=str(O/'Icons/Stock_Icon_Studio.blend'),compress=True);bpy.ops.render.render(write_still=True);print('SAIGA_STOCK_ICON_SOURCE_SAVED',flush=True)
