"""Read only the current SVD magazine materials needed for authoring/import."""
import json
from pathlib import Path
import unreal as u

O = Path(__file__).parent
path = '/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/SK_SVD_ModularStock'
mesh = u.load_asset(path)
slots = {str(s.material_slot_name): s.material_interface.get_path_name() for s in mesh.materials}
mag = u.load_asset(slots['SM_SVD_Magazine_001'])
L = u.MaterialEditingLibrary
base = mag.get_base_material()
parameters = {}
for kind in ('scalar', 'vector', 'texture'):
    values = {}
    for name in getattr(L, 'get_' + kind + '_parameter_names')(base):
        value = getattr(L, 'get_material_instance_' + kind + '_parameter_value')(mag, name)
        values[str(name)] = value.get_path_name() if kind == 'texture' and value else list(value.to_tuple()) if kind == 'vector' else value
    parameters[kind] = values
record = {'mesh': mesh.get_path_name(), 'slots': slots, 'magazine_material': mag.get_path_name(), 'parameters': parameters}
(O / 'source_materials.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print('SVD_EXTMAG_SOURCE ' + json.dumps({'mesh': record['mesh'], 'magazine_material': record['magazine_material'], 'parameters': parameters}))
