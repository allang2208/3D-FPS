"""Append newly published equipment without replacing the captured outfit revision."""
import hashlib
import json
from pathlib import Path

PROJECT = Path('D:/FPS3D/FPSGAME')
WORK = PROJECT / 'SourceAssets/KaitlinPlayer20261023'
INPUT = WORK / 'FitInputs'
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
current = read(PROJECT / 'Content/ColdSteelData/player_body.json')
snapshot = read(INPUT / 'player_body.json')
inventory = read(INPUT / 'inventory.json')
known = {row['source'] for row in inventory['meshes']}
added = []


def collect(value, selector):
    if isinstance(value, dict):
        for key, child in value.items():
            collect(child, selector + [key])
    elif isinstance(value, str) and value.startswith('/Game/') and value.rsplit('/', 1)[-1].startswith(('SK_', 'SKM_')):
        if value in known:
            return
        known.add(value)
        added.append(value)
        inventory['meshes'].append({'source': value, 'roles': ['backpack'], 'selectors': [selector],
                                    'file': hashlib.sha256(value.encode()).hexdigest()[:20] + '.json'})


for item, recipe in current['outfits'].items():
    if item not in snapshot['outfits']:
        snapshot['outfits'][item] = recipe
        collect(recipe, ['player_body', 'outfits', item])
snapshot['head_equipment'] = current['head_equipment']
snapshot['clips'] = current['clips']
inventory['animation_mappings'] = current['clips']
(INPUT / 'player_body.json').write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding='utf-8')
inventory['source_config_sha256']['player_body'] = hashlib.sha256((INPUT / 'player_body.json').read_bytes()).hexdigest()
(INPUT / 'inventory.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding='utf-8')
if added:
    (INPUT / 'extra_equipment_pending.json').write_text(json.dumps({'sources': added}, indent=2), encoding='utf-8')
print('KAITLIN_ADDED_EQUIPMENT', len(added), 'meshes;', len(snapshot['head_equipment']), 'headpieces', flush=True)
