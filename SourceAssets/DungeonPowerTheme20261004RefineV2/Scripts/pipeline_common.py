"""Shared authoring contract. Importing this module never launches Unreal.

Authored positions are Blender metres; UE positions are (100*x,-100*y,100*z).
This package is a pending delivery, not an installation or a test receipt.
"""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
OWNED_BASE = '/Game/Dungeons/PowerTheme20261004/RefineV2'
SUBJECT_MAP = '/Game/GameMaps/Design/L_PowerTheme20261004_Subject'
RETURN_MAP = '/Game/GameMaps/DayNight_Lighting'
OWNER = 'DungeonPowerTheme20261004RefineV2'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False).encode('utf-8')).hexdigest()


def file_digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def source_file(relative):
    candidate = Path(relative)
    if candidate.is_absolute():
        raise ValueError('Source paths must be package-relative: ' + str(relative))
    path = (ROOT / candidate).resolve()
    if ROOT.resolve() not in path.parents or not path.is_file():
        raise ValueError('Source is absent or outside this delivery: ' + str(relative))
    return path


def package_path(value):
    return str(value).split('.')[0]


def require_owned(path):
    if not package_path(path).startswith(OWNED_BASE + '/'):
        raise RuntimeError('Refusing to save outside the owned namespace: ' + str(path))


def vector_m(value):
    if len(value) != 3 or not all(math.isfinite(float(n)) for n in value):
        raise ValueError('A finite 3D metre vector is required: ' + repr(value))
    return [100.0 * value[0], -100.0 * value[1], 100.0 * value[2]]


def direction(value):
    return [value[0], -value[1], value[2]]


def add(a, b):
    return [a[i] + b[i] for i in range(3)]


def cell_m(cell):
    a, b = vector_m(cell['min']), vector_m(cell['max'])
    return {'min': [min(a[i], b[i]) for i in range(3)],
            'max': [max(a[i], b[i]) for i in range(3)]}


def origin(spec):
    # origin_m is the original manifest contract; origins_m is accepted for a
    # single section only, never as an implicit global coordinate conversion.
    return spec.get('origin_m', spec.get('origins_m', [0, 0, 0]))


def load_inputs():
    scene = read(ROOT / 'Config/scene.json')
    manifest = read(ROOT / 'Authored/manifest.json')
    raw = read(ROOT / 'Config/materials.json')
    roles = raw.get('roles', raw.get('materials', raw))
    if scene.get('ue_base') != OWNED_BASE or scene.get('sample_map') != SUBJECT_MAP:
        raise RuntimeError('This delivery may only author its declared namespace and subject map')
    if not scene.get('revision') or not scene.get('rooms'):
        raise ValueError('Scene revision and rooms are required')
    if manifest.get('revision', scene['revision']) != scene['revision']:
        raise RuntimeError('Scene/manifest revision differs; preserve both until reconciled')
    sections = scene['rooms'] + scene.get('connectors', [])
    ids = [s['id'] for s in sections]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate room/connector IDs')
    names = [o['name'] for o in manifest['objects']]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate authored mesh names')
    for item in manifest['objects']:
        if item['room_id'] not in ids + scene.get('prototype_ids', []):
            raise ValueError('Mesh references unknown section: ' + item['name'])
        if item.get('guardrail_drop') and not item.get('collision'):
            raise ValueError('GuardrailDrop requires real collision: ' + item['name'])
        if item.get('collision') and item.get('simple_collision_hulls', 0) < 1:
            raise ValueError('Collidable authored mesh needs explicit UCX: ' + item['name'])
    return scene, manifest, roles


def existing_specs(scene, authored=False):
    """Scene-wide paths declare dependencies; reused_parts declare placements.

    Section reused_parts.position_m is local to that section. Scene-wide
    reused_parts has a required room_id, plus a local position_m. An entry may
    use asset_id resolved from existing_assets, or provide mesh explicitly.
    """
    declarations = scene.get('existing_assets', [])
    if isinstance(declarations, dict):
        declarations = [dict(id=k, **v) if isinstance(v, dict) else {'id': k, 'mesh': v}
                        for k, v in declarations.items()]
    lookup = {s['id']: s for s in declarations if s.get('id')}
    sections = {s['id']: s for s in scene['rooms'] + scene.get('connectors', [])}
    placed = []
    field = 'authored_parts' if authored else 'reused_parts'
    for section in sections.values():
        for item in section.get(field, []):
            placed.append((section, item))
    for item in scene.get(field, []):
        placed.append((sections[item['room_id']], item))
    for section, item in placed:
        merged = dict(lookup.get(item.get('asset_id'), {}), **item)
        path = merged.get('mesh', merged.get('ue_path'))
        if not path or not path.startswith('/Game/'):
            raise ValueError('A verified /Game mesh path is required: ' + repr(merged))
        if 'position_m' not in merged:
            raise ValueError('Reused part needs explicit local position_m: ' + path)
        merged['mesh'] = path
        if authored:
            require_owned(path)
        yield section, merged


