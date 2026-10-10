"""Save clean polished quartz on the unchanged pre-wear author geometry."""
import json
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parent
P = json.loads((ROOT/'parameters.json').read_text(encoding='utf-8'))
SOURCE = ROOT.parent/'QuartzOpticsV36/Staff_QuartzOptics_V36.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
bpy.context.preferences.filepaths.save_version = 0
material = bpy.data.materials.new('M_Staff_QuartzPolish_V41')
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
bsdf.inputs['Transmission Weight'].default_value = 1.
links.new(bsdf.outputs['BSDF'],out.inputs['Surface'])
vertex = nodes.new('ShaderNodeVertexColor')
vertex.layer_name = 'QuartzSurface'
channels = nodes.new('ShaderNodeSeparateColor')
links.new(vertex.outputs['Color'],channels.inputs['Color'])
facet = nodes.new('ShaderNodeMapRange')
facet.clamp = True
for key,value in {'From Min':.15,'From Max':.85,'To Min':P['roughness_min'],'To Max':P['roughness_max']}.items():
    facet.inputs[key].default_value = value
links.new(channels.outputs['Red'],facet.inputs['Value'])
roughness = nodes.new('ShaderNodeMixRGB')
roughness.blend_type = 'MIX'
roughness.label = 'Original facets / original narrow bevels'
links.new(channels.outputs['Green'],roughness.inputs[0])
links.new(facet.outputs[0],roughness.inputs[1])
roughness.inputs[2].default_value = (P['bevel_roughness'],)*3+(1.,)
links.new(roughness.outputs[0],bsdf.inputs['Roughness'])
# Normal remains unconnected: use original planar face and smooth bevel normals.
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
    obj['quartz_material_revision'] = 41
    objects.append(obj.name)
bpy.context.scene['quartz_surface_stage'] = 'V41 polished facets; no surface textures; unchanged geometry and V36 optics'
note = bpy.data.texts.new('QuartzPolishV41_README')
note.write('V41 polished-quartz author source. Original geometry and bevels retained.\n'
           'UE uses existing scene lighting/reflections plus material-local SSR.\n'
           'Blender uses its native participating medium; this is not UE visual acceptance.\n'
           'No wear maps, extra lights, internal cards or global renderer changes.\n'
           'No preview rendering or game testing.\n'+json.dumps(P,indent=2))
target = ROOT/'Staff_QuartzPolish_V41.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(target))
(ROOT/'author-receipt.json').write_text(json.dumps(dict(complete=True,source=str(SOURCE),
    blend=str(target),objects=objects,geometry_changed=False,new_textures=0,
    runtime_tested=False,rendered=False),indent=2),encoding='utf-8')
print('STAFF_QUARTZ_V41_AUTHORED geometry_changed=false textures=0 rendered=false',flush=True)
