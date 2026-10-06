"""Keep editable material identities in sync; never change geometry or UVs."""
import json
from pathlib import Path

S = Path(__file__).resolve().parent.parent
REFERENCE = json.loads((S / 'RSH12Optics20261004/finish_reference.json').read_text())


def foregrip_materials(ob):
    for material in ob.data.materials:
        if not material or not material.name.startswith(('RSH_Foregrip_Insert', 'M_M4_prism_1', 'Resonance_Metal_M4')):
            continue
        material.use_nodes = True
        nodes, links = material.node_tree.nodes, material.node_tree.links
        shader = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if not shader:
            shader = nodes.new('ShaderNodeBsdfPrincipled')
            output = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None) or nodes.new('ShaderNodeOutputMaterial')
            links.new(shader.outputs['BSDF'], output.inputs['Surface'])
        for name, value in [('Base Color', (*REFERENCE['base_color'], 1.)),
                            ('Roughness', REFERENCE['roughness'][0]), ('Metallic', 1.)]:
            socket = shader.inputs[name]
            for link in list(socket.links):
                links.remove(link)
            socket.default_value = value
        material.diffuse_color = (*REFERENCE['base_color'], 1.)
        material['RSHMaterialFinish'] = 'RSH rail metal; production micrograin/wet layer in UE private material'
