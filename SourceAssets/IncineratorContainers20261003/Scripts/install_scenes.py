"""Save treatment bays into the latest production catalog and the retained subject map."""
import hashlib
import json
import runpy
import shutil
import traceback
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
PRODUCTION='/Game/GameMaps/L_Dungeon_Randomized'
PREVIEW='/Game/GameMaps/Design/L_Incinerator_Theme_Subject'
LINE=ROOT.parent/'DungeonIncineratorLine20261003'
read=lambda p:json.loads(p.read_text('utf-8-sig'))
write=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8')
existing=globals().get('TREATMENT_CONTAINERS_EXISTING_EDITOR',False)
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and not existing:
    raise RuntimeError('Commandlet or existing editor bridge required')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world():raise RuntimeError('Preserve active play session')
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
if dirty:raise RuntimeError('Preserve unsaved maps: '+str(dirty))
imported=read(ROOT/'Receipts/assets.json')
if imported.get('stage')!='assets_saved':raise RuntimeError('Models must be saved before placement')
helpers=runpy.run_path(str(ROOT/'Scripts/catalog_rules.py'))
ue=runpy.run_path(str(ROOT/'Scripts/unreal_helpers.py'))
layout=helpers['read_layout']();actors=u.get_editor_subsystem(u.EditorActorSubsystem)
original=editor.get_editor_world().get_path_name().split('.')[0]
report=dict(stage='saving',maps={},tests_run=False,game_run=False,rendered=False,editor_opened=False,
    count_ranges=layout['count_ranges'],physical_count_ranges=layout['physical_count_ranges'],rewards_deferred=True)
receipt=ROOT/'Receipts/install.json';(ROOT/'Backup').mkdir(exist_ok=True)
cache={}


def backup(path):
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    dest=ROOT/'Backup'/(path.stem+'-'+digest[:12]+path.suffix)
    if not dest.exists():shutil.copy2(path,dest)
    return digest


def map_backup(path):return backup(PROJECT/'Content'/(path.removeprefix('/Game/')+'.umap'))


def asset(path):
    if path not in cache:
        cache[path]=u.load_asset(path)
        if not cache[path]:raise RuntimeError('Treatment asset unavailable '+path)
    return cache[path]


try:
    write(receipt,report)
    before_sha=map_backup(PRODUCTION);world=u.EditorLoadingAndSavingUtils.load_map(PRODUCTION)
    generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
    if len(generators)!=1:raise RuntimeError('Saved production generator unavailable')
    generator=generators[0];before=generator.get_editor_property('module_catalog_json');catalog=json.loads(before)
    current={m['id']:m for m in catalog['modules']}
    authored={m['id']:m for m in read(ROOT/'Config/placement-source.json')['modules']}
    for identity in layout['groups']:
        if helpers['geometry_key'](current[identity])!=helpers['geometry_key'](authored[identity]):
            raise RuntimeError('Treatment architecture changed during bay authoring: '+identity)
    (ROOT/'Backup'/('catalog-'+hashlib.sha256(before.encode()).hexdigest()[:12]+'.json')).write_text(before,encoding='utf8')
    catalog=helpers['extend'](catalog)
    hard={a.get_path_name():a for a in generator.get_editor_property('module_assets') if a}
    for path in sorted(set(helpers['paths'](layout))):
        obj=asset(path);hard[obj.get_path_name()]=obj
    generator.modify();generator.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
    generator.set_editor_property('module_assets',list(hard.values()))
    ue['ensure_outline'](actors,layout['outline'],'Dungeon_SceneContainerOutline',asset)
    if not u.EditorLoadingAndSavingUtils.save_map(world,PRODUCTION):raise RuntimeError('Production save failed')
    report['maps'][PRODUCTION]=dict(stage='map_saved',previous_sha256=before_sha,
        modules=list(layout['groups']),selection='existing seeded CargoWarehouseContainers Compose')
    write(receipt,report)

    before_sha=map_backup(PREVIEW);world=u.EditorLoadingAndSavingUtils.load_map(PREVIEW)
    if not world:raise RuntimeError('Retained incinerator subject map unavailable')
    line=read(LINE/'Config/line.json')
    for actor in actors.get_all_level_actors():
        if ue['OWNED_TAG'] in [str(t) for t in actor.tags]:actors.destroy_actor(actor)
    selected={}
    for offset,(identity,groups) in enumerate(layout['groups'].items()):
        pose=next(p for p in line['placements'] if p['id']==identity)
        for spec in layout['fixed_parts'][identity]:ue['spawn_fixed'](actors,spec,pose,asset)
        containers=helpers['choose'](groups,layout['preview_seed']+offset)
        for spec in containers:ue['spawn_container'](actors,spec,pose,asset)
        selected[identity]=[dict(id=s['container_id'],caption=s['caption'],position=s['position'],yaw=s['yaw']) for s in containers]
    ue['ensure_outline'](actors,layout['outline'],'IncineratorLine_ContainerOutline',asset,True)
    if not u.EditorLoadingAndSavingUtils.save_map(world,PREVIEW):raise RuntimeError('Subject save failed')
    report['maps'][PREVIEW]=dict(stage='map_saved',previous_sha256=before_sha,
        preview_seed=layout['preview_seed'],authored_container_count=sum(map(len,selected.values())),selected=selected)
    write(receipt,report)

    report['mirrors_saved']=[]
    for relative in ('DungeonRoutes20260922/Config/catalog.json','DungeonThemedRoutes20261001/Config/catalog.json',
        'WarehouseContainers20261002/Config/catalog.json','DungeonSplitLevels20261001/Config/catalog.json',
        'DungeonStaffLiving20261002/Production20261002/Config/catalog.json',
        'StationWorkshop20261003/Config/catalog.json','SceneLootExpansion20261003/Config/catalog.json'):
        path=ROOT.parent/relative
        if path.exists():backup(path);write(path,helpers['extend'](read(path)));report['mirrors_saved'].append(relative)
    for relative in ('DungeonIncineratorHall20260929/Pool20260930/Config/module.json',
                     'DungeonFlueGasStation20261001/Production20261001/Config/module.json'):
        path=ROOT.parent/relative
        if path.exists():backup(path);write(path,helpers['extend_module'](read(path)))
    source=LINE/'Config/source-modules.json';backup(source);data=read(source)
    data['modules']=[helpers['extend_module'](m) for m in data['modules']];write(source,data)
    write(ROOT/'Config/catalog.json',catalog)
    backup(LINE/'Config/line.json')
    line.update(treatment_container_revision=layout['revision'],treatment_container_count_ranges=layout['count_ranges'],
        treatment_physical_container_count_ranges=layout['physical_count_ranges'],
        authored_container_count=sum(map(len,selected.values())),container_preview_seed=layout['preview_seed'],
        container_rewards_deferred=True)
    write(LINE/'Config/line.json',line)
    assembly_file=ROOT/'Config/assemblies.json';assembly=read(assembly_file)
    assembly['scene_placement_completed']=True;write(assembly_file,assembly)
    report.update(stage='maps_saved',original_map=original);write(receipt,report)
    print('TREATMENT_CONTAINER_MAPS_SAVED '+str(sum(map(len,selected.values()))),flush=True)
except Exception:
    report.update(stage='save_failed',error=traceback.format_exc());write(receipt,report);raise
finally:
    if existing and original and u.EditorAssetLibrary.does_asset_exist(original):
        u.EditorLoadingAndSavingUtils.load_map(original)
