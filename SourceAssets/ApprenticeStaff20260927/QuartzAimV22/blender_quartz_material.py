"""Matching editable quartz surface; no internal veil meshes."""
import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
P=json.loads((ROOT/'quartz_parameters.json').read_text())
def create_quartz_material():
    m=bpy.data.materials.get(P['material']) or bpy.data.materials.new(P['material']);m.use_nodes=True
    m.diffuse_color=(*P['base_color'],1)
    n=m.node_tree.nodes;n.clear();links=m.node_tree.links
    bs=n.new('ShaderNodeBsdfPrincipled');out=n.new('ShaderNodeOutputMaterial');links.new(bs.outputs[0],out.inputs['Surface'])
    bs.inputs['Base Color'].default_value=(*P['base_color'],1);bs.inputs['IOR'].default_value=P['ior']
    coords=n.new('ShaderNodeTexCoord');scale=n.new('ShaderNodeVectorMath');scale.operation='MULTIPLY';scale.inputs[1].default_value=P['local_cloud_frequency']
    links.new(coords.outputs['Object'],scale.inputs[0]);noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=1.;noise.inputs['Detail'].default_value=1.
    links.new(scale.outputs['Vector'],noise.inputs['Vector'])
    for name,lo,hi in [('Roughness',P['roughness_min'],P['roughness_max']),('Transmission Weight',P['blender_transmission_clear'],P['blender_transmission_cloudy'])]:
        math=n.new('ShaderNodeMath');math.operation='MULTIPLY_ADD';math.inputs[1].default_value=hi-lo;math.inputs[2].default_value=lo
        links.new(noise.outputs['Fac'],math.inputs[0]);links.new(math.outputs[0],bs.inputs[name])
    return m
