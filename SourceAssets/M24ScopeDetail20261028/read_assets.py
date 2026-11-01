"""Read the live factory optic inputs before authoring its private materials."""
import json
from pathlib import Path
import unreal as u

O = Path(__file__).resolve().parent
MESH = '/Game/Weapons/M24/Surface20261027/SM_M24_m24_custom_scope_6x'
E, L = u.EditorAssetLibrary, u.MaterialEditingLibrary
mesh = u.load_asset(MESH)
if not mesh:
    raise RuntimeError('Missing factory scope: ' + MESH)
result = {'mesh': MESH, 'slots': [], 'materials': {}}
for slot in mesh.static_materials:
    mat = slot.material_interface
    result['slots'].append({'slot': str(slot.material_slot_name), 'material': mat.get_path_name()})
    while mat and mat.get_path_name() not in result['materials']:
        item = {'class': mat.get_class().get_name()}
        result['materials'][mat.get_path_name()] = item
        if isinstance(mat, u.MaterialInstanceConstant):
            item['parent'] = mat.parent.get_path_name()
            item['scalars'] = {str(x.parameter_info.name): x.parameter_value for x in mat.scalar_parameter_values}
            item['textures'] = {str(x.parameter_info.name): x.parameter_value.get_path_name() if x.parameter_value else None for x in mat.texture_parameter_values}
            mat = mat.parent
        else:
            item['expressions'] = [{'class': n.get_class().get_name(), 'description': str(n.get_editor_property('desc'))} for n in L.get_material_expressions(mat)]
            break
(O / 'inputs.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('M24_SCOPE_INPUTS_RECORDED', flush=True)
