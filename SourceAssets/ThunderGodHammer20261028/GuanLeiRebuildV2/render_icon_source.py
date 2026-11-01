import bpy,sys,math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(P/'GuanLeiSeatV2_Editable.blend'),link=False) as (a,b):b.objects=['SM_ThunderHammer_GuanLeiSeatV2']
bpy.context.collection.objects.link(b.objects[0])
bpy.context.preferences.filepaths.save_version=0
obj=bpy.data.objects['SM_ThunderHammer_GuanLeiSeatV2']
mat=next(m for m in obj.data.materials if m.name=='M_ThunderGodHammerSurface');mat.use_nodes=True;ns=mat.node_tree.nodes;ls=mat.node_tree.links;ns.clear()
bs=ns.new('ShaderNodeBsdfPrincipled');out=ns.new('ShaderNodeOutputMaterial');ls.new(bs.outputs['BSDF'],out.inputs['Surface'])
def tex(name,space):
    n=ns.new('ShaderNodeTexImage');n.image=bpy.data.images.load(str(P.parent/'Textures'/(name+'.jpg')),check_existing=False);n.image.colorspace_settings.name=space;return n
c=tex('BaseColor','sRGB');mr=tex('MetallicRoughness','Non-Color');normal=tex('Normal','Non-Color');ls.new(c.outputs['Color'],bs.inputs['Base Color']);sep=ns.new('ShaderNodeSeparateColor');ls.new(mr.outputs['Color'],sep.inputs[0]);ls.new(sep.outputs['Green'],bs.inputs['Roughness']);ls.new(sep.outputs['Blue'],bs.inputs['Metallic']);nm=ns.new('ShaderNodeNormalMap');ls.new(normal.outputs['Color'],nm.inputs[0]);ls.new(nm.outputs['Normal'],bs.inputs['Normal'])
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
for layer in scene.view_layers:layer.material_override=None
scene.use_nodes=False;scene.render.use_compositing=False;scene.compositing_node_group=None;scene.render.use_sequencer=False
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=0;scene.view_settings.gamma=1
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100;scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.world=bpy.data.worlds.new('Neutral studio');scene.world.use_nodes=True;wn=scene.world.node_tree.nodes;wn.clear();bg=wn.new('ShaderNodeBackground');wo=wn.new('ShaderNodeOutputWorld');scene.world.node_tree.links.new(bg.outputs[0],wo.inputs[0]);bg.inputs[0].default_value=(.13,.13,.13,1);bg.inputs[1].default_value=.3
vs=[v.co for v in obj.data.vertices];lo=Vector([min(v[i] for v in vs) for i in range(3)]);hi=Vector([max(v[i] for v in vs) for i in range(3)]);scale=1.25/max(hi-lo);obj.scale=(scale,)*3;obj.location=-(lo+hi)*.5*scale
bpy.ops.object.camera_add(location=(1.15,-4,.6));cam=bpy.context.object;cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=1.6;scene.camera=cam
for loc,power,size in [((-2,-3,3),450,3),((2,-2,1),300,2),((0,1,2),450,2)]:
    bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=power;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(-o.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(P/'GuanLeiSeatV2_IconSource.png');bpy.ops.render.render(write_still=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'GuanLeiSeatV2_IconSource.blend'))
