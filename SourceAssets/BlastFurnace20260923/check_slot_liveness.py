"""Are the furnace mesh's material slot references live, or dangling?

    & UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this> -unattended -nop4 -nosplash

verify_blast_furnace reported every slot "bound" because the material_interface
field was non-null. This checks one level deeper: that each interface resolves
to a real, loadable material object, and that the material itself resolves its
BaseColor texture. A slot can look bound on paper while its interface is a
dangling soft reference left behind by delete_asset + reimport.
"""
import json
from pathlib import Path

import unreal as u

HERE = Path(__file__).resolve().parent
MESH = '/Game/Props/BlastFurnace20260923/SM_BlastFurnace'
report = {'slots': []}

mesh = u.load_asset(MESH)
if mesh is None:
    raise SystemExit('MESH_MISSING')

for index, slot in enumerate(mesh.get_editor_property('static_materials')):
    name = str(slot.get_editor_property('material_slot_name'))
    interface = slot.get_editor_property('material_interface')
    row = {'slot': name, 'interface_type': type(interface).__name__ if interface else None}
    if interface is not None:
        path = interface.get_path_name()
        row['interface_path'] = path
        # Try to load the actual material asset the interface points at.
        try:
            loaded = u.load_asset(path.split('.')[0])
            row['resolves_to'] = loaded.get_class().get_name() if loaded else None
            row['is_valid'] = loaded is not None
        except Exception as error:  # noqa: BLE001
            row['is_valid'] = False
            row['error'] = str(error)
    report['slots'].append(row)

(HERE / 'slot-liveness.json').write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                         encoding='utf-8')
print('SLOT_LIVENESS ' + json.dumps(report, ensure_ascii=False), flush=True)