def external_dependencies(scene, roles, used_roles=None):
    paths = set()
    declarations = scene.get('existing_assets', [])
    if isinstance(declarations, dict):
        declarations = list(declarations.values())
    for item in declarations:
        path = item if isinstance(item, str) else item.get('mesh', item.get('ue_path'))
        if path:
            paths.add(path)
        if isinstance(item, dict):
            paths.update(p for p in (item.get('materials') or {}).values() if p)
    for _, part in existing_specs(scene):
        paths.add(part['mesh'])
        overrides = part.get('materials', part.get('material_overrides', [])) or []
        for value in (overrides.values() if isinstance(overrides, dict) else overrides):
            if value:
                paths.add(value)
    for name, role in roles.items():
        if used_roles is not None and name not in used_roles:
            continue
        if role.get('existing_ue_path'):
            paths.add(role['existing_ue_path'])
    return sorted(p for p in paths if not p.startswith(OWNED_BASE + '/'))


def light_spec(item):
    """Return the actual AuthoredDungeonGenerator light schema (UE cm)."""
    result = {k: v for k, v in item.items() if k not in
              ('id', 'position_m', 'lumens', 'radius_cm', 'yaw_deg', 'pitch_deg')}
    result['position'] = vector_m(item['position_m'])
    result['intensity'] = float(item['lumens'])
    result['radius'] = float(item['radius_cm'])
    result['type'] = item.get('type', 'point')
    result['role'] = item.get('role', 'key')
    result['color'] = item.get('color', item.get('tint', [1, 1, 1]))
    result['indirect_lighting_intensity'] = item.get('indirect_lighting_intensity', item.get('indirect', 1))
    result.pop('tint', None)
    result.pop('indirect', None)
    result['cast_shadows'] = bool(item.get('cast_shadows', False))
    result['max_draw_distance_cm'] = float(item.get('max_draw_distance_cm', 3400))
    result['fade_range_cm'] = float(item.get('fade_range_cm', 600))
    if not 0 < result['radius'] <= 2500:
        raise ValueError('Local light radius must be finite and bounded (0..2500 cm)')
    if not 0 < result['max_draw_distance_cm'] <= 6000:
        raise ValueError('Local light draw distance must be finite and bounded (0..6000 cm)')
    if not 0 < result['fade_range_cm'] < result['max_draw_distance_cm']:
        raise ValueError('Light needs a positive fade range below draw distance')
    if result['type'] not in ('point', 'spot'):
        raise ValueError('Only point/spot lights are supported by this delivery')
    if item.get('yaw_deg') is not None:
        result['yaw'] = -float(item['yaw_deg'])
    return result


def execution_guard(u):
    if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
        raise RuntimeError('Copy the package under the intended FPSGAME/SourceAssets first')
    command = u.SystemLibrary.get_command_line().lower()
    if '-run=pythonscript' not in command or '-powerthemeauthorizewrite' not in command:
        raise RuntimeError('Authorized background Python commandlet required; no live-editor execution')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():
        raise RuntimeError('Preserve unsaved maps')
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('Preserve the active game session')


def assert_dependencies(u, paths):
    missing = [p for p in paths if not u.load_asset(p)]
    if missing:
        raise RuntimeError('Required approved assets are missing; no substitute will be made:\n' + '\n'.join(missing))


def stamp_asset(u, asset, fingerprint, revision):
    require_owned(asset.get_path_name())
    for key, value in [('Owner', OWNER), ('Revision', revision), ('Fingerprint', fingerprint)]:
        u.EditorAssetLibrary.set_metadata_tag(asset, OWNER + '.' + key, value)


def matching_asset(u, path, fingerprint, revision):
    if not u.EditorAssetLibrary.does_asset_exist(path):
        disk = PROJECT / 'Content' / (package_path(path).removeprefix('/Game/') + '.uasset')
        if disk.exists():
            raise RuntimeError('Unregistered existing asset file must be preserved: ' + str(disk))
        return None
    asset = u.load_asset(path)
    expected = {'Owner': OWNER, 'Revision': revision, 'Fingerprint': fingerprint}
    if not asset or any(u.EditorAssetLibrary.get_metadata_tag(asset, OWNER + '.' + k) != v
                        for k, v in expected.items()):
        raise RuntimeError('Existing asset is unowned or differs. Preserve it and create a new revision/namespace: ' + path)
    return asset
