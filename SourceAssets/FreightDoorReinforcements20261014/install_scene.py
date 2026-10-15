"""Scoped saved-map edit. No generation, gameplay, screenshots or asset deletion."""
import datetime
import json
import runpy
import shutil
from pathlib import Path
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/FreightDoorReinforcements20261014'
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
PATCH=runpy.run_path(str(PROJECT/'Tools/FreightEncounter/service_doors.py'))
assert Path(u.Paths.project_dir()).resolve()==PROJECT.resolve()
background='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
original=None
if not background:
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level.is_in_play_in_editor():raise RuntimeError('PIE active; no map edit performed')
    original=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world().get_path_name().split('.')[0]
    dirty=u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    if dirty:raise RuntimeError('Unsaved maps present; preserve them before the freight map edit')
backup=ROOT/'Before/Content/GameMaps/L_Dungeon_Randomized.umap'
backup.parent.mkdir(parents=True,exist_ok=True)
if not backup.exists():shutil.copy2(PROJECT/'Content/GameMaps/L_Dungeon_Randomized.umap',backup)
world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
if not world:raise RuntimeError('Cannot load production map')
generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
if len(generators)!=1:raise RuntimeError('Expected one generator')
generator=generators[0]
raw=generator.get_editor_property('module_catalog_json')
before=ROOT/'Before/production-catalog.json'
if not before.exists():before.write_text(raw,encoding='utf8')
catalog=json.loads(raw)
old=next(m for m in catalog['modules'] if m['id']==PATCH['STATION'])
removed=[p for p in old['parts'] if p.get('fixture_id') in PATCH['REMOVED']]
updated=PATCH['patch_document'](catalog)
generator.modify()
generator.set_editor_property('module_catalog_json',json.dumps(updated,ensure_ascii=False))
if not u.EditorLoadingAndSavingUtils.save_map(world,TARGET):raise RuntimeError('Production map save failed')
report=dict(stage='map_saved',timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    map=TARGET,removed_parts=removed,service_walk_mask=PATCH['SERVICE_WALK'],
    doors_preserved=['AbandonedTransitStation.service.00','AbandonedTransitStation.service.01'],
    game_run=False,tests_run=False)
(ROOT/'Receipts/scene.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
if original and original!=TARGET:u.EditorLoadingAndSavingUtils.load_map(original)
print('FREIGHT_DOOR_MAP_SAVED '+json.dumps(report,ensure_ascii=False))
