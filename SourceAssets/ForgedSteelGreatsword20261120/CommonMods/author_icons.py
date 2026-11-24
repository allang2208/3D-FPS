"""Render physical modules to IconReferences for the workbench card illustrator."""
import math
import runpy
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

here = Path(__file__).resolve().parent
project = here.parents[2]
out = here / 'IconReferences'
out.mkdir(exist_ok=True)
variant = None
if '--executioner-blade' in sys.argv:
    variant = ('ExecutionerBlade', 'ExecutionerBlade', 'executioner_blade')
elif '--hollow-blade' in sys.argv:
    variant = ('LegendaryBladeLiebo', 'HollowBlade', 'hollow_blade')
elif '--ring-chain-pommel' in sys.argv:
    variant = ('RingChainPommel', 'RingChainPommel', 'ring_chain_pommel')
elif '--fishtail-pommel' in sys.argv:
    variant = ('FishtailPommel', 'FishtailPommel', 'fishtail_pommel')
elif '--raven-quill-guard' in sys.argv:
    variant = ('RavenQuillGuard/Art/NestedV4', 'RavenQuillGuard', 'raven_quill_guard')
if variant:
    model_file = here.parent / variant[0] / (variant[1]+'.blend')
else:
    model_file = here.parent / 'Integration/ForgedSteelGreatsword_Modular_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(model_file))
scene = bpy.context.scene
if variant:
    slot = 'guard' if variant[1].endswith('Guard') else 'pommel' if variant[1].endswith('Pommel') else 'blade_1'
    models = {slot: bpy.data.objects['SM_ForgedSteelGreatsword_'+variant[1]]}
else:
    models = {key: bpy.data.objects[f'SM_ForgedSteelGreatsword_{label}_V1']
              for key, label in [('blade_1','Blade'), ('guard','Guard'), ('grip','Grip'), ('pommel','Pommel')]}
for obj in scene.objects:
    obj.hide_render = True
helpers = runpy.run_path(str(Path.home()/'.codex/skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py'))
helpers['apply_grayscale'](list(models.values()))
helpers['neutral_output'](scene)
scene.render.engine = 'CYCLES'
scene.cycles.samples = 20
scene.cycles.use_denoising = True
scene.render.threads_mode = 'FIXED'
scene.render.threads = 4
scene.render.resolution_x = scene.render.resolution_y = 1024 if variant else 512
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.color_mode = 'RGBA'
scene.view_settings.view_transform = 'Standard'
scene.world = bpy.data.worlds.new('Soft studio light')
scene.world.color = (.30,.30,.30)

bpy.ops.object.camera_add(location=(0,-5,0), rotation=(math.pi/2,0,0))
scene.camera = bpy.context.object
scene.camera.data.type = 'ORTHO'
scene.camera.data.ortho_scale = 2
for loc, power, size in [((-2,-3,3),420,3), ((2,-2,1),240,2), ((1,1,2),310,2)]:
    bpy.ops.object.light_add(type='AREA', location=loc)
    light = bpy.context.object
    light.data.energy, light.data.size = power, size
    light.rotation_euler = (-light.location).to_track_quat('-Z','Y').to_euler()

# Use the established frame artwork on the studio backing. The inset supplies a
# continuous dark plate behind the mesh in place of the empty-slot symbol.
bpy.ops.mesh.primitive_plane_add(size=2, location=(0,.35,0), rotation=(math.pi/2,0,0))
plate=bpy.context.object
mat=bpy.data.materials.new('Workbench frame')
mat.use_nodes=True
plate.data.materials.append(mat)
nodes=mat.node_tree.nodes
link=mat.node_tree.links.new
tex=nodes.new('ShaderNodeTexImage')
tex.image=bpy.data.images.load(str(project/'Content/ColdSteelData/AttachmentIcons20260913/blade_2_false.png'))
coord=nodes.new('ShaderNodeTexCoord').outputs['UV']
link(coord,tex.inputs['Vector'])
dist=nodes.new('ShaderNodeVectorMath')
dist.operation='DISTANCE'
link(coord,dist.inputs[0])
dist.inputs[1].default_value=(.5,.5,0)
ramp=nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].position=.29
ramp.color_ramp.elements[1].position=.355
link(dist.outputs['Value'],ramp.inputs[0])
grain=nodes.new('ShaderNodeTexNoise')
grain.inputs['Scale'].default_value=185
link(coord,grain.inputs[0])
shade=nodes.new('ShaderNodeMath')
shade.operation='MULTIPLY_ADD'
link(grain.outputs['Fac'],shade.inputs[0])
shade.inputs[1].default_value=.021
shade.inputs[2].default_value=.010
mix=nodes.new('ShaderNodeMixRGB')
link(ramp.outputs[0],mix.inputs[0])
link(shade.outputs[0],mix.inputs[1])
link(tex.outputs[0],mix.inputs[2])
emit=nodes.new('ShaderNodeEmission')
link(mix.outputs[0],emit.inputs[0])
alpha=nodes.new('ShaderNodeMixShader')
link(tex.outputs['Alpha'],alpha.inputs[0])
link(nodes.new('ShaderNodeBsdfTransparent').outputs[0],alpha.inputs[1])
link(emit.outputs[0],alpha.inputs[2])
plate_output = next(node for node in nodes if node.type == 'OUTPUT_MATERIAL')
link(alpha.outputs[0],plate_output.inputs['Surface'])
plate.visible_diffuse=plate.visible_glossy=False

for key, obj in models.items():
    angle = math.radians(76 if key in ('blade_1','grip') else -8)
    if variant and key=='pommel':
        angle = math.radians(32)
    rot = Matrix.Rotation(math.radians(8),4,'X') @ Matrix.Rotation(angle,4,'Y')
    coords = [rot @ v.co for v in obj.data.vertices]
    lo = Vector(tuple(min(v[i] for v in coords) for i in range(3)))
    hi = Vector(tuple(max(v[i] for v in coords) for i in range(3)))
    scale = (1.15 if key=='pommel' and not variant else 1.40) / max(hi.x-lo.x,hi.z-lo.z)
    obj.matrix_world = Matrix.Translation(-(hi+lo)*(.5*scale)) @ Matrix.Scale(scale,4) @ rot
    obj.hide_render=False
    filename = key+'_'+variant[2]+'.png' if variant else key+'_factory.png'
    scene.render.filepath=str(out/filename)
    bpy.ops.render.render(write_still=True)
    obj.hide_render=True
