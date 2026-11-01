"""Read the three active advanced-chassis assemblies before material authoring."""
import unreal as u, json, hashlib
from pathlib import Path
O = Path(__file__).resolve().parent
L = u.MaterialEditingLibrary
paths = {
    'standard': '/Game/Weapons/M24/AdvancedAction20261029/Meshes/SM_M24_m24_advanced_action',
    'skeleton_front': '/Game/Weapons/M24/ReceiverGripRebuild20261031/Meshes/SM_M24_AdvancedFront_ForIndependentGrip',
    'skeleton_seat': '/Game/Weapons/M24/ReceiverGripRebuild20261031/Meshes/SM_M24_ReceiverStock_Advanced',
}
R = {'assets': {}, 'materials': {}}
def digest(a):
    p = Path(u.Paths.project_content_dir()) / (a.get_path_name().split('.')[0].removeprefix('/Game/') + '.uasset')
    return hashlib.sha256(p.read_bytes()).hexdigest()
for key, path in paths.items():
    mesh = u.load_asset(path)
    if not mesh: raise RuntimeError('Missing ' + path)
    row = {'path': path, 'sha256': digest(mesh), 'slots': []}
    for slot in mesh.static_materials:
        mat = slot.material_interface
        row['slots'].append({'slot': str(slot.material_slot_name), 'material': mat.get_path_name()})
        if mat.get_path_name() in R['materials']: continue
        base = mat.get_base_material()
        data = {'parent': mat.get_editor_property('parent').get_path_name(), 'master': base.get_path_name(), 'sha256': digest(mat), 'parameters': {}, 'codes': []}
        for kind in ('scalar', 'vector', 'texture'):
            values = {}
            for name in getattr(L, 'get_' + kind + '_parameter_names')(base):
                value = getattr(L, 'get_material_instance_' + kind + '_parameter_value')(mat, name)
                values[str(name)] = value.get_path_name() if isinstance(value, u.Object) else [value.r, value.g, value.b, value.a] if isinstance(value, u.LinearColor) else value
            data['parameters'][kind] = values
        for node in L.get_material_expressions(base):
            if isinstance(node, u.MaterialExpressionCustom):
                data['codes'].append({'description': str(node.get_editor_property('description')), 'code': node.get_editor_property('code')})
        R['materials'][mat.get_path_name()] = data
    R['assets'][key] = row
(O / 'inputs.json').write_text(json.dumps(R, indent=2), encoding='utf-8')
print('M24_ADVANCED_FINISH_INPUTS', len(R['assets']), len(R['materials']), flush=True)
