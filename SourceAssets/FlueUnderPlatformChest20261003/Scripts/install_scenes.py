"""Save one under-gallery treasure into the current catalog and retained subject map."""
import hashlib
import json
import runpy
import shutil
import traceback
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
LINE=ROOT.parent/'DungeonIncineratorLine20261003'
PRODUCTION='/Game/GameMaps/L_Dungeon_Randomized'
PREVIEW='/Game/GameMaps/Design/L_Incinerator_Theme_Subject'
read=lambda p:json.loads(p.read_text('utf-8-sig'))
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
def backup(path):
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    target=ROOT/'Backup'/(path.stem+'-'+digest[:12]+path.suffix)
    if not target.exists():shutil.copy2(path,target)
    return digest

existing=globals().get('FLUE_CHEST_EXISTING_EDITOR',False)
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and not existing:
    raise RuntimeError('Commandlet or existing editor bridge required')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Preserve the active play session')
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
if dirty:raise RuntimeError('Preserve unsaved maps '+str(dirty))
original=editor.get_editor_world() if editor else None
original=original.get_path_name().split('.')[0] if original else ''
rules=runpy.run_path(str(ROOT/'Scripts/extend_catalog.py'));data=rules['rules']()
ue=runpy.run_path(str(ROOT/'Scripts/unreal_helpers.py'))
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
cache={}
def asset(path):
    if path not in cache:
        cache[path]=u.load_asset(path)
        if not cache[path]:raise RuntimeError('Saved treasure asset unavailable '+path)
    return cache[path]
receipt=ROOT/'Receipts/install.json'
report=dict(stage='saving',maps={},revision=data['revision'],chest=data['chest'],
    tests_run=False,game_run=False,rendered=False,editor_opened=False,assets_imported=False,native_changes=False)
try:
    write(receipt,report)
    old=backup(PROJECT/'Content/GameMaps/L_Dungeon_Randomized.umap')
    world=u.EditorLoadingAndSavingUtils.load_map(PRODUCTION)
    generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
    if len(generators)!=1:raise RuntimeError('Current production generator unavailable')
    generator=generators[0];before=generator.get_editor_property('module_catalog_json')
    write(ROOT/'Backup'/('catalog-'+hashlib.sha256(before.encode()).hexdigest()[:12]+'.json'),json.loads(before))
    catalog=rules['extend'](json.loads(before))
    hard={a.get_path_name():a for a in generator.get_editor_property('module_assets') if a}
    for path in sorted(set(rules['asset_paths'](data['chest']))):
        loaded=asset(path);hard[loaded.get_path_name()]=loaded
    text=json.dumps(catalog,ensure_ascii=False)
    generator.modify();generator.set_editor_property('module_catalog_json',text)
    generator.set_editor_property('module_assets',list(hard.values()))
    if not u.EditorLoadingAndSavingUtils.save_map(world,PRODUCTION):raise RuntimeError('Production map save failed')
    report['maps'][PRODUCTION]=dict(stage='map_saved',previous_sha256=old,module=data['module'],chests_added=1)
    write(receipt,report)

    old=backup(PROJECT/'Content/GameMaps/Design/L_Incinerator_Theme_Subject.umap')
    world=u.EditorLoadingAndSavingUtils.load_map(PREVIEW)
    if not world:raise RuntimeError('Retained incinerator subject map unavailable')
    line=read(LINE/'Config/line.json')
    pose=next(p for p in line['placements'] if p['id']==data['module'])
    for actor in actors.get_all_level_actors():
        if 'FlueUnderPlatformChest.Preview' in [str(t) for t in actor.tags]:actors.destroy_actor(actor)
    actor=ue['spawn_preview_chest'](actors,data['chest'],pose,asset,data['preview_blueprint'])
    location=actor.get_actor_location()
    if not u.EditorLoadingAndSavingUtils.save_map(world,PREVIEW):raise RuntimeError('Subject treasure save failed')
    report['maps'][PREVIEW]=dict(stage='map_saved',previous_sha256=old,chests_added=1,
        position=[location.x,location.y,location.z],claim='DungeonChestClaim.IncineratorLine.FlueUnderPlatform')
    write(receipt,report)

    report['mirrors_saved']=[]
    for relative in ('DungeonRoutes20260922/Config/catalog.json','DungeonThemedRoutes20261001/Config/catalog.json',
        'WarehouseContainers20261002/Config/catalog.json','DungeonSplitLevels20261001/Config/catalog.json',
        'DungeonStaffLiving20261002/Production20261002/Config/catalog.json',
        'StationWorkshop20261003/Config/catalog.json','SceneLootExpansion20261003/Config/catalog.json',
        'IncineratorContainers20261003/Config/catalog.json'):
        path=ROOT.parent/relative
        if path.exists():
            backup(path);write(path,rules['extend'](read(path)));report['mirrors_saved'].append(relative)
    path=ROOT.parent/'DungeonFlueGasStation20261001/Production20261001/Config/module.json'
    backup(path);write(path,rules['extend_module'](read(path)))
    path=LINE/'Config/source-modules.json';backup(path);source=read(path)
    source['modules']=[rules['extend_module'](m) for m in source['modules']]
    source['source_catalog_sha256']=hashlib.sha256(text.encode()).hexdigest();write(path,source)
    backup(LINE/'Config/line.json')
    line.update(flue_under_platform_chest_revision=data['revision'],flue_under_platform_chest_count=1,
        source_catalog_sha256=source['source_catalog_sha256']);write(LINE/'Config/line.json',line)
    write(ROOT/'Config/catalog.json',catalog)
    report.update(stage='maps_saved',original_map=original);write(receipt,report)
    print('FLUE_UNDER_PLATFORM_CHEST_MAPS_SAVED',PRODUCTION,PREVIEW,flush=True)
except Exception:
    report.update(stage='save_failed',error=traceback.format_exc());write(receipt,report);raise
finally:
    if existing and original and u.EditorAssetLibrary.does_asset_exist(original):
        u.EditorLoadingAndSavingUtils.load_map(original)
