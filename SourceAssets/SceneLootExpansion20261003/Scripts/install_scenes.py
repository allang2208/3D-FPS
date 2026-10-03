"""Save additional search bays and the staff restroom chest using existing assets."""
import copy,hashlib,json,math,runpy,shutil
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
read=lambda p:json.loads(p.read_text('utf-8-sig'))
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and not globals().get('SCENE_LOOT_EXISTING_EDITOR_INSTALL',False):raise RuntimeError('Commandlet or existing editor bridge required')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Preserve the active game session before scene save')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()}
if dirty:raise RuntimeError('Preserve unsaved maps before scene save: '+str(sorted(dirty)))
AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
original=editor.get_editor_world().get_path_name().split('.')[0] if editor and editor.get_editor_world() else ''
helpers=runpy.run_path(str(ROOT/'Scripts/extend_catalog.py'));rules=helpers['rules']()
report=dict(stage='saving',maps={},tests_run=False,rendered=False,game_run=False,editor_opened=False,
    native_changes=False,assets_imported=False,reuses_saved_assets=True,rewards_deferred=True)
receipt=ROOT/'Receipts/install.json'

def record():receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
def write(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
def backup(target):
    path=PROJECT/'Content'/(target.removeprefix('/Game/')+'.umap')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    dst=ROOT/'Backup'/(path.stem+'-'+digest[:12]+'.umap')
    if not dst.exists():shutil.copy2(path,dst)
    return digest

target='/Game/GameMaps/L_Dungeon_Randomized';old=backup(target)
world=u.EditorLoadingAndSavingUtils.load_map(target)
generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
if len(generators)!=1:raise RuntimeError('Production generator unavailable')
generator=generators[0];before=generator.get_editor_property('module_catalog_json')
(ROOT/'Backup'/('catalog-'+hashlib.sha256(before.encode()).hexdigest()[:12]+'.json')).write_text(before,encoding='utf8')
catalog=helpers['extend'](json.loads(before))
hard={a.get_path_name():a for a in generator.get_editor_property('module_assets') if a}
for path in sorted(set(helpers['asset_paths'](rules))):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Required saved asset unavailable: '+path)
    hard[asset.get_path_name()]=asset
generator.modify();generator.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
generator.set_editor_property('module_assets',list(hard.values()))
if not u.EditorLoadingAndSavingUtils.save_map(world,target):raise RuntimeError('Production map save failed')
report['maps'][target]=dict(stage='map_saved',previous_sha256=old,
    freight_containers=rules['freight_count'],warehouse_additional=rules['warehouse_additional_count'],
    warehouse_total=rules['warehouse_total_count'],restroom_chest=rules['restroom_chest'])
record()

target='/Game/GameMaps/Design/L_FreightTransit_Theme_Subject';old=backup(target)
world=u.EditorLoadingAndSavingUtils.load_map(target)
if not world:raise RuntimeError('Current station line unavailable')
linepath=PROJECT/'SourceAssets/DungeonStationLine20261002/Config/line.json';line=read(linepath)
owned_tag='SceneLootExpansion.Preview'
for actor in AA.get_all_level_actors():
    tags=[str(t) for t in actor.tags]
    warehouse_reserve=isinstance(actor,u.ColdSteelSceneContainer) and str(actor.get_editor_property('container_id')).startswith('StationLine.CargoWarehouse.Reserve.')
    if owned_tag in tags or warehouse_reserve:AA.destroy_actor(actor)
selected={}
for module_id,groups in [('FreightTransfer_WarehouseLink',rules['freight_groups']),('AbandonedCargoWarehouse',rules['warehouse_groups'])]:
    pose=next(p for p in line['placements'] if p['id']==module_id)
    a=math.radians(pose['yaw']);origin=pose['position']
    def pos(p):return u.Vector(p[0]*math.cos(a)-p[1]*math.sin(a)+origin[0],p[0]*math.sin(a)+p[1]*math.cos(a)+origin[1],p[2]+origin[2])
    containers=helpers['choose'](groups,rules['preview_seed']+(1 if module_id=='AbandonedCargoWarehouse' else 0))
    selected[module_id]=[]
    for c in containers:
        actor=AA.spawn_actor_from_class(u.ColdSteelSceneContainer,pos(c['position']),u.Rotator(pitch=0,yaw=pose['yaw']+c['yaw'],roll=0))
        actor.set_actor_label('SceneLoot_'+c['container_id']);actor.set_folder_path('StationLine/AdditionalContainers/'+module_id)
        actor.set_editor_property('tags',[*actor.tags,u.Name(owned_tag),u.Name('StationLine.Subject'),u.Name(module_id)])
        actor.set_editor_property('container_id','StationLine.'+c['container_id']);actor.set_editor_property('caption',c['caption'])
        actor.set_editor_property('storage_pages',c['storage_pages']);actor.set_editor_property('opened_yaw',c.get('opened_yaw',100.))
        actor.set_editor_property('opened_roll',c.get('opened_roll',105.));actor.set_editor_property('initial_open_fraction',c.get('initial_open_fraction',0.))
        actor.set_editor_property('opening_motion',getattr(u.ColdSteelContainerMotion,c['opening_motion'].upper()))
        if c.get('drawer_travel'):actor.set_editor_property('drawer_travel',u.Vector(*c['drawer_travel']))
        actor.body.set_static_mesh(u.load_asset(c['body']));actor.door.set_static_mesh(u.load_asset(c['door']))
        actor.body.set_collision_profile_name('BlockAll');actor.door.set_collision_profile_name('NoCollision')
        actor.door_hinge.set_relative_location(u.Vector(*c['hinge']),False,False)
        for key,component in [('body_materials',actor.body),('door_materials',actor.door)]:
            for i,path in enumerate(c.get(key,[])):component.set_material(i,u.load_asset(path))
        selected[module_id].append(dict(id=c['container_id'],position=c['position'],yaw=c['yaw']))
if not u.EditorLoadingAndSavingUtils.save_map(world,target):raise RuntimeError('Station line save failed')
extra_warehouse=len(selected['AbandonedCargoWarehouse']);freight_count=len(selected['FreightTransfer_WarehouseLink'])
base_warehouse_count=line.get('warehouse_base_container_count',line.get('warehouse_container_count',9))
report['maps'][target]=dict(stage='map_saved',previous_sha256=old,preview_seed=rules['preview_seed'],
    freight_containers=freight_count,warehouse_added=extra_warehouse,warehouse_total=base_warehouse_count+extra_warehouse,selected=selected)
record()

text=json.dumps(catalog,ensure_ascii=False,indent=2)
for relative in ('DungeonRoutes20260922/Config/catalog.json','DungeonThemedRoutes20261001/Config/catalog.json',
    'WarehouseContainers20261002/Config/catalog.json','DungeonSplitLevels20261001/Config/catalog.json',
    'DungeonStaffLiving20261002/Production20261002/Config/catalog.json','StationWorkshop20261003/Config/catalog.json'):
    (PROJECT/'SourceAssets'/relative).write_text(text,encoding='utf8')
(ROOT/'Config/catalog.json').write_text(text,encoding='utf8')
warehouse=next(m for m in catalog['modules'] if m['id']=='AbandonedCargoWarehouse')
write(PROJECT/'SourceAssets/DungeonThemedRoutes20261001/Config/warehouse-module.json',warehouse)
container_rules_path=PROJECT/'SourceAssets/WarehouseContainers20261002/Config/containers.json'
write(container_rules_path,helpers['expand_warehouse'](read(container_rules_path)))
for relative in ('DungeonStaffLiving20261002/Production20261002/Config/modules.json','DungeonStaffLiving20261002/Config/modules-draft.json'):
    path=PROJECT/'SourceAssets'/relative;data=read(path)
    module=next(m for m in data['modules'] if m['id']=='StaffRecreation')
    module['props']=[p for p in module.get('props',[]) if p.get('identity')!='staff_activity_restroom']+[copy.deepcopy(rules['restroom_chest'])]
    data['restroom_chest_revision']=1;write(path,data)
line.update(scene_loot_expansion_revision=1,freight_container_count=freight_count,
    warehouse_container_revision=2,warehouse_base_container_count=base_warehouse_count,
    warehouse_additional_container_count=extra_warehouse,warehouse_container_count=base_warehouse_count+extra_warehouse,
    additional_container_preview_seed=rules['preview_seed'])
write(linepath,line)
roompath=PROJECT/'SourceAssets/DungeonCargoWarehouse20261001/Config/room.json';room=read(roompath)
room.update(container_revision=2,container_count=[12,17],container_extension_author='SourceAssets/SceneLootExpansion20261003')
write(roompath,room)
report.update(stage='maps_saved',staff_preview='Retired accepted samples remain archived; chest saved in production StaffRecreation module')
record()
if original and original!=target and u.EditorAssetLibrary.does_asset_exist(original):u.EditorLoadingAndSavingUtils.load_map(original)
print('SCENE_LOOT_MAPS_SAVED','FREIGHT',freight_count,'WAREHOUSE_ADDED',extra_warehouse,'STAFF_RESTROOM_CHEST',1,flush=True)
