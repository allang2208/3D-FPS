"""Read the material assignments needed to repair the reported treasure rendering."""
import json
from pathlib import Path
import unreal as u
ROOT='/Game/Props/GamedevTreasureChest20260922'
mesh=u.load_asset(ROOT+'/SK_GamedevTreasureChest')
record={'mesh':mesh.get_path_name(),'materials':[]}
for slot in mesh.get_editor_property('materials'):
    material=slot.get_editor_property('material_interface')
    record['materials'].append({'slot':str(slot.get_editor_property('material_slot_name')),
        'material':material.get_path_name() if material else None,
        'skeletal_usage':material.get_editor_property('used_with_skeletal_mesh') if material else None})
Path(__file__).with_name('asset_inputs.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('TREASURE_REPAIR_INPUTS '+json.dumps(record))
