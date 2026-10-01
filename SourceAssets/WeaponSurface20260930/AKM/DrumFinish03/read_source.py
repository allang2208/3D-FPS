"""Read the production drum inputs needed to author its scoped finish revision."""
import json
from pathlib import Path
import unreal as u

O = Path(__file__).parent
L = u.MaterialEditingLibrary
mesh = u.load_asset('/Game/Weapons/AttachmentFinish20260913/AKM/Meshes/SM_AKM_drum')
out = {'mesh': mesh.get_path_name(), 'slots': [], 'materials': {}}
for slot in mesh.get_editor_property('static_materials'):
    m = slot.material_interface
    out['slots'].append({'slot': str(slot.material_slot_name), 'material': m.get_path_name()})
    base = m.get_base_material()
    if base.get_path_name() in out['materials']:
        continue
    row = {'base': base.get_path_name(), 'nodes': []}
    if isinstance(m, u.MaterialInstance):
        row['scalars'] = {str(v.parameter_info.name): v.parameter_value for v in m.get_editor_property('scalar_parameter_values')}
    for n in L.get_material_expressions(base):
        info = {'name': n.get_name(), 'class': n.get_class().get_name()}
        if isinstance(n, u.MaterialExpressionCustom):
            info['description'] = str(n.get_editor_property('description'))
            info['code'] = n.get_editor_property('code')
        if isinstance(n, u.MaterialExpressionTextureBase):
            tex = n.get_editor_property('texture')
            info['texture'] = tex.get_path_name() if tex else None
        row['nodes'].append(info)
    out['materials'][base.get_path_name()] = row
out['pie'] = bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()) if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() else False
(O / 'source.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
print('WEAPON_SURFACE_AKM_DRUM_SOURCE', json.dumps({'slots': out['slots'], 'pie': out['pie']}), flush=True)
