"""Read the owned material graph for authoring; no asset mutation or playback."""
import json
from pathlib import Path
import unreal

lib = unreal.MaterialEditingLibrary
root = Path(unreal.Paths.project_dir()) / 'SourceAssets/FireballSlowBurn20260914'
root.mkdir(parents=True, exist_ok=True)
mat = unreal.load_asset('/Game/NiagaraExamples/Materials/MasterMaterials/M_SmokeAndFire_Sprites')
nodes = []
for node in lib.get_material_expressions(mat):
    item = {'name': node.get_name(), 'class': node.get_class().get_name(),
            'inputs': [n.get_name() if n else None for n in lib.get_inputs_for_material_expression(mat, node)]}
    for prop in ['parameter_name', 'texture', 'function', 'material_function', 'r', 'g', 'b', 'a', 'default_value', 'code']:
        try:
            item[prop] = str(node.get_editor_property(prop))
        except Exception:
            pass
    nodes.append(item)
outputs = {}
for prop in [unreal.MaterialProperty.MP_EMISSIVE_COLOR, unreal.MaterialProperty.MP_OPACITY]:
    node = lib.get_material_property_input_node(mat, prop)
    outputs[str(prop)] = {'node': node.get_name() if node else None,
                          'pin': lib.get_material_property_input_node_output_name(mat, prop)}
(root / 'material-source.json').write_text(json.dumps({'blend': str(mat.get_editor_property('blend_mode')),
    'outputs': outputs, 'nodes': nodes}, indent=2), encoding='utf-8')
unreal.log('FIREBALL_SLOW_BURN_MATERIAL_SOURCE_READ')
