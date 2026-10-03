"""Save the V3 catalog, then rebind only three meshes in the accepted subject."""
import hashlib,json,runpy,shutil
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PARENT=ROOT.parent;PROJECT=PARENT.parents[1]
BASE='/Game/Dungeons/StationWorkshop20261003/RefineV3'
read=lambda p:json.loads(p.read_text('utf-8-sig'))
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and not globals().get('STATION_WORKSHOP_EXISTING_EDITOR_INSTALL',False):raise RuntimeError('Commandlet or existing editor bridge required')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Preserve the active game session before station map save')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()}
if dirty:raise RuntimeError('Preserve unsaved maps before station save: '+str(sorted(dirty)))
assets=read(ROOT/'Receipts/assets.json')
if assets.get('stage')!='assets_saved':raise RuntimeError('Save correction assets before scene integration')
helpers=runpy.run_path(str(PARENT/'Scripts/extend_catalog.py'))
rules=read(ROOT/'Config/workshop.json')
actors=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
original=editor.get_editor_world().get_path_name().split('.')[0] if editor and editor.get_editor_world() else ''
report=dict(stage='saving',maps={},tests_run=False,rendered=False,game_run=False,editor_opened=False,
    native_changes=False,native_build='Reuses already saved V2 binaries; mesh/material/catalog corrections only')
rp=ROOT/'Receipts/install.json'
def record():rp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
def backup(target):
    file=PROJECT/'Content'/(target.removeprefix('/Game/')+'.umap')
    sha=hashlib.sha256(file.read_bytes()).hexdigest()
    dest=ROOT/'Backup'/(file.stem+'-'+sha[:12]+'.umap')
    if not dest.exists():shutil.copy2(file,dest)
    return sha

target='/Game/GameMaps/L_Dungeon_Randomized';before_sha=backup(target)
world=u.EditorLoadingAndSavingUtils.load_map(target)
generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
if len(generators)!=1:raise RuntimeError('Production generator unavailable')
generator=generators[0];before=generator.get_editor_property('module_catalog_json')
(ROOT/'Backup'/('catalog-'+hashlib.sha256(before.encode()).hexdigest()[:12]+'.json')).write_text(before,encoding='utf8')
catalog=helpers['extend'](json.loads(before),rules)
hard={a.get_path_name():a for a in generator.get_editor_property('module_assets') if a}
for path in sorted({item['path'] for item in assets['meshes'].values()}|set(assets['materials'])):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Correction asset unavailable: '+path)
    hard[asset.get_path_name()]=asset
generator.modify();generator.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
generator.set_editor_property('module_assets',list(hard.values()))
if not u.EditorLoadingAndSavingUtils.save_map(world,target):raise RuntimeError('Production map save failed')
report['maps'][target]=dict(stage='map_saved',revision=3,previous_sha256=before_sha);record()

target='/Game/GameMaps/Design/L_FreightTransit_Theme_Subject';before_sha=backup(target)
world=u.EditorLoadingAndSavingUtils.load_map(target)
if not world:raise RuntimeError('Accepted station-line subject unavailable')
remap={
    '/Game/Dungeons/StationWorkshop20261003/Meshes/SM_SW_Roof':BASE+'/Meshes/SM_SW_Roof',
    '/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkbenchKit/Meshes/SM_WBK_Fab_BenchRetained':BASE+'/Meshes/SM_SW_BenchRetained',
    '/Game/Dungeons/TransitStation20260928/Meshes/SM_Station_Railings':BASE+'/Meshes/SM_Station_Railings'}
rebound=[]
for actor in actors.get_all_level_actors():
    for component in actor.get_components_by_class(u.StaticMeshComponent):
        mesh=component.static_mesh;old=mesh.get_path_name().split('.')[0] if mesh else ''
        replacement=remap.get(old)
        if not replacement:continue
        if old.endswith('/SM_WBK_Fab_BenchRetained') and 'Station.Workshop.Preview' not in [str(t) for t in actor.tags]:continue
        component.modify();component.set_static_mesh(u.load_asset(replacement))
        rebound.append(dict(actor=actor.get_actor_label(),old=old,new=replacement))
if not u.EditorLoadingAndSavingUtils.save_map(world,target):raise RuntimeError('Station-line subject save failed')
report['maps'][target]=dict(stage='map_saved',revision=3,previous_sha256=before_sha,rebound_components=rebound)

text=json.dumps(catalog,ensure_ascii=False,indent=2)
for relative in ('DungeonRoutes20260922/Config/catalog.json','DungeonThemedRoutes20261001/Config/catalog.json',
    'WarehouseContainers20261002/Config/catalog.json','DungeonSplitLevels20261001/Config/catalog.json',
    'DungeonStaffLiving20261002/Production20261002/Config/catalog.json'):
    (PROJECT/'SourceAssets'/relative).write_text(text,encoding='utf8')
for path in (ROOT/'Config/catalog.json',PARENT/'Config/catalog.json'):path.write_text(text,encoding='utf8')
station=next(m for m in catalog['modules'] if m['id']=='AbandonedTransitStation')
(PROJECT/'SourceAssets/DungeonTransitStation20260928/Config/module.json').write_text(json.dumps(station,ensure_ascii=False,indent=2),encoding='utf8')
(PARENT/'Config/workshop.json').write_text((ROOT/'Config/workshop.json').read_text('utf8'),encoding='utf8')
for path,field in ((PROJECT/'SourceAssets/DungeonStationLine20261002/Config/line.json','station_workshop_revision'),
    (PROJECT/'SourceAssets/DungeonTransitStation20260928/Config/room.json','workshop_revision')):
    data=read(path);data[field]=3;path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
report['stage']='maps_saved';record()
(PARENT/'Receipts/install.json').write_text(rp.read_text('utf8'),encoding='utf8')
if original and original!=target and u.EditorAssetLibrary.does_asset_exist(original):
    u.EditorLoadingAndSavingUtils.load_map(original)
print('STATION_WORKSHOP_V3_MAPS_SAVED',len(rebound),'COMPONENTS_REBOUND',flush=True)
