"""Bind local source textures on the editable Blender scene (no rendering)."""
import json
from pathlib import Path
import bpy

O = Path(__file__).resolve().parent

def bind():
    g = json.loads((O / 'Original/GLTF/scene.gltf').read_text(encoding='utf-8'))
    mapping = {'sniper': 'M24_Body', 'Scope.002': 'M24_Scope',
        'ScopeGlass.002': 'M24_ScopeGlass', 'Plexiglass.002': 'M24_TopGlass'}

    def image(mat, path, color):
        node = mat.node_tree.nodes.new('ShaderNodeTexImage')
        node.image = bpy.data.images.load(str(path), check_existing=True)
        node.image.colorspace_settings.name = 'sRGB' if color else 'Non-Color'
        return node

    for row in g['materials']:
        mat = bpy.data.materials[mapping[row['name']]]
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        out = nodes.new('ShaderNodeOutputMaterial')
        bs = nodes.new('ShaderNodeBsdfPrincipled')
        links.new(bs.outputs['BSDF'], out.inputs['Surface'])

        def tex(index, color=False):
            uri = g['images'][g['textures'][index]['source']]['uri']
            return image(mat, O / 'Original/GLTF' / uri, color)

        pbr = row['pbrMetallicRoughness']
        col = tex(pbr['baseColorTexture']['index'], True)
        links.new(col.outputs['Color'], bs.inputs['Base Color'])
        orm = tex(pbr['metallicRoughnessTexture']['index'])
        split = nodes.new('ShaderNodeSeparateColor')
        links.new(orm.outputs['Color'], split.inputs['Color'])
        links.new(split.outputs['Green'], bs.inputs['Roughness'])
        links.new(split.outputs['Blue'], bs.inputs['Metallic'])
        normal = tex(row['normalTexture']['index'])
        nmap = nodes.new('ShaderNodeNormalMap')
        links.new(normal.outputs['Color'], nmap.inputs['Color'])
        links.new(nmap.outputs['Normal'], bs.inputs['Normal'])
        trans = row.get('extensions', {}).get('KHR_materials_transmission', {})
        if 'transmissionTexture' in trans:
            tr = tex(trans['transmissionTexture']['index'])
            links.new(tr.outputs['Color'], bs.inputs['Transmission Weight'])
            links.new(col.outputs['Alpha'], bs.inputs['Alpha'])
    mat = bpy.data.materials['M24_SourceArms']
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new('ShaderNodeOutputMaterial')
    bs = nodes.new('ShaderNodeBsdfPrincipled')
    links.new(bs.outputs['BSDF'], out.inputs['Surface'])
    col = image(mat, O / 'Donor/Source/textures/armColor.png', True)
    links.new(col.outputs['Color'], bs.inputs['Base Color'])
    normal = image(mat, O / 'Donor/Source/textures/armNormal.png', False)
    nmap = nodes.new('ShaderNodeNormalMap')
    links.new(normal.outputs['Color'], nmap.inputs['Color'])
    links.new(nmap.outputs['Normal'], bs.inputs['Normal'])
    smooth = image(mat, O / 'Donor/Source/textures/armsmoothness.png', False)
    inv = nodes.new('ShaderNodeMath')
    inv.operation = 'SUBTRACT'
    inv.inputs[0].default_value = 1
    links.new(smooth.outputs['Color'], inv.inputs[1])
    links.new(inv.outputs[0], bs.inputs['Roughness'])

if __name__ == '__main__':
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.open_mainfile(filepath=str(O / 'M24_CustomScope_Native_Editable.blend'), use_scripts=False)
    bind()
    bpy.ops.wm.save_as_mainfile(filepath=str(O / 'M24_CustomScope_Native_Editable.blend'))
