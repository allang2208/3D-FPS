"""Read the saved M870 material identities used by the world weapon copy."""
import json
from pathlib import Path
import unreal as u

path = '/Game/Weapons/M870/Tactical20261015/SK_M870_V7'
mesh = u.load_asset(path)
if not mesh:
    raise RuntimeError('Cannot load ' + path)
rows = []
for index, slot in enumerate(mesh.materials):
    material = slot.material_interface
    rows.append({
        'index': index,
        'slot': str(slot.material_slot_name),
        'imported_slot': str(slot.get_editor_property('imported_material_slot_name')),
        'material': material.get_path_name() if material else None,
    })
report = {'mesh': mesh.get_path_name(), 'materials': rows, 'assets_modified': False}
(Path(__file__).parent / 'material_slots.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('M870_MATERIAL_SLOTS ' + json.dumps(report), flush=True)
