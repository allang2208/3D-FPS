"""Update only the quartz material in the active model and V28 animation sources."""
import json
import runpy
import shutil
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parent
bpy.context.preferences.filepaths.save_version = 0
targets = [ROOT.parent / 'BarkRebuildV21/Staff_NaturalBark_V21.blend',
           ROOT.parent / 'PrimaryWholeArmV28/Staff_PrimarySmash_V28.blend']
before = ROOT / 'Before'
before.mkdir(parents=True, exist_ok=True)
saved = []
for path in targets:
    backup = before / path.name
    if not backup.exists():
        shutil.copy2(path, backup)
    bpy.ops.wm.open_mainfile(filepath=str(path))
    bpy.context.preferences.filepaths.save_version = 0
    old = [m for m in bpy.data.materials if m.name.startswith(('M_Staff_QuartzDenseV22', 'M_Staff_QuartzMilkV20'))]
    new = runpy.run_path(str(ROOT.parent / 'QuartzAimV22/blender_quartz_material.py'))['create_quartz_material']()
    for material in old:
        if material != new:
            material.user_remap(new)
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    saved.append(str(path))
(ROOT / 'editable-receipt.json').write_text(json.dumps({'saved': saved, 'rendered': False}, indent=2), encoding='utf-8')
print('STAFF_QUARTZ_EDITABLE_SAVED ' + json.dumps(saved))
