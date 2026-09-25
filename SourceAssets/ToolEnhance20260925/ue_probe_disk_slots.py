# Read-only probe: report the ON-DISK slot materials of both tool viewmodels and
# both world meshes, straight from a fresh commandlet process. Writes JSON in a
# finally block; per-asset failures are recorded, not raised.
import json
from pathlib import Path

import unreal as u

OUT = Path(u.Paths.project_dir()).resolve() / 'Saved/Production/tool-enhance-disk-slots.json'
report = {}
try:
    for tag, path in (('SK_Axe', '/Game/Items/ProductionTools/GripMotion20260913/SK_Harvest_Axe'),
                      ('SK_Pick', '/Game/Items/ProductionTools/RusticPickaxe20260919/SK_RusticPickaxe'),
                      ('SM_Axe', '/Game/Items/ProductionTools/BattleAxe20260919/SM_BattleAxe'),
                      ('SM_Pick', '/Game/Items/ProductionTools/RusticPickaxe20260919/SM_RusticPickaxe')):
        try:
            asset = u.load_asset(path)
            if asset is None:
                report[tag] = {'missing': True}
                continue
            if hasattr(asset, 'static_materials'):
                slots = asset.static_materials
            else:
                slots = asset.get_editor_property('materials')
            report[tag] = [(str(s.material_slot_name),
                            s.material_interface.get_path_name() if s.material_interface else None)
                           for s in slots]
        except Exception as exc:
            report[tag] = {'error': str(exc)}
finally:
    OUT.write_text(json.dumps(report, indent=1), encoding='utf-8')
