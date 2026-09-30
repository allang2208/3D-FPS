"""Production attachment icon from the actual drum; no acceptance renders."""
import bpy,json,importlib.util
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'LMG201_Drum46.blend'),use_scripts=False);bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;obj=bpy.data.objects['SM_LMG201_LargeDrum'];G=json.loads((O/'geometry_inputs.json').read_text())
root_to_mag=Matrix(G['mag_blender']).inverted()@Matrix(G['root_blender']);obj.data.transform(root_to_mag.inverted())
textures=O.parents[1]/'LargeDrumUpgrade20260920/AKM/Textures'
for slot in obj.material_slots:
 m=slot.material;n=m.node_tree.nodes;l=m.node_tree.links;bs=next(v for v in n if v.type=='BSDF_PRINCIPLED');metal='Fasteners' in m.name or 'FactoryNeck' in m.name
 if any(x in m.name for x in ['DrumPolymer','DrumIndex','DrumFasteners']):
  bc=n.new('ShaderNodeTexImage');bc.image=bpy.data.images.load(str(textures/'T_AKM_Drum_BaseColor.png'),check_existing=True)
  lumin=n.new('ShaderNodeRGBToBW');l.new(bc.outputs['Color'],lumin.inputs[0]);factor=n.new('ShaderNodeMath');factor.operation='DIVIDE';factor.inputs[1].default_value=.013;l.new(lumin.outputs[0],factor.inputs[0])
  tint=n.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1;tint.inputs[1].default_value=(.0175,.021,.0255,1) if metal else (.010,.013,.016,1);l.new(factor.outputs[0],tint.inputs[2]);l.new(tint.outputs[0],bs.inputs['Base Color'])
  nt=n.new('ShaderNodeTexImage');nt.image=bpy.data.images.load(str(textures/'T_AKM_Drum_Normal.png'),check_existing=True);nt.image.colorspace_settings.name='Non-Color';nm=n.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.55;l.new(nt.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs['Normal'],bs.inputs['Normal'])
 bs.inputs['Roughness'].default_value=.385 if metal else .46;bs.inputs['Metallic'].default_value=.68 if metal else 0.
spec=importlib.util.spec_from_file_location('gray','C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py');gray=importlib.util.module_from_spec(spec);spec.loader.exec_module(gray);gray.apply_grayscale([obj]);gray.neutral_output(scene)
pts=[obj.matrix_world@v.co for v in obj.data.vertices];center=Vector(tuple((min(p[i] for p in pts)+max(p[i] for p in pts))/2 for i in range(3)));extent=max(max(p.y for p in pts)-min(p.y for p in pts),max(p.z for p in pts)-min(p.z for p in pts))/.80
# +X camera makes the gun's -Y muzzle direction point left, with a level horizon.
data=bpy.data.cameras.new('D46_IconCamera');cam=bpy.data.objects.new('D46_IconCamera',data);scene.collection.objects.link(cam);cam.location=center+Vector((2,0,0));cam.rotation_euler=Vector((-1,0,0)).to_track_quat('-Z','Y').to_euler();data.type='ORTHO';data.ortho_scale=extent;scene.camera=cam
for name,delta,power in [('Key',(1,-.3,1.4),155),('Fill',(1,.9,.45),72),('Rim',(-.8,.4,1),105)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=power*extent*extent;d.size=extent*1.8;lamp=bpy.data.objects.new(name,d);scene.collection.objects.link(lamp);lamp.location=center+Vector(delta)*extent*2;lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
scene.world=bpy.data.worlds.new('D46IconWorld');scene.world.use_nodes=True;next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND').inputs['Color'].default_value=(.25,.25,.25,1)
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=32;scene.cycles.use_denoising=True;scene.render.film_transparent=True;scene.render.resolution_x=scene.render.resolution_y=512;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
folder=O/'Icons';folder.mkdir(exist_ok=True);key='ue_lmg201_magazine_large_drum';scene.render.filepath=str(folder/(key+'.png'));bpy.ops.render.render(write_still=True);bpy.ops.wm.save_as_mainfile(filepath=str(folder/(key+'.blend')))
(O/'icon.json').write_text(json.dumps({'key':key,'file':scene.render.filepath,'purpose':'production gunsmith attachment icon; actual mesh, neutral grayscale, alpha'},indent=2));print('DRUM46_ICON_SAVED',flush=True)
