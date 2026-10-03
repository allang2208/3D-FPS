"""Fit the roof and move only the freight tool cabinets; preserve other actors."""
import hashlib,json,math,runpy,shutil
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PARENT=ROOT.parent;PROJECT=ROOT.parents[2]
read=lambda p:json.loads(p.read_text('utf-8-sig'))
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and not globals().get('STATION_FIT_EXISTING_EDITOR',False):raise RuntimeError('Commandlet or existing editor bridge required')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Preserve active game session before fitted scene save')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()}
if dirty:raise RuntimeError('Preserve unsaved maps before fitted scene save: '+str(sorted(dirty)))
if read(ROOT/'Receipts/assets.json').get('stage')!='assets_saved':raise RuntimeError('Save fitted roof before scene integration')
helpers=runpy.run_path(str(ROOT/'Scripts/fit_rules.py'));roof=u.load_asset(helpers['ROOF'])
if not roof:raise RuntimeError('Fitted roof asset unavailable')
AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
original=editor.get_editor_world().get_path_name().split('.')[0] if editor and editor.get_editor_world() else ''
report=dict(stage='saving',maps={},revision=4,tests_run=False,rendered=False,game_run=False,editor_opened=False,native_changes=False)
receipt=ROOT/'Receipts/install.json'
def write(p,data):p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
def record():write(receipt,report)
def backup(target):
    path=PROJECT/'Content'/(target.removeprefix('/Game/')+'.umap');digest=hashlib.sha256(path.read_bytes()).hexdigest()
    dest=ROOT/'Backup'/(path.stem+'-'+digest[:12]+'.umap')
    if not dest.exists():shutil.copy2(path,dest)
    return digest

target='/Game/GameMaps/L_Dungeon_Randomized';old=backup(target)
world=u.EditorLoadingAndSavingUtils.load_map(target)
generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
if len(generators)!=1:raise RuntimeError('Production generator unavailable')
generator=generators[0];before=generator.get_editor_property('module_catalog_json')
(ROOT/'Backup'/('catalog-'+hashlib.sha256(before.encode()).hexdigest()[:12]+'.json')).write_text(before,encoding='utf8')
catalog=helpers['extend'](json.loads(before))
hard={a.get_path_name():a for a in generator.get_editor_property('module_assets') if a};hard[roof.get_path_name()]=roof
generator.modify();generator.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
generator.set_editor_property('module_assets',list(hard.values()))
if not u.EditorLoadingAndSavingUtils.save_map(world,target):raise RuntimeError('Production map save failed')
report['maps'][target]=dict(stage='map_saved',previous_sha256=old,fitted_roof=helpers['ROOF'],tool_positions=helpers['TOOL_POSITIONS']);record()

target='/Game/GameMaps/Design/L_FreightTransit_Theme_Subject';old=backup(target)
world=u.EditorLoadingAndSavingUtils.load_map(target)
if not world:raise RuntimeError('Accepted station preview unavailable')
linepath=PROJECT/'SourceAssets/DungeonStationLine20261002/Config/line.json';line=read(linepath)
pose=next(p for p in line['placements'] if p['id']=='FreightTransfer_WarehouseLink')
a=math.radians(pose['yaw']);origin=pose['position']
def pos(p):return u.Vector(p[0]*math.cos(a)-p[1]*math.sin(a)+origin[0],p[0]*math.sin(a)+p[1]*math.cos(a)+origin[1],p[2]+origin[2])
roof_actors=[];moved=[]
for actor in AA.get_all_level_actors():
    for component in actor.get_components_by_class(u.StaticMeshComponent):
        mesh=component.static_mesh
        if mesh and mesh.get_path_name().split('.')[0].split('/')[-1] in helpers['ROOF_NAMES']:
            actor.modify();component.modify();component.set_static_mesh(roof)
            component.set_material(0,roof.get_material(0));roof_actors.append(actor.get_actor_label())
    if not isinstance(actor,u.ColdSteelSceneContainer):continue
    identity=str(actor.get_editor_property('container_id')).removeprefix('StationLine.')
    key=identity.removesuffix('.Drawer');point=helpers['TOOL_POSITIONS'].get(key)
    if point:
        actor.modify();actor.set_actor_location(pos(point),False,False)
        moved.append(dict(id=identity,local_position=point))
if not u.EditorLoadingAndSavingUtils.save_map(world,target):raise RuntimeError('Station preview save failed')
report['maps'][target]=dict(stage='map_saved',previous_sha256=old,roof_actors=roof_actors,moved_containers=moved);record()

station=next(m for m in catalog['modules'] if m['id']=='AbandonedTransitStation')
for path in (PARENT/'Config/workshop.json',PARENT/'RefineV3/Config/workshop.json',ROOT/'Config/workshop.json'):write(path,station['station_workshop'])
lootpath=PROJECT/'SourceAssets/SceneLootExpansion20261003/Config/layout.json';loot=helpers['fitted'](read(lootpath))
loot.update(revision=2,freight_tool_bay_revision=2);write(lootpath,loot)
text=json.dumps(catalog,ensure_ascii=False,indent=2)
for relative in ('DungeonRoutes20260922/Config/catalog.json','DungeonThemedRoutes20261001/Config/catalog.json',
    'WarehouseContainers20261002/Config/catalog.json','DungeonSplitLevels20261001/Config/catalog.json',
    'DungeonStaffLiving20261002/Production20261002/Config/catalog.json','StationWorkshop20261003/Config/catalog.json',
    'SceneLootExpansion20261003/Config/catalog.json'):
    (PROJECT/'SourceAssets'/relative).write_text(text,encoding='utf8')
(ROOT/'Config/catalog.json').write_text(text,encoding='utf8')
write(PROJECT/'SourceAssets/DungeonTransitStation20260928/Config/module.json',station)
line.update(station_workshop_revision=4,freight_tool_bay_revision=2);write(linepath,line)
roompath=PROJECT/'SourceAssets/DungeonTransitStation20260928/Config/room.json';room=read(roompath);room['workshop_revision']=4;write(roompath,room)
report['stage']='maps_saved';record()
if original and original!=target and u.EditorAssetLibrary.does_asset_exist(original):u.EditorLoadingAndSavingUtils.load_map(original)
print('STATION_FIT_V4_MAPS_SAVED','ROOFS',len(roof_actors),'TOOL_PARTS',len(moved),flush=True)
