"""Requested model troubleshooting: same-camera factory and five actual authored meshes."""
import bpy,math,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;(P/'Preview').mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P/'ThorFactoryDerivedSeatsV3.blend'))
scene=bpy.context.scene
parts=[o for o in scene.objects if o.type=='MESH']
surface=parts[0].data.materials[0];surface.use_nodes=True;ns=surface.node_tree.nodes;ls=surface.node_tree.links;ns.clear()
bs=ns.new('ShaderNodeBsdfPrincipled');out=ns.new('ShaderNodeOutputMaterial');ls.new(bs.outputs['BSDF'],out.inputs['Surface'])
def tex(name,space):
 n=ns.new('ShaderNodeTexImage');n.image=bpy.data.images.load(str(P.parent/'Textures'/(name+'.jpg')),check_existing=False);n.image.colorspace_settings.name=space;return n
color=tex('BaseColor','sRGB');mr=tex('MetallicRoughness','Non-Color');normal=tex('Normal','Non-Color')
ls.new(color.outputs['Color'],bs.inputs['Base Color']);sep=ns.new('ShaderNodeSeparateColor');ls.new(mr.outputs['Color'],sep.inputs[0]);ls.new(sep.outputs['Green'],bs.inputs['Roughness']);ls.new(sep.outputs['Blue'],bs.inputs['Metallic']);nm=ns.new('ShaderNodeNormalMap');ls.new(normal.outputs['Color'],nm.inputs['Color']);ls.new(nm.outputs['Normal'],bs.inputs['Normal'])
for o in parts:o.hide_set(False);o.hide_render=True
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.film_transparent=True
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.use_compositing=False;scene.render.use_sequencer=False
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=0
scene.world=bpy.data.worlds.new('Comparison neutral studio');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.12,.12,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.4
for o in parts:o.location=Vector((0,0,-.916));o.scale=(1,1,1)
bpy.ops.object.camera_add(location=(.075,-.42,.045));cam=bpy.context.object;cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.191;scene.camera=cam
for loc,power,size in [((-.22,-.3,.28),5,.3),((.2,-.22,.04),2.6,.2),((0,.15,.2),5,.2)]:
 bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=power;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(-o.location).to_track_quat('-Z','Y').to_euler()
for ob in parts:
 ob.hide_render=False;scene.render.filepath=str(P/'Preview'/(ob.name+'.png'));bpy.ops.render.render(write_still=True);ob.hide_render=True
print('COMPARISON_RENDERED',flush=True)
