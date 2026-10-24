"""Snapshot the saved male equipment recipes for Kaitlin's authored derivatives."""
import hashlib
import json
from pathlib import Path

PROJECT = Path('D:/FPS3D/FPSGAME')
WORK = PROJECT / 'SourceAssets/KaitlinPlayer20261023/FitInputs'
WORK.mkdir(parents=True, exist_ok=True)
recipes = {}
for name in ('player_body', 'modular_outfits'):
    raw = (PROJECT / ('Content/ColdSteelData/' + name + '.json')).read_bytes()
    recipes[name] = json.loads(raw.decode('utf-8-sig'))
    (WORK / (name + '.json')).write_bytes(raw)

meshes = {}


def record(path, selector, role):
    # Actual asset type is read by the UE extraction stage. Keep original names
    # and selectors so shared source meshes are extracted once and fitted once.
    name = path.rsplit('/', 1)[-1]
    if not name.startswith(('SK_', 'SKM_')):
        return
    row = meshes.setdefault(path, {'source': path, 'roles': [], 'selectors': [],
                                   'file': hashlib.sha256(path.encode()).hexdigest()[:20] + '.json'})
    if role not in row['roles']:
        row['roles'].append(role)
    row['selectors'].append(selector)


def visit(value, selector, role):
    if isinstance(value, dict):
        for key, child in value.items():
            if key != 'body_variants':
                visit(child, selector + [key], role)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            visit(child, selector + [index], role)
    elif isinstance(value, str) and value.startswith('/Game/'):
        record(value, selector, role)


body = recipes['player_body']
modular = recipes['modular_outfits']
record(body['body_mesh'], ['player_body', 'body_mesh'], 'world_body')
visit(body.get('heads', {}), ['player_body', 'heads'], 'head_source')
for key, recipe in modular['items'].items():
    visit(recipe, ['modular_outfits', 'items', key], 'garment')
for path, recipe in modular['profiles'].items():
    record(path, ['modular_outfits', 'profiles', path], 'pose_source')
    visit(recipe, ['modular_outfits', 'profiles', path], 'skin_or_profile_part')
visit(body['outfits'], ['player_body', 'outfits'], 'backpack')
visit(body['head_equipment'], ['player_body', 'head_equipment'], 'headwear')
def priority(row):
    if 'world_body' in row['roles']:
        return 0
    if 'Jason' in row['source'] and 'skin_or_profile_part' in row['roles']:
        return 1
    if 'Jason' in row['source'] and 'garment' in row['roles']:
        return 2
    return 3


manifest = {'status': 'source_inventory_only', 'meshes': sorted(meshes.values(), key=priority),
            'source_config_sha256': {name: hashlib.sha256((WORK / (name + '.json')).read_bytes()).hexdigest()
                                     for name in recipes},
            'animation_mappings': body['clips']}
(WORK / 'inventory.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print('KAITLIN_FIT_INPUT_INVENTORY', len(meshes), 'mesh inputs;', len(body['clips']), 'animation mappings')
