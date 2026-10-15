"""Save only the approved power-container recipe changes into the current map."""
from datetime import datetime, timezone
from pathlib import Path
import json
import hashlib
import runpy
import shutil
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT / 'SourceAssets/PowerCollectibles20261014'
TARGET = '/Game/GameMaps/L_Dungeon_Randomized'
PATCH = runpy.run_path(str(ROOT / 'Scripts/power_containers.py'))
if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
    raise RuntimeError('Wrong project host')
background = '-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
original = None
if not background:
    level = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level.is_in_play_in_editor():
        raise RuntimeError('PIE active; map preserved')
    original = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world().get_path_name().split('.')[0]
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():
        raise RuntimeError('Unsaved maps present; preserve them before power-container integration')
backup = ROOT / 'Before/Content/GameMaps/L_Dungeon_Randomized.umap'
backup.parent.mkdir(parents=True, exist_ok=True)
if not backup.exists():
    shutil.copy2(PROJECT / 'Content/GameMaps/L_Dungeon_Randomized.umap', backup)
map_file = PROJECT / 'Content/GameMaps/L_Dungeon_Randomized.umap'
loaded_map_hash = hashlib.sha256(map_file.read_bytes()).hexdigest()
world = u.EditorLoadingAndSavingUtils.load_map(TARGET)
if not world:
    raise RuntimeError('Cannot load production map')
generators = u.GameplayStatics.get_all_actors_of_class(world, u.AuthoredDungeonGenerator)
if len(generators) != 1:
    raise RuntimeError('Expected one dungeon generator')
generator = generators[0]
raw = generator.get_editor_property('module_catalog_json')
before = ROOT / 'Before/production-catalog.json'
if not before.exists():
    before.write_text(raw, encoding='utf8')
catalog = PATCH['patch_document'](json.loads(raw))
# These are existing authored body/lid assets. Resolve them while installing
# references, so a missing source package cannot silently create an empty box.
for path in (PATCH['BODY'], PATCH['LID']):
    if not u.load_asset(path):
        raise RuntimeError('Required toolbox asset unavailable: ' + path)
if hashlib.sha256(map_file.read_bytes()).hexdigest() != loaded_map_hash:
    raise RuntimeError('Production map changed during loading; preserve concurrent save and retry from latest map')
generator.modify()
generator.set_editor_property('module_catalog_json', json.dumps(catalog, ensure_ascii=False))
if not u.EditorLoadingAndSavingUtils.save_map(world, TARGET):
    raise RuntimeError('Production map save failed')
report = dict(stage='map_saved', timestamp_utc=datetime.now(timezone.utc).isoformat(),
              map=TARGET, added_containers=PATCH['TOOLBOXES'], game_run=False,
              tests_run=False, multiplayer_tested=False)
(ROOT / 'Receipts/scene.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
if original and original != TARGET:
    u.EditorLoadingAndSavingUtils.load_map(original)
print('POWER_CONTAINER_MAP_SAVED')
