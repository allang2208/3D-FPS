"""Independent-process read-back of the furnace's palette entry.

    & UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this> -unattended -nop4 -nosplash

An empty FName reads back as ``Name("None")`` whose ``str()`` is ``"None"``, so
the material is reported through both ``str()`` and ``is_none()``.
"""
import json
from pathlib import Path

import unreal as u

HERE = Path(__file__).resolve().parent
palette = u.load_asset('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette')
found = None
for item in palette.get_editor_property('components'):
    if str(item.get_editor_property('id')) == 'blast_furnace':
        found = item
        break
if found is None:
    raise SystemExit('entry missing')

material = found.get_editor_property('material')
mesh = found.get_editor_property('mesh')
footprint = found.get_editor_property('footprint')
report = {
    'material_str': str(material),
    'material_repr': repr(material),
    'material_is_none': bool(material.is_none()) if hasattr(material, 'is_none') else None,
    'classified_into_other_tab': bool(material.is_none()) if hasattr(material, 'is_none') else None,
    'mesh': mesh.get_path_name() if mesh else None,
    'footprint': [footprint.x, footprint.y, footprint.z],
    'palette_entries': len(palette.get_editor_property('components')),
}
(HERE / 'drawer-verify.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('BLAST_FURNACE_DRAWER_VERIFY ' + json.dumps(report, ensure_ascii=False), flush=True)
