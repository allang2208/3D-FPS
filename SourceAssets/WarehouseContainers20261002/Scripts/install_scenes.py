"""Save production rules and add one reproducible container layout to the existing station line."""
import json,runpy,shutil,hashlib,math
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():raise RuntimeError('Background commandlet required')
build=json.loads((ROOT/'Receipts/native-build.json').read_text('utf-8-sig'))
if build.get('editor_exit')!=0 or build.get('game_exit')!=0:raise RuntimeError('Native lid implementation must be built before scene save')
assets=json.loads((ROOT/'Receipts/assets.json').read_text('utf8'))
if assets.get('stage')!='assets_saved':raise RuntimeError('Container assets must be saved first')
helpers=runpy.run_path(str(ROOT/'Scripts/extend_catalog.py'));rules=json.loads((ROOT/'Config/containers.json').read_text('utf8'))
AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
report=dict(stage='saving',maps={},tests_run=False,rendered=False,game_run=False,editor_opened=False,rewards_deferred=True)
RP=ROOT/'Receipts/install.json'
def record():RP.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
def backup(target):
    disk=PROJECT/'Content'/(target.removeprefix('/Game/')+'.umap');digest=hashlib.sha256(disk.read_bytes()).hexdigest()
    dst=ROOT/'Backup'/(disk.stem+'-'+digest[:12]+'.umap')
    if not dst.exists():shutil.copy2(disk,dst)
    return digest

target='/Game/GameMaps/L_Dungeon_Randomized';old=backup(target)
world=u.EditorLoadingAndSavingUtils.load_map(target)
generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
if len(generators)!=1:raise RuntimeError('Production generator unavailable')
g=generators[0];before=g.get_editor_property('module_catalog_json')
(ROOT/'Backup'/('catalog-'+hashlib.sha256(before.encode()).hexdigest()[:12]+'.json')).write_text(before,encoding='utf8')
catalog=helpers['extend'](json.loads(before))
material_paths=[]
for group in rules['groups']:
    for slot in group['slots']:
        for variant in slot['variants']:
            for c in variant['containers']:material_paths.extend(c.get('body_materials',[])+c.get('door_materials',[]))
paths=list(assets['materials'])+material_paths+[x['path'] for x in assets['meshes'].values()]
hard={a.get_path_name():a for a in g.get_editor_property('module_assets') if a}
for p in sorted(set(paths)):
    obj=u.load_asset(p)
    if not obj:raise RuntimeError('Container dependency unavailable '+p)
    hard[obj.get_path_name()]=obj
g.modify();g.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False));g.set_editor_property('module_assets',list(hard.values()))
if not u.EditorLoadingAndSavingUtils.save_map(world,target):raise RuntimeError('Production map save failed')
random_count=[sum(g['pick_count'][i]*len(g['slots'][0]['variants'][0]['containers']) for g in rules['groups']) for i in range(2)]
report['maps'][target]=dict(stage='map_saved',previous_sha256=old,random_count=random_count);record()
text=json.dumps(catalog,ensure_ascii=False,indent=2)
for relative in ('DungeonRoutes20260922/Config/catalog.json','DungeonThemedRoutes20261001/Config/catalog.json',
    'DungeonSplitLevels20261001/Config/catalog.json','DungeonStaffLiving20261002/Production20261002/Config/catalog.json'):
    (PROJECT/'SourceAssets'/relative).write_text(text,encoding='utf8')
(ROOT/'Config/catalog.json').write_text(text,encoding='utf8')
warehouse=next(m for m in catalog['modules'] if m['id']=='AbandonedCargoWarehouse')
(PROJECT/'SourceAssets/DungeonThemedRoutes20261001/Config/warehouse-module.json').write_text(json.dumps(warehouse,ensure_ascii=False,indent=2),encoding='utf8')

target='/Game/GameMaps/Design/L_FreightTransit_Theme_Subject';old=backup(target)
world=u.EditorLoadingAndSavingUtils.load_map(target)
if not world:raise RuntimeError('Existing station line unavailable')
line=json.loads((PROJECT/'SourceAssets/DungeonStationLine20261002/Config/line.json').read_text('utf8'))
pose=next(p for p in line['placements'] if p['id']=='AbandonedCargoWarehouse')
a=math.radians(pose['yaw']);origin=pose['position']
def pos(p):return u.Vector(p[0]*math.cos(a)-p[1]*math.sin(a)+origin[0],p[0]*math.sin(a)+p[1]*math.cos(a)+origin[1],p[2]+origin[2])
selected,containers=helpers['choose_preview'](rules)
owned_tag='Warehouse.Containers.Preview'
for actor in AA.get_all_level_actors():
    tags=[str(t) for t in actor.tags]
    if owned_tag in tags or ('SceneLootExpansion.Preview' in tags and 'AbandonedCargoWarehouse' in tags):AA.destroy_actor(actor)
