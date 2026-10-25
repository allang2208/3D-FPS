"""Publish only the fitted chair roles and their corresponding camera/timing."""
import hashlib
import json
import os
import runpy
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'SourceAssets/FurnitureRest20261022'/globals().get('FURNITURE_REVISION', 'ChairReuse20261024')
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
saved = read(OUT/'assets_saved.json')
baseline = read(OUT/'baseline_routes.json')
metadata = read(OUT/'clip_metadata.json')
type_updates = read(OUT/'type_updates.json') if (OUT/'type_updates.json').exists() else {}
complete = read(OUT/'save_complete.json')
if not complete['saved'] or set(saved['default']) != set(metadata):
    raise RuntimeError('Chair save stage is incomplete.')
if hashlib.sha256((OUT/'authored.json').read_bytes()).hexdigest() != complete['authored_sha256']:
    raise RuntimeError('The saved clips do not match the current authored source.')
helper = runpy.run_path(str(ROOT/'Tools/PlayerBody/config_transaction.py'))
commit = helper['commit']
body_path = ROOT/'Content/ColdSteelData/player_body.json'
before = body_path.read_bytes()
body = json.loads(before.decode('utf-8-sig'))
owned = []
for role, asset in saved['default'].items():
    if body['clips'][role] not in (baseline['default'][role], asset):
        raise RuntimeError('Chair route changed during authoring: '+role)
    body['clips'][role] = asset
    owned.append(('clips', role))
for name, variant in baseline['variants'].items():
    routes = saved['variants'].get(name, {})
    if set(routes) != set(metadata):
        raise RuntimeError('Native variant save stage incomplete: '+name)
    current = body['body_variants'][name]
    if current['body_mesh'] != variant['mesh']:
        raise RuntimeError('Target body changed during authoring: '+name)
    for role, asset in routes.items():
        if current['clips'][role] not in (variant['clips'][role], asset):
            raise RuntimeError('Variant chair route changed during authoring: '+name+'/'+role)
        current['clips'][role] = asset
        owned.append(('body_variants', name, 'clips', role))
for routes in (saved['default'], *saved['variants'].values()):
    for asset in routes.values():
        package = ROOT/'Content'/(asset.split('.')[0][6:]+'.uasset')
        if not package.is_file():
            raise RuntimeError('Saved animation package is missing: '+asset)

for variant,tracks in globals().get('NATIVE_CAMERA_UPDATES',{}).items():
    node=body if variant=='default' else body['body_variants'][variant]
    prefix=() if variant=='default' else ('body_variants',variant)
    for role,track in tracks.items():
        if role not in metadata or track['animation']!=node['clips'][role]:raise RuntimeError('Native camera does not match saved role: '+role)
        node.setdefault('furniture_camera_tracks',{})[role]=track
        owned.append(prefix+('furniture_camera_tracks',role))

furniture_path = ROOT/'Content/ColdSteelData/furniture_rest.json'
furniture_before = furniture_path.read_bytes()
furniture = json.loads(furniture_before.decode('utf-8-sig'))
if (OUT/'baseline.json').exists():
    initial_types=read(OUT/'baseline.json').get('furniture',{}).get('types',{})
    for kind,spec in type_updates.items():
        if kind in initial_types and furniture['types'][kind] not in (initial_types[kind],spec):raise RuntimeError('Furniture type changed while fitting: '+kind)
furniture['clips'].update(metadata)
furniture['types'].update(type_updates)
# The shared writer's public commit is deliberately limited to player_body.
# Furniture camera files use the existing furniture publication lock and the
# same scoped text editor, retaining unrelated fields and formatting.
original = json.loads(furniture_before.decode('utf-8-sig'))
edits = list(helper['_changes'](original, furniture))
text = furniture_before.decode('utf-8-sig')
for key, value in edits:
    if len(key) < 2 or not ((key[0] == 'clips' and key[1] in metadata) or (key[0] == 'types' and key[1] in type_updates)):
        raise RuntimeError('Unowned furniture edit: '+repr(key))
    text = helper['_set'](text, key, value)
result = (b'\xef\xbb\xbf' if furniture_before.startswith(b'\xef\xbb\xbf') else b'') + text.encode('utf-8')
if json.loads(result.decode('utf-8-sig')) != furniture:
    raise RuntimeError('Scoped furniture result differs from intended changes.')
with helper['_lock'](ROOT/'Saved/FurnitureRestConfigWrites/writer.lock'):
    if furniture_path.read_bytes() != furniture_before:
        raise RuntimeError('Furniture configuration changed; merge from fresh input.')
    if edits:
        backup = OUT/'furniture_rest.before.json'
        if not backup.exists():
            backup.write_bytes(furniture_before)
        temporary = furniture_path.with_name('.chair-reuse-'+uuid.uuid4().hex+'.tmp')
        try:
            temporary.write_bytes(result)
            if furniture_path.read_bytes() != furniture_before:
                raise RuntimeError('Furniture configuration changed during publication.')
            os.replace(temporary, furniture_path)
        finally:
            if temporary.exists():
                temporary.unlink()
config_receipt = {'status': 'applied' if edits else 'unchanged',
                  'changed_paths': [list(k) for k, v in edits],
                  'before_sha256': hashlib.sha256(furniture_before).hexdigest(),
                  'after_sha256': hashlib.sha256(result).hexdigest()}
body_receipt = commit(body_path, before, body, owned_paths=owned, producer=__file__)
(OUT/'publication.json').write_text(json.dumps({
    'body': body_receipt, 'furniture': config_receipt,
    'default_roles': list(saved['default']),
    'variant_roles': {k: list(v) for k, v in saved['variants'].items()},
    'runtime_published': True, 'game_tested': False,
    'git_commit': None, 'git_push': None,
}, indent=2), encoding='utf-8')
print('CHAIR_REUSE_PUBLISHED', len(owned), 'body routes;', len(metadata), 'timing/camera tracks')
