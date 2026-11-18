"""Publish the six saved hand refinements without replacing any seat placement."""
import copy
import hashlib
import json
import os
from pathlib import Path
import runpy
import uuid

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ.get('CHAPEL_FURNITURE_OUTPUT', str(ROOT / 'SourceAssets/ChapelFurniture20261116/HandsR2')))
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
data = read(OUT / 'authored.json')
saved = read(OUT / 'assets_saved.json')
if not saved.get('saved') or saved['source_sha256'] != hashlib.sha256((OUT / 'authored.json').read_bytes()).hexdigest():
    raise RuntimeError('Save the fitted native hand revision before publishing.')
helper = runpy.run_path(str(ROOT / 'Tools/PlayerBody/config_transaction.py'))
path = ROOT / 'Content/ColdSteelData/player_body.json'
before = path.read_bytes()
body = json.loads(before.decode('utf-8-sig'))
owned = []
for variant, rig in data['variants'].items():
    node = body if variant == 'default' else body['body_variants'][variant]
    prefix = () if variant == 'default' else ('body_variants', variant)
    if node['body_mesh'] != rig['mesh']:
        raise RuntimeError('Native body changed during hand fitting: ' + variant)
    for phase, take in rig['clips'].items():
        role = 'Rest.ChapelPew.' + phase
        asset = saved['variants'][variant][role]
        if node['clips'].get(role) not in (take['asset'], asset):
            raise RuntimeError('Pew animation changed concurrently: ' + variant + '/' + role)
        if not (ROOT / 'Content' / (asset.split('.')[0][6:] + '.uasset')).is_file():
            raise RuntimeError('Saved hand animation package is missing: ' + asset)
        node['clips'][role] = asset
        node.setdefault('furniture_camera_tracks', {})[role] = saved['camera_tracks'][variant][role]
        owned.extend([prefix + ('clips', role), prefix + ('furniture_camera_tracks', role)])
body_receipt = helper['commit'](path, before, body, owned_paths=owned, producer=__file__)

furniture_path = ROOT / 'Content/ColdSteelData/furniture_rest.json'
with helper['_lock'](ROOT / 'Saved/FurnitureRestConfigWrites/writer.lock'):
    before = furniture_path.read_bytes()
    original = json.loads(before.decode('utf-8-sig'))
    candidate = copy.deepcopy(original)
    for role, track in saved['camera_tracks']['default'].items():
        candidate['clips'][role] = {'duration': track['duration'], 'camera': [p + [0, 0] for p in track['eyes']]}
    changes = list(helper['_changes'](original, candidate))
    text = before.decode('utf-8-sig')
    for key, value in changes:
        if len(key) < 2 or key[0] != 'clips' or key[1] not in saved['camera_tracks']['default']:
            raise RuntimeError('Unowned hand timing field: ' + repr(key))
        text = helper['_set'](text, key, value)
    result = (b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'') + text.encode('utf-8')
    if json.loads(result.decode('utf-8-sig')) != candidate:
        raise RuntimeError('Scoped hand timing serialization differs from candidate.')
    if furniture_path.read_bytes() != before:
        raise RuntimeError('Furniture timing changed during publication; retry from fresh input.')
    if changes:
        backup = OUT / 'furniture_rest.before.json'
        if not backup.exists():
            backup.write_bytes(before)
        temporary = furniture_path.with_name('.chapel-hands-' + uuid.uuid4().hex + '.tmp')
        temporary.write_bytes(result)
        os.replace(temporary, furniture_path)
(OUT / 'publication.json').write_text(json.dumps({'body': body_receipt,
    'furniture_changed_paths': [list(k) for k, _ in changes], 'assets': saved['variants'],
    'runtime_published': True, 'game_tested': False}, indent=2), encoding='utf-8')
print('CHAPEL_RELAXED_HANDS_PUBLISHED', flush=True)
