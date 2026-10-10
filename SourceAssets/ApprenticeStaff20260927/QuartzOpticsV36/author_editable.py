"""Save a V36 editable material source on the unchanged V35 staff geometry.

Blender uses native participating volume; the realtime UE counterpart uses the
mesh-derived finite-chord approximation. This is authoring, not preview rendering.
"""
import json
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parent
P = json.loads((ROOT/'parameters.json').read_text(encoding='utf-8'))
SOURCE = ROOT.parent/'QuartzSurfaceV35/Staff_QuartzSurface_V35.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
bpy.context.preferences.filepaths.save_version = 0
material = bpy.data.materials.new('M_Staff_QuartzOptics_V36')
material.use_nodes = True
material['ue_material_recipe'] = str(ROOT/'ue_material.py')
material['optical_units'] = 'UE author centimetres; density is per author unit'
nodes = material.node_tree.nodes
nodes.clear()
links = material.node_tree.links
out = nodes.new('ShaderNodeOutputMaterial')
bsdf = nodes.new('ShaderNodeBsdfPrincipled')
bsdf.inputs['Base Color'].default_value = (1,1,1,1)
bsdf.inputs['IOR'].default_value = P['ior']
bsdf.inputs['Transmission Weight'].default_value = 1
links.new(bsdf.outputs['BSDF'],out.inputs['Surface'])
vertex = nodes.new('ShaderNodeVertexColor')
vertex.layer_name = 'QuartzSurface'
channels = nodes.new('ShaderNodeSeparateColor')
links.new(vertex.outputs['Color'],channels.inputs['Color'])
rough = nodes.new('ShaderNodeMath')
rough.operation = 'MULTIPLY_ADD'
rough.inputs[1].default_value = P['roughness_max']-P['roughness_min']
rough.inputs[2].default_value = P['roughness_min']
links.new(channels.outputs['Red'],rough.inputs[0])
mask = nodes.new('ShaderNodeTexImage')
mask.image = bpy.data.images['T_QuartzSurface_Masks_V35']
mask_split = nodes.new('ShaderNodeSeparateColor')
links.new(mask.outputs['Color'],mask_split.inputs['Color'])
for signal, key in ((mask_split.outputs['Red'],'roughness_growth_add'),
                    (mask_split.outputs['Green'],'roughness_pit_add'),
                    (channels.outputs['Green'],'roughness_bevel_add')):
    addition = nodes.new('ShaderNodeMath')
    addition.operation = 'MULTIPLY_ADD'
    addition.inputs[1].default_value = P[key]
    links.new(signal,addition.inputs[0])
    links.new(rough.outputs[0],addition.inputs[2])
    rough = addition
links.new(rough.outputs[0],bsdf.inputs['Roughness'])
tex = nodes.new('ShaderNodeTexImage')
tex.image = bpy.data.images['T_QuartzSurface_Normal_V35']
normal = nodes.new('ShaderNodeNormalMap')
normal.inputs['Strength'].default_value = P['surface_normal_strength']
links.new(tex.outputs['Color'],normal.inputs['Color'])
links.new(normal.outputs['Normal'],bsdf.inputs['Normal'])

absorption = [s*(1-a) for s,a in zip(P['extinction_per_cm'],P['medium_albedo'])]
scattering = [s*a for s,a in zip(P['extinction_per_cm'],P['medium_albedo'])]
absorb = nodes.new('ShaderNodeVolumeAbsorption')
absorb.inputs['Color'].default_value = (*[1-s/max(absorption) for s in absorption],1)
absorb.inputs['Density'].default_value = max(absorption)
scatter = nodes.new('ShaderNodeVolumeScatter')
scatter.inputs['Color'].default_value = (*[s/max(scattering) for s in scattering],1)
scatter.inputs['Density'].default_value = max(scattering)
scatter.inputs['Anisotropy'].default_value = 0
volume = nodes.new('ShaderNodeAddShader')
links.new(absorb.outputs[0],volume.inputs[0])
links.new(scatter.outputs[0],volume.inputs[1])
links.new(volume.outputs[0],out.inputs['Volume'])
objects = []
for obj in bpy.data.objects:
    if obj.type != 'MESH' or not obj.name.startswith('SM_Staff_'):
        continue
    for slot in obj.material_slots:
        if slot.material and slot.material.name.startswith('M_Staff_Quartz'):
            slot.material = material
    obj['quartz_material_revision'] = 36
    objects.append(obj.name)
bpy.context.scene['quartz_surface_stage'] = 'V36 finite absorption / clean facets, unchanged V35 geometry'
note = bpy.data.texts.new('QuartzOpticsV36_README')
note.write('V36 material author source. Geometry and V35 bevels unchanged.\n'
           'UE: ue_material.py + mesh-derived OpticalChord.hlsl are authoritative.\n'
           'Blender: native absorption/scatter volume, no runtime G-key light.\n'
           'No preview render or game test performed.\n'+json.dumps(P,indent=2))
target = ROOT/'Staff_QuartzOptics_V36.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(target))
(ROOT/'author-receipt.json').write_text(json.dumps(dict(complete=True,source=str(SOURCE),
    blend=str(target),objects=objects,geometry_changed=False,runtime_tested=False,rendered=False),indent=2),encoding='utf-8')
print('STAFF_QUARTZ_V36_EDITABLE_SAVED geometry_changed=false rendered=false',flush=True)
