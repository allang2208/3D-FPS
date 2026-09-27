"""Read the staff's actual native rig and its existing M4 outfit derivatives."""
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
SOURCE = '/Game/Characters/ModularOutfit20260924/BarePalmV7/M4/SK_M4_BareArmsV7.SK_M4_BareArmsV7'
config = json.loads((PROJECT / 'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
paths = {SOURCE}
for item in config['items'].values():
    for field in ('rig_meshes', 'skin_meshes'):
        path = item.get(field, {}).get('M4')
        if path:
            paths.add(path)
result = {'source': SOURCE, 'profile_registered': SOURCE in config['profiles'], 'meshes': []}
for path in sorted(paths):
    mesh = u.load_asset(path)
    if not mesh:
        raise RuntimeError('Missing outfit source: ' + path)
    result['meshes'].append({
        'path': mesh.get_path_name(),
        'skeleton': mesh.get_editor_property('skeleton').get_path_name(),
        'materials': [str(m.material_slot_name) for m in mesh.get_editor_property('materials')],
    })
(ROOT / 'outfit-source-inspection.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('STAFF_OUTFIT_SOURCE ' + json.dumps(result))
