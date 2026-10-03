"""Save the production station extension and add it to the existing freight-line subject."""
import hashlib,json,math,runpy,shutil
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
read=lambda p:json.loads(p.read_text('utf-8-sig'))
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and not globals().get('STATION_WORKSHOP_EXISTING_EDITOR_INSTALL',False):raise RuntimeError('Background commandlet or existing editor bridge required')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Preserve the current game session before saving station maps')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()}
if dirty:raise RuntimeError('Preserve unsaved maps before station installation: '+str(sorted(dirty)))
build=read(ROOT/'Receipts/native-build.json')
if build.get('editor_exit')!=0 or build.get('game_exit')!=0:raise RuntimeError('Native workshop assembly must be built before scene save')
assets=read(ROOT/'Receipts/assets.json')
if assets.get('stage')!='assets_saved':raise RuntimeError('Workshop assets must be saved before scene save')
helpers=runpy.run_path(str(ROOT/'Scripts/extend_catalog.py'));rules=read(ROOT/'Config/workshop.json')
AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
report=dict(stage='saving',maps={},tests_run=False,rendered=False,game_run=False,editor_opened=False,rewards_deferred=True)
RP=ROOT/'Receipts/install.json'
def record():RP.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
def backup(target):
    disk=PROJECT/'Content'/(target.removeprefix('/Game/')+'.umap');digest=hashlib.sha256(disk.read_bytes()).hexdigest()
    dest=ROOT/'Backup'/(disk.stem+'-'+digest[:12]+'.umap')
    if not dest.exists():shutil.copy2(disk,dest)
    return digest

target='/Game/GameMaps/L_Dungeon_Randomized';old=backup(target)
world=u.EditorLoadingAndSavingUtils.load_map(target)
generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
if len(generators)!=1:raise RuntimeError('Production generator unavailable')
generator=generators[0];before=generator.get_editor_property('module_catalog_json')
(ROOT/'Backup'/('catalog-'+hashlib.sha256(before.encode()).hexdigest()[:12]+'.json')).write_text(before,encoding='utf8')
catalog=helpers['extend'](json.loads(before),rules)
hard={a.get_path_name():a for a in generator.get_editor_property('module_assets') if a}
for path in sorted(set(helpers['asset_paths'](rules))|set(assets['materials'])):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Workshop dependency unavailable '+path)
    hard[asset.get_path_name()]=asset
generator.modify();generator.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
generator.set_editor_property('module_assets',list(hard.values()))
if not u.EditorLoadingAndSavingUtils.save_map(world,target):raise RuntimeError('Production workshop map save failed')
report['maps'][target]=dict(stage='map_saved',previous_sha256=old,dressing_variants=3,container_count=[6,7],
    revision=rules['revision'],runtime_actors=len(rules.get('runtime_actors',[])),chests=len(rules.get('props',[])));record()
text=json.dumps(catalog,ensure_ascii=False,indent=2)
for relative in ('DungeonRoutes20260922/Config/catalog.json','DungeonThemedRoutes20261001/Config/catalog.json',
 'WarehouseContainers20261002/Config/catalog.json',
 'DungeonSplitLevels20261001/Config/catalog.json','DungeonStaffLiving20261002/Production20261002/Config/catalog.json'):
    (PROJECT/'SourceAssets'/relative).write_text(text,encoding='utf8')
(ROOT/'Config/catalog.json').write_text(text,encoding='utf8')
station=next(m for m in catalog['modules'] if m['id']=='AbandonedTransitStation')
(PROJECT/'SourceAssets/DungeonTransitStation20260928/Config/module.json').write_text(json.dumps(station,ensure_ascii=False,indent=2),encoding='utf8')

target='/Game/GameMaps/Design/L_FreightTransit_Theme_Subject';old=backup(target)
world=u.EditorLoadingAndSavingUtils.load_map(target)
if not world:raise RuntimeError('Existing station-line subject unavailable')
linepath=PROJECT/'SourceAssets/DungeonStationLine20261002/Config/line.json';line=read(linepath)
pose=next(p for p in line['placements'] if p['id']=='AbandonedTransitStation');angle=math.radians(pose['yaw']);origin=pose['position']
def position(p):return u.Vector(p[0]*math.cos(angle)-p[1]*math.sin(angle)+origin[0],p[0]*math.sin(angle)+p[1]*math.cos(angle)+origin[1],p[2]+origin[2])
tag='Station.Workshop.Preview'
for actor in AA.get_all_level_actors():
    if tag in [str(t) for t in actor.tags]:AA.destroy_actor(actor)
