"""Remove the rejected miner encounter; run before archiving its assets/classes."""
import hashlib
import json
import shutil
from pathlib import Path
import unreal

ROOT = Path('D:/FPS3D/FPSGAME').resolve()
ARCHIVE = ROOT / 'trash/infected-miner-rejected-20260913'
REPORT = ROOT / 'Docs/Rejected/infected-miner-scene-removal-20260913.json'
PREFIXES = ('/Game/Monsters/InfectedMiner/', '/Game/Tests/InfectedMiner/')

def owned(package):
    return any(package.startswith(prefix) for prefix in PREFIXES)

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

registry = unreal.AssetRegistryHelpers.get_asset_registry()
registry.search_all_assets(True)
options = unreal.AssetRegistryDependencyOptions(True, True, True, True, True)
external = set()
for folder in PREFIXES:
    for asset in registry.get_assets_by_path(folder.rstrip('/'), recursive=True):
        external.update(str(p) for p in registry.get_referencers(asset.package_name, options)
                        if str(p).startswith('/Game/') and not owned(str(p)))

report = {'status': 'preparing', 'external_referencers': sorted(external),
          'removed_actors': [], 'backups': [], 'replacement': None}
REPORT.parent.mkdir(parents=True, exist_ok=True)
def write_report():
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
write_report()

map_path = '/Game/GameMaps/L_Normandy_FPS_Test'
map_file = ROOT / 'Content/GameMaps/L_Normandy_FPS_Test.umap'
backups = {map_file}
for package in external:
    relative = package.removeprefix('/Game/')
    for suffix in ('.umap', '.uasset', '.uexp', '.ubulk'):
        candidate = ROOT / 'Content' / (relative + suffix)
        if candidate.is_file():
            backups.add(candidate)
    if package != map_path and not package.startswith('/Game/__ExternalActors__/GameMaps/L_Normandy_FPS_Test/'):
        raise RuntimeError('Unexpected reference requires explicit scoped edit: ' + package)

# Native spawners can reference the class without referencing the Blueprint package.
external_dir = ROOT / 'Content/__ExternalActors__/GameMaps/L_Normandy_FPS_Test'
if external_dir.exists():
    for path in external_dir.rglob('*.uasset'):
        data = path.read_bytes()
        if b'InfectedMiner' in data or 'InfectedMiner'.encode('utf-16-le') in data:
            backups.add(path)

for source in sorted(backups):
    source = source.resolve()
    assert source.is_relative_to(ROOT / 'Content')
    destination = (ARCHIVE / 'BeforeSceneRemoval' / source.relative_to(ROOT)).resolve()
    assert destination.is_relative_to(ARCHIVE.resolve())
    sha = digest(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        assert digest(destination) == sha, 'Existing archive differs; do not overwrite'
    else:
        shutil.copy2(source, destination)
    assert digest(destination) == sha
    report['backups'].append({'source': source.relative_to(ROOT).as_posix(),
        'target': destination.relative_to(ROOT).as_posix(), 'bytes': source.stat().st_size,
        'sha256': sha, 'reason': 'Before removing only the rejected miner encounter; shared level retained',
        'replacement': 'Current village level without miner encounter', 'state': 'copied'})
write_report()

level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert level.load_level(map_path)
for actor in actors.get_all_level_actors():
    cls = actor.get_class().get_name()
    if cls in ('InfectedMinerSpawner', 'InfectedMiner', 'BP_InfectedMiner_C'):
        report['removed_actors'].append({'name': actor.get_name(), 'label': actor.get_actor_label(),
                                        'class': cls, 'path': actor.get_path_name()})
        assert actors.destroy_actor(actor)
assert report['removed_actors'], 'Expected miner encounter was not found; no level saved'
for item in report['backups']:
    path = ROOT / item['source']
    if path.exists():
        assert digest(path) == item['sha256'], 'Another task changed the map before save'
assert level.save_current_level()
report['status'] = 'removed_and_saved'
report['map'] = map_path
report['saved_map_sha256'] = digest(map_file)
write_report()
unreal.log('MINER_RETIREMENT_SCENE_SAVED ' + json.dumps(report['removed_actors']))
