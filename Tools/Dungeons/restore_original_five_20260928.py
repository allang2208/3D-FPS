"""One-off retirement of derived rooms. Save only the dungeon generator; never generate a layout."""
import hashlib
import json
import runpy
from pathlib import Path
import unreal as u

PROJECT = Path(__file__).resolve().parents[2]
ARCHIVE = PROJECT / 'trash/dungeon-room-variants-retired-20260928'
TARGET = '/Game/GameMaps/L_Dungeon_Randomized'
ORIGINALS = ['Distribution', 'Drainage', 'ShoredBreach', 'VentilationLoop', 'FreightTransfer']
RETIRED = {'Drainage_NearBridge', 'Drainage_FarBridge', 'VentilationLoop_WestCore', 'VentilationLoop_EastCore'}
PREFIXES = ('/Game/Dungeons/RoomSizes20260928/', '/Game/Dungeons/RoomVariants20260924/')
BENCH = '/Game/Dungeons/FacilityScenes20260927/Meshes/SM_Facility_RepairBench'

if Path(u.Paths.project_dir()).resolve() != PROJECT:
    raise RuntimeError('Wrong project')
ue = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if ue and ue.get_game_world():
    raise RuntimeError('Preserve active play')

def dirty():
    return list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages()) + list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())

initial = {p.get_name() for p in dirty()}
if any('/gamemaps/l_dungeon_randomized' in p.lower() for p in initial):
    raise RuntimeError('Preserve unsaved dungeon changes')
world = ue.get_editor_world() if ue else None
if not world or world.get_path_name().split('.')[0] != TARGET:
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():
        raise RuntimeError('Preserve current unsaved map')
    world = u.EditorLoadingAndSavingUtils.load_map(TARGET)
generators = u.GameplayStatics.get_all_actors_of_class(world, u.AuthoredDungeonGenerator)
if len(generators) != 1:
    raise RuntimeError('Expected one dungeon generator')
g = generators[0]
before = g.get_editor_property('module_catalog_json')
ARCHIVE.mkdir(parents=True, exist_ok=True)
backup = ARCHIVE / ('saved-catalog-before-' + hashlib.sha256(before.encode()).hexdigest()[:12] + '.json')
if not backup.exists():
    backup.write_text(before, encoding='utf-8')
catalog = json.loads(before)
old_ids = catalog['room_ids'][:]
removed = []
retained = []
for module in catalog['modules']:
    mid = module['id']
    if (mid in RETIRED or mid.startswith('VentilationLoop_Recipe_')
            or module.get('size_source') == 'DungeonRoomSizes20260928'):
        removed.append(mid)
    else:
        retained.append(module)
catalog['modules'] = retained
if not set(ORIGINALS).issubset({m['id'] for m in retained}):
    raise RuntimeError('Original room module missing; do not install')
catalog['room_ids'] = ORIGINALS
for key in ('room_recipe_library', 'room_variation_version', 'room_composition_version',
            'room_size_version', 'room_size_min_expansion_cm'):
    catalog.pop(key, None)
catalog['generator_version'] = max(7, catalog.get('generator_version', 1))
# Reapply only the updated scene recipes. Reservations are authored alongside
# surviving equipment, so the removed bench also releases its floor space.
scenes = PROJECT / 'SourceAssets/DungeonFacilityScenes20260927/Scripts/extend_catalog.py'
catalog = runpy.run_path(str(scenes))['extend'](catalog)

assets = []
removed_assets = []
for asset in g.get_editor_property('module_assets'):
    if not asset:
        continue
    path = asset.get_path_name().split('.')[0]
    if path.startswith(PREFIXES) or path == BENCH:
        removed_assets.append(path)
    else:
        assets.append(asset)
g.modify()
g.set_editor_property('module_catalog_json', json.dumps(catalog, ensure_ascii=False))
g.set_editor_property('module_assets', assets)
owned = [p for p in dirty() if p.get_name() not in initial and '/gamemaps/l_dungeon_randomized' in p.get_name().lower()]
if not owned or not u.EditorLoadingAndSavingUtils.save_packages(owned, False):
    raise RuntimeError('Generator catalog save failed')
(PROJECT / 'SourceAssets/DungeonRoutes20260922/Config/catalog.json').write_text(
    json.dumps(catalog, ensure_ascii=False, indent=2), encoding='utf-8')
result = dict(stage='map_saved', map=TARGET, previous_room_ids=old_ids, room_ids=ORIGINALS,
              removed_modules=removed, removed_hard_references=removed_assets,
              generator_version=catalog['generator_version'], room_scene_version=catalog['room_scene_version'],
              saved_actor_packages=[p.get_name() for p in owned], root_map_modified=False, tests_run=False)
receipt = PROJECT / 'Saved/DungeonOriginalFive20260928/install.json'
receipt.parent.mkdir(parents=True, exist_ok=True)
receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print('ORIGINAL_FIVE_SAVED', json.dumps(dict(room_ids=ORIGINALS, removed_modules=len(removed),
    removed_hard_references=len(removed_assets), saved_actor_packages=result['saved_actor_packages'])), flush=True)
