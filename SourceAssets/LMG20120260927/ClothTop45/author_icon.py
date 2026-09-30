"""Update the existing neutral gunsmith icon from the revised model."""
import bpy,json,importlib.util
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;OUT=O/'Icons';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'LMG201_ClothTop45.blend'),use_scripts=False);bpy.context.preferences.filepaths.save_version=0
scene=bpy.data.scenes.new('C45_ProductionIcon');bpy.context.window.scene=scene;objects=[]
for name in ['C45_AmmoBag_Local','C45_Mount_Local']:
    source=bpy.data.objects[name];a=source.copy();a.data=source.data.copy();a.hide_render=False;scene.collection.objects.link(a);a.hide_set(False);objects.append(a)
cloth=objects[0];mat=cloth.data.materials[0].copy();cloth.data.materials[0]=mat;nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
mask=nodes.new('ShaderNodeUVMap');mask.uv_map='C45Region';sep=nodes.new('ShaderNodeSeparateXYZ');links.new(mask.outputs[0],sep.inputs[0])
for label,value in [('Base Color',(.0865,.1144,.0578,1)),('Roughness',.79)]:
    previous=bs.inputs[label].links[0].from_socket if bs.inputs[label].links else None
    if label=='Base Color':
        blend=nodes.new('ShaderNodeMixRGB');blend.inputs[2].default_value=value;links.new(sep.outputs[0],blend.inputs[0]);links.new(previous,blend.inputs[1]);links.new(blend.outputs[0],bs.inputs[label])
    else:
        mix=nodes.new('ShaderNodeMix');mix.data_type='FLOAT';mix.inputs[3].default_value=value;links.new(sep.outputs[0],mix.inputs[0]);links.new(previous,mix.inputs[2]);links.new(mix.outputs[0],bs.inputs[label])
# Source baked normal is faded out on newly unwrapped fabric. Fine fabric normal
# is shared in scale with UE; no inherited atlas dents on the new roof.
old=bs.inputs['Normal'].links[0].from_socket;tex=nodes.new('ShaderNodeUVMap');tex.uv_map='C45FabricMeters';scale=nodes.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs[3].default_value=1/.00065;links.new(tex.outputs[0],scale.inputs[0]);wave=nodes.new('ShaderNodeTexWave');wave.wave_type='BANDS';wave.bands_direction='DIAGONAL';wave.inputs['Scale'].default_value=1;links.new(scale.outputs[0],wave.inputs['Vector']);bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.08;bump.inputs['Distance'].default_value=.000018;links.new(wave.outputs['Fac'],bump.inputs['Height']);blend=nodes.new('ShaderNodeMixRGB');links.new(sep.outputs[0],blend.inputs[0]);links.new(old,blend.inputs[1]);links.new(bump.outputs[0],blend.inputs[2]);links.new(blend.outputs[0],bs.inputs['Normal'])
spec=importlib.util.spec_from_file_location('gray','C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py');gray=importlib.util.module_from_spec(spec);spec.loader.exec_module(gray);gray.apply_grayscale(objects);gray.neutral_output(scene)
points=[a.matrix_world@v.co for a in objects for v in a.data.vertices];center=Vector(tuple((min(p[i] for p in points)+max(p[i] for p in points))/2 for i in range(3)));size=(max(p.z for p in points)-min(p.z for p in points))/.8
cd=bpy.data.cameras.new('C45IconCamera');cam=bpy.data.objects.new('C45IconCamera',cd);scene.collection.objects.link(cam);cam.location=center+Vector((2,0,0));cam.rotation_euler=Vector((-1,0,0)).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO';cd.ortho_scale=size;scene.camera=cam
for name,delta,power in [('Key',(1,-.3,1.4),130),('Fill',(1,.9,.45),60),('Rim',(-.8,.4,1),100)]:
    ld=bpy.data.lights.new(name,'AREA');ld.energy=power*size*size;ld.size=size*1.8;lamp=bpy.data.objects.new(name,ld);scene.collection.objects.link(lamp);lamp.location=center+Vector(delta)*size*2;lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
scene.world=bpy.data.worlds.new('IconWorld');scene.world.use_nodes=True;next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND').inputs['Color'].default_value=(.25,.25,.25,1)
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24;scene.cycles.use_denoising=True;scene.render.film_transparent=True;scene.render.resolution_x=scene.render.resolution_y=512;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
key='ue_lmg201_magazine_lmg201_cloth_box';scene.render.filepath=str(OUT/(key+'.png'));bpy.ops.render.render(write_still=True);bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(key+'.blend')))
(O/'icon.json').write_text(json.dumps({'key':key,'file':scene.render.filepath,'purpose':'production gunsmith option icon'},indent=2));print('C45_ICON_SAVED',flush=True)