text_rebound=0;geometry_rebound=0
for actor in AA.get_all_level_actors():
    for component in actor.get_components_by_class(u.StaticMeshComponent):
        mesh=component.static_mesh
        replacement=rules.get('text_asset_remap',{}).get(mesh.get_path_name().split('.')[0] if mesh else '')
        if replacement:
            component.modify();component.set_static_mesh(u.load_asset(replacement));text_rebound+=1
        geometry_replacement=rules.get('geometry_asset_remap',{}).get(mesh.get_path_name().split('.')[0] if mesh else '')
        if geometry_replacement:
            component.modify();component.set_static_mesh(u.load_asset(geometry_replacement));geometry_rebound+=1
def named(actor,label):
    if not actor:raise RuntimeError('Workshop actor spawn failed '+label)
    actor.set_actor_label('StationWorkshop_'+label);actor.set_folder_path('StationLine/StationWorkshop')
    actor.set_editor_property('tags',[*actor.tags,u.Name(tag),u.Name('StationLine.Subject')]);return actor
parts,containers=helpers['preview'](rules)
for i,p in enumerate(parts):
    asset=u.load_asset(p['mesh'])
    if not asset:raise RuntimeError('Workshop mesh unavailable '+p['mesh'])
    actor=named(AA.spawn_actor_from_class(u.StaticMeshActor,position(p['position']),u.Rotator(pitch=0,yaw=pose['yaw']+p['yaw'],roll=0)),str(i)+'_'+asset.get_name())
    c=actor.static_mesh_component;c.set_static_mesh(asset);c.set_mobility(u.ComponentMobility.STATIC)
    c.set_collision_profile_name('BlockAll' if p['collision'] else 'NoCollision')
    actor.set_actor_scale3d(u.Vector(*p['scale']))
    for mi,mp in enumerate(p['materials']):c.set_material(mi,u.load_asset(mp))
for c in containers:
    actor=named(AA.spawn_actor_from_class(u.ColdSteelSceneContainer,position(c['position']),u.Rotator(pitch=0,yaw=pose['yaw']+c['yaw'],roll=0)),c['container_id'])
    actor.set_editor_property('container_id','StationLine.'+c['container_id']);actor.set_editor_property('caption',c['caption'])
    actor.set_editor_property('storage_pages',c['storage_pages']);actor.set_editor_property('opened_yaw',c.get('opened_yaw',100.))
    actor.set_editor_property('opened_roll',c.get('opened_roll',105.));actor.set_editor_property('initial_open_fraction',c.get('initial_open_fraction',0.))
    actor.set_editor_property('opening_motion',getattr(u.ColdSteelContainerMotion,c['opening_motion'].upper()))
    if c.get('drawer_travel'):actor.set_editor_property('drawer_travel',u.Vector(*c['drawer_travel']))
    actor.body.set_static_mesh(u.load_asset(c['body']));actor.door.set_static_mesh(u.load_asset(c['door']))
    actor.body.set_collision_profile_name('BlockAll');actor.door.set_collision_profile_name('NoCollision')
    actor.door_hinge.set_relative_location(u.Vector(*c['hinge']),False,False)
for spec in rules.get('runtime_actors',[]):
    rot=u.Rotator(pitch=0,yaw=pose['yaw']+spec['yaw'],roll=0)
    if spec['type']=='glass_window':
        actor=named(AA.spawn_actor_from_class(u.WardGlassWindow,position(spec['position']),rot),spec['id'])
        pane=actor.glass_pane;pane.set_static_mesh(u.load_asset(spec['pane']))
        pane.set_editor_property('fracture_mesh',u.load_asset(spec['fracture']))
        pane.set_editor_property('fracture_material',u.load_asset(spec['fracture_material']))
        pane.set_editor_property('impact_particles',u.load_asset(spec['impact_particles']))
        pane.set_editor_property('break_sound',u.load_asset(spec['sound']))
        pane.set_editor_property('pane_dimensions',u.Vector(*spec['dimensions_cm']))
    elif spec['type']=='solid_door':
        actor=named(AA.spawn_actor_from_class(u.ColdSteelDoor,position(spec['position']),rot),spec['id'])
        positive=spec['positive_hinge'];actor.set_editor_property('hinge_on_positive_y',positive)
        actor.set_editor_property('open_angle_degrees',85.);actor.set_editor_property('open_seconds',spec['open_seconds'])
        actor.set_editor_property('auto_close_seconds',spec['auto_close_seconds'])
        components={c.get_name():c for c in actor.get_components_by_class(u.SceneComponent)}
        leaf=components['DoorLeaf'];frame=components['DoorFrame'];hinge=components['DoorHinge']
        frame.set_static_mesh(None);frame.set_collision_profile_name('NoCollision');frame.set_visibility(False,True)
        leaf.set_static_mesh(u.load_asset(spec['leaf']));leaf.set_mobility(u.ComponentMobility.MOVABLE);leaf.set_collision_profile_name('BlockAll')
        width=111. if spec['id']=='PersonnelEntrance' else 105.;sign=1 if positive else -1
        hinge.set_relative_location(u.Vector(0,sign*width/2,0),False,False)
        leaf.set_relative_location(u.Vector(0,-sign*width/2,0),False,False)
        leaf.set_relative_rotation(u.Rotator(pitch=0,yaw=180 if positive else 0,roll=0),False,False)
