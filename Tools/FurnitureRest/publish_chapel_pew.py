"""Publish only chapel pew slots, saved native roles and matching eye tracks."""
import copy
import hashlib
import json
import os
from pathlib import Path
import runpy
import uuid

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/ChapelFurniture20261116'
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
authored = read(OUT / 'authored.json')
saved = read(OUT / 'assets_saved.json')
if not saved.get('saved') or saved['source_sha256'] != hashlib.sha256((OUT / 'authored.json').read_bytes()).hexdigest():
    raise RuntimeError('Save the current native pew animations before publication.')
helper = runpy.run_path(str(ROOT / 'Tools/PlayerBody/config_transaction.py'))
path = ROOT / 'Content/ColdSteelData/player_body.json'
before = path.read_bytes()
body = json.loads(before.decode('utf-8-sig'))
owned = []
for variant, rig in authored['variants'].items():
    node = body if variant == 'default' else body['body_variants'][variant]
    prefix = () if variant == 'default' else ('body_variants', variant)
    if rig['mesh'] != node['body_mesh']:
        raise RuntimeError('Body mesh changed during pew authoring: ' + variant)
    for phase, take in rig['clips'].items():
        role = 'Rest.ChapelPew.' + phase
        asset = saved['variants'][variant][role]
        if node['clips']['Rest.Chair55.' + phase] != take['asset']:
            raise RuntimeError('Source chair role changed: ' + variant + '/' + phase)
        if node['clips'].get(role, asset) != asset:
            raise RuntimeError('Pew role already belongs to another revision: ' + role)
        if not (ROOT / 'Content' / (asset.split('.')[0][6:] + '.uasset')).is_file():
            raise RuntimeError('Saved pew asset is missing: ' + asset)
        node['clips'][role] = asset
        node.setdefault('furniture_camera_tracks', {})[role] = saved['camera_tracks'][variant][role]
        owned.extend([prefix + ('clips', role), prefix + ('furniture_camera_tracks', role)])
body_receipt = helper['commit'](path, before, body, owned_paths=owned, producer=__file__)

furniture_path = ROOT / 'Content/ColdSteelData/furniture_rest.json'
mesh = '/Game/WorldGeneration/TemperateHills/OldChapel/Meshes/SM_ChapelPew.SM_ChapelPew'
height = authored['surface_height']
profile = {'mesh': mesh, 'caption': '教堂长椅', 'scale': [1.25, 1.25, 1.25],
           'auto_select_free_slot': True, 'slots': [
               {'kind': 'ChapelPew', 'seat': [-18, y, height / 1.25],
                'focus': [-8, y, height / 1.25], 'yaw': 180, 'label': label}
               for y, label in ((-70, '左座'), (0, '中座'), (70, '右座'))]}
with helper['_lock'](ROOT / 'Saved/FurnitureRestConfigWrites/writer.lock'):
    original_bytes = furniture_path.read_bytes()
    original = json.loads(original_bytes.decode('utf-8-sig'))
    candidate = copy.deepcopy(original)
    candidate['types']['ChapelPew'] = {'lying': False, 'surface_height': height,
                                     'entry_offset': [0, 70, 0], 'entry_yaw': 0}
    for phase in ('Enter', 'Idle', 'Exit'):
        role = 'Rest.ChapelPew.' + phase
        track = saved['camera_tracks']['default'][role]
        candidate['clips'][role] = {'duration': track['duration'],
                                    'camera': [p + [0, 0] for p in track['eyes']]}
    profiles = candidate['furniture']
    existing = next((i for i, p in enumerate(profiles) if p['mesh'] == mesh), None)
    if existing is None:
        profiles.append(profile)
    else:
        profiles[existing] = profile
    changes = list(helper['_changes'](original, candidate))
    text = original_bytes.decode('utf-8-sig')
    for key, value in changes:
        if key != ('furniture',) and key[:2] != ('types', 'ChapelPew') and not (
                len(key) > 1 and key[0] == 'clips' and key[1].startswith('Rest.ChapelPew.')):
            raise RuntimeError('Unowned pew configuration path: ' + repr(key))
        text = helper['_set'](text, key, value)
    result = (b'\xef\xbb\xbf' if original_bytes.startswith(b'\xef\xbb\xbf') else b'') + text.encode('utf-8')
    if json.loads(result.decode('utf-8-sig')) != candidate:
        raise RuntimeError('Furniture serialization differs from the intended pew profile.')
    if furniture_path.read_bytes() != original_bytes:
        raise RuntimeError('Furniture configuration changed; publish again from fresh data.')
    backup = OUT / 'furniture_rest.before.json'
    if not backup.exists():
        backup.write_bytes(original_bytes)
    temporary = furniture_path.with_name('.chapel-pew-' + uuid.uuid4().hex + '.tmp')
    temporary.write_bytes(result)
    os.replace(temporary, furniture_path)
(OUT / 'publication.json').write_text(json.dumps({
    'body': body_receipt, 'furniture_changed_paths': [list(k) for k, _ in changes],
    'profile': profile, 'saved_native_clips': saved['variants'],
    'runtime_published': True, 'game_tested': False}, ensure_ascii=False, indent=2), encoding='utf-8')
print('CHAPEL_PEW_PUBLISHED', len(profile['slots']), 'slots per pew; 6 native clips', flush=True)