existing={actor.get_actor_label():actor for actor in AA.get_all_level_actors()}
for i,p in enumerate(warehouse['parts']):
    slot=p.get('container_replace_slot')
    if not slot:continue
    label='StationLine_AbandonedCargoWarehouse_'+str(i);actor=existing.get(label)
    if slot in selected:
        if actor:AA.destroy_actor(actor)
    elif not actor:
        actor=AA.spawn_actor_from_class(u.StaticMeshActor,pos(p['position']),u.Rotator(pitch=p.get('pitch',0),yaw=pose['yaw']+p.get('yaw',0),roll=p.get('roll',0)))
        actor.set_actor_label(label);actor.set_folder_path('StationLine/AbandonedCargoWarehouse')
        actor.set_editor_property('tags',[u.Name('StationLine.Subject'),u.Name('AbandonedCargoWarehouse')])
        actor.static_mesh_component.set_static_mesh(u.load_asset(p['mesh']));actor.set_actor_scale3d(u.Vector(*p.get('scale',[1,1,1])))
        actor.static_mesh_component.set_collision_profile_name('BlockAll')
        for mi,mp in enumerate(p.get('materials',[])):actor.static_mesh_component.set_material(mi,u.load_asset(mp))
for c in containers:
    actor=AA.spawn_actor_from_class(u.ColdSteelSceneContainer,pos(c['position']),u.Rotator(pitch=0,yaw=pose['yaw']+c['yaw'],roll=0))
    actor.set_actor_label('WarehouseSearch_'+c['container_id']);actor.set_folder_path('StationLine/WarehouseContainers')
    actor.set_editor_property('tags',[*actor.tags,u.Name(owned_tag),u.Name('StationLine.Subject')])
    actor.set_editor_property('container_id','StationLine.'+c['container_id']);actor.set_editor_property('caption',c['caption'])
    actor.set_editor_property('storage_pages',c['storage_pages']);actor.set_editor_property('opened_yaw',c.get('opened_yaw',100.))
    actor.set_editor_property('opened_roll',c.get('opened_roll',105.))
    actor.set_editor_property('opening_motion',getattr(u.ColdSteelContainerMotion,c['opening_motion'].upper()))
    if c.get('drawer_travel'):actor.set_editor_property('drawer_travel',u.Vector(*c['drawer_travel']))
    actor.body.set_static_mesh(u.load_asset(c['body']));actor.door.set_static_mesh(u.load_asset(c['door']))
    actor.body.set_collision_profile_name('BlockAll');actor.door.set_collision_profile_name('NoCollision')
    actor.door_hinge.set_relative_location(u.Vector(*c['hinge']),False,False)
    for key,component in [('body_materials',actor.body),('door_materials',actor.door)]:
        for i,p in enumerate(c.get(key,[])):component.set_material(i,u.load_asset(p))
label='StationLine_ContainerOutline'
pp=next((a for a in AA.get_all_level_actors() if a.get_actor_label()==label),None)
if not pp:pp=AA.spawn_actor_from_class(u.PostProcessVolume,u.Vector())
pp.set_actor_label(label);pp.set_folder_path('StationLine/Environment');pp.set_editor_property('unbound',True);pp.set_editor_property('priority',1.)
settings=pp.get_editor_property('settings');blend=u.WeightedBlendable();blend.set_editor_property('weight',1.)
blend.set_editor_property('object',u.load_asset(rules['outline']));arr=u.WeightedBlendables();arr.set_editor_property('array',[blend])
settings.set_editor_property('weighted_blendables',arr);pp.set_editor_property('settings',settings)
if not u.EditorLoadingAndSavingUtils.save_map(world,target):raise RuntimeError('Station line container save failed')
report['maps'][target]=dict(stage='map_saved',previous_sha256=old,preview_seed=rules['preview_seed'],containers=len(containers),selected_slots=selected)
report['stage']='maps_saved';record()
reserve_count=sum(c['container_id'].startswith('CargoWarehouse.Reserve.') for c in containers)
line.update(warehouse_container_revision=rules['revision'],warehouse_preview_seed=rules['preview_seed'],warehouse_container_count=len(containers),
    warehouse_base_container_count=len(containers)-reserve_count,warehouse_additional_container_count=reserve_count)
(PROJECT/'SourceAssets/DungeonStationLine20261002/Config/line.json').write_text(json.dumps(line,ensure_ascii=False,indent=2),encoding='utf8')
cp=PROJECT/'SourceAssets/DungeonCargoWarehouse20261001/Config/room.json';cfg=json.loads(cp.read_text('utf8'))
cfg.update(container_revision=rules['revision'],container_count=random_count,container_author='SourceAssets/WarehouseContainers20261002',container_rewards_deferred=True)
cp.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf8')
print('WAREHOUSE_CONTAINER_SCENES_SAVED',len(containers),flush=True)