for i,p in enumerate(rules.get('props',[])):
    chest_class=u.load_asset(rules['preview_chest_blueprint']).generated_class()
    actor=named(AA.spawn_actor_from_class(chest_class,position(p['position']),u.Rotator(pitch=0,yaw=pose['yaw']+p['yaw'],roll=0)),'UpperPlatformChest_'+str(i))
    actor.set_actor_scale3d(u.Vector(*p['scale']));actor.set_editor_property('tags',[*actor.tags,
        u.Name('DungeonTreasureChest'),u.Name('FutureTreasureLoot'),u.Name('DungeonTreasure.HubTest'),
        u.Name('DungeonChestClaim.StationLine.UpperPlatform')])
    c=actor.skeletal_mesh_component;c.set_skeletal_mesh_asset(u.load_asset(p['skeletal_mesh']))
    c.set_mobility(u.ComponentMobility.MOVABLE);c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
    c.set_animation_mode(u.AnimationMode.ANIMATION_SINGLE_NODE);c.play_animation(u.load_asset(p['closed_animation']),False)
    anim=c.get_editor_property('animation_data');anim.set_editor_property('saved_position',u.load_asset(p['closed_animation']).get_play_length())
    anim.set_editor_property('saved_play_rate',0.);anim.set_editor_property('saved_playing',False);c.set_editor_property('animation_data',anim)
    # The saved Blueprint supplies an owned box for production-equivalent interaction traces.
    collision=actor.get_component_by_class(u.BoxComponent)
    collision.set_box_extent(u.Vector(*p['collision_extent']),False)
    collision.set_relative_location(u.Vector(*p['collision_center']),False,False);collision.set_collision_profile_name('BlockAll')
for i,l in enumerate(rules['lights']):
    actor=named(AA.spawn_actor_from_class(u.PointLight,position(l['position'])),'Light_'+str(i))
    c=actor.get_component_by_class(u.PointLightComponent);c.set_mobility(u.ComponentMobility.MOVABLE)
    c.set_editor_property('intensity_units',u.LightUnits.LUMENS);c.set_intensity(l['intensity'])
    c.set_editor_property('attenuation_radius',l['radius']);c.set_editor_property('cast_shadows',l['cast_shadows'])
    c.set_editor_property('max_draw_distance',l['max_draw_distance_cm']);c.set_editor_property('max_distance_fade_range',l['fade_range_cm'])
    c.set_editor_property('indirect_lighting_intensity',.6);c.set_light_color(u.LinearColor(*l['color'],1))
if not any(a.get_actor_label()=='StationLine_ContainerOutline' for a in AA.get_all_level_actors()):
    outline=u.load_asset(rules['outline'])
    if not outline:raise RuntimeError('Existing focus outline unavailable')
    pp=named(AA.spawn_actor_from_class(u.PostProcessVolume,u.Vector()),'Outline');pp.set_editor_property('unbound',True)
    pp.set_editor_property('priority',1.);settings=pp.get_editor_property('settings')
    blend=u.WeightedBlendable();blend.set_editor_property('weight',1.);blend.set_editor_property('object',outline)
    arr=u.WeightedBlendables();arr.set_editor_property('array',[blend]);settings.set_editor_property('weighted_blendables',arr);pp.set_editor_property('settings',settings)
if not u.EditorLoadingAndSavingUtils.save_map(world,target):raise RuntimeError('Station-line workshop map save failed')
report['maps'][target]=dict(stage='map_saved',previous_sha256=old,variant=rules['preview_variant'],
    static_actors=len(parts),containers=len(containers),lights=len(rules['lights']),revision=rules['revision'],
    runtime_actors=len(rules.get('runtime_actors',[])),chests=len(rules.get('props',[])),existing_label_components_rebound=text_rebound,
    existing_geometry_components_rebound=geometry_rebound)
report['stage']='maps_saved';record()
line.update(station_workshop_revision=rules['revision'],station_workshop_variant=rules['preview_variant'],station_workshop_containers=len(containers))
linepath.write_text(json.dumps(line,ensure_ascii=False,indent=2),encoding='utf8')
cp=PROJECT/'SourceAssets/DungeonTransitStation20260928/Config/room.json';cfg=read(cp)
cfg.update(workshop_extension='SourceAssets/StationWorkshop20261003',workshop_revision=rules['revision'])
cp.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf8')
print('STATION_WORKSHOP_MAPS_SAVED',len(parts),len(containers),flush=True)
