import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
sys.path.insert(0,'C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts')
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(P.parent/'ModulesV1/ThunderGodHammer_Modular_Editable.blend'),link=False) as (a,b):
    b.objects=['SM_ThunderGodHammer_'+s+'_factory' for s in ['head_mount','hammer_heads','grip','pommel']]
for ob in b.objects:bpy.context.collection.objects.link(ob)
bpy.context.preferences.filepaths.save_version=0
names=['head_mount','hammer_heads','grip','pommel']
parts={s:bpy.data.objects['SM_ThunderGodHammer_'+s+'_factory'] for s in names}
info={}
for s,o in parts.items():
    vs=[o.matrix_world@v.co for v in o.data.vertices]
    info[s]={'bounds':[[min(v[i] for v in vs) for i in range(3)],[max(v[i] for v in vs) for i in range(3)]],'materials':[m.name for m in o.data.materials]}
(P/'source_geometry.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
for o in list(bpy.context.scene.objects):
    if o not in parts.values():bpy.data.objects.remove(o,do_unlink=True)
surface=next(iter(parts.values())).data.materials[0]
surface.use_nodes=True;ns=surface.node_tree.nodes;ls=surface.node_tree.links;ns.clear()
bs=ns.new('ShaderNodeBsdfPrincipled');out=ns.new('ShaderNodeOutputMaterial');ls.new(bs.outputs['BSDF'],out.inputs['Surface'])
def tex(name,space):
    n=ns.new('ShaderNodeTexImage');n.image=bpy.data.images.load(str(P.parent/'Textures'/(name+'.jpg')),check_existing=False);n.image.colorspace_settings.name=space;return n
color=tex('BaseColor','sRGB');mr=tex('MetallicRoughness','Non-Color');normal=tex('Normal','Non-Color')
ls.new(color.outputs['Color'],bs.inputs['Base Color']);sep=ns.new('ShaderNodeSeparateColor');ls.new(mr.outputs['Color'],sep.inputs['Color'])
ls.new(sep.outputs['Green'],bs.inputs['Roughness']);ls.new(sep.outputs['Blue'],bs.inputs['Metallic'])
nm=ns.new('ShaderNodeNormalMap');ls.new(normal.outputs['Color'],nm.inputs['Color']);ls.new(nm.outputs['Normal'],bs.inputs['Normal'])
gray=ns.new('ShaderNodeRGBToBW');ls.new(color.outputs['Color'],gray.inputs[0]);ls.new(gray.outputs[0],bs.inputs['Base Color'])
for o in parts.values():o.hide_render=True
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
for layer in scene.view_layers:layer.material_override=None
scene.use_nodes=False
scene.render.use_sequencer=False
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.world=bpy.data.worlds.new('Factory neutral studio');scene.world.use_nodes=True;wn=scene.world.node_tree.nodes;wn.clear();bg=wn.new('ShaderNodeBackground');wo=wn.new('ShaderNodeOutputWorld');scene.world.node_tree.links.new(bg.outputs[0],wo.inputs[0]);bg.inputs[0].default_value=(.13,.13,.13,1);bg.inputs[1].default_value=.3
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=0;scene.view_settings.gamma=1
scene.render.use_compositing=False;scene.compositing_node_group=None
bpy.ops.object.camera_add(location=(.4,-4,.28));cam=bpy.context.object;cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=1.5;scene.camera=cam
for loc,power,size in [((-2,-3,3),420,3),((2,-2,1),300,2),((0,1,2),350,2)]:
    bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=power;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(-o.location).to_track_quat('-Z','Y').to_euler()
for s,o in parts.items():
    vs=[v.co for v in o.data.vertices];lo=Vector([min(v[i] for v in vs) for i in range(3)]);hi=Vector([max(v[i] for v in vs) for i in range(3)])
    scale=1.25/max(hi-lo);o.scale=(scale,)*3;o.location=-(lo+hi)*.5*scale;o.hide_render=False
    scene.render.filepath=str(P/'References'/(s+'.png'));bpy.ops.render.render(write_still=True);o.hide_render=True
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'FactoryIconSources.blend'))
print('FACTORY_REFERENCES_SAVED')
