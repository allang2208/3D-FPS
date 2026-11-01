"""Read the installed optic sockets and slot contract for physical-lens authoring."""
import json
from pathlib import Path
import unreal as u

out = Path(__file__).resolve().parent
mesh = u.load_asset('/Game/Weapons/M24/Surface20261027/SM_M24_m24_custom_scope_6x')
result = {'mesh': mesh.get_path_name(), 'slots': [], 'sockets': {}}
for s in mesh.static_materials:
    result['slots'].append({'name': str(s.material_slot_name), 'material': s.material_interface.get_path_name()})
for name in ('SightRear', 'SightFront', 'SightUp', 'TopSightRear'):
    s = mesh.find_socket(name)
    if s:
        p = s.relative_location
        result['sockets'][name] = [p.x, p.y, p.z]
result['worlds'] = [str(w.world_type) for w in u.get_editor_subsystem(u.UnrealEditorSubsystem).get_all_worlds()] if hasattr(u.UnrealEditorSubsystem, 'get_all_worlds') else []
(out / 'inputs.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('M24_PHYSICAL_SCOPE_INPUTS', json.dumps(result), flush=True)
