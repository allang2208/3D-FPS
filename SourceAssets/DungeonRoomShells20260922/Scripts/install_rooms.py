"""Replace only the repeated B corridor with three distinct architectural rooms."""
import gc,json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/'Config/rooms.json').read_text(encoding='utf-8'))
MAN=json.loads((ROOT/'Authored/manifest.json').read_text(encoding='utf-8'))
IM=json.loads((ROOT/'Receipts/import.json').read_text(encoding='utf-8'))
TARGET=CFG['target_map'];ARCHIVE='/Game/Dungeons/RoomShells20260922/Archive/L_Dungeon_ConnectionProof'
E=u.EditorAssetLibrary;AA=u.get_editor_subsystem(u.EditorActorSubsystem);ED=u.get_editor_subsystem(u.LevelEditorSubsystem);UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if UE.get_game_world():raise RuntimeError('Preserve running play session')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
if IM['stage']!='meshes_saved':raise RuntimeError('Finish all room mesh imports first')
receipt={'stage':'preparing','target':TARGET,'archive':ARCHIVE,'rooms':[r['id'] for r in CFG['rooms']],'tests_run':False,'runtime_random_generation':False}
def write():(ROOT/'Receipts/install.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
write()
if not E.does_asset_exist(ARCHIVE):
    backup=E.duplicate_asset(TARGET,ARCHIVE)
    if not backup or not E.save_loaded_asset(backup,False):raise RuntimeError('Cannot preserve connection proof')
    del backup;gc.collect()
if not UE.get_editor_world() or UE.get_editor_world().get_path_name().split('.')[0]!=TARGET:
    if not ED.load_level(TARGET):raise RuntimeError('Cannot open owned map')
receipt['stage']='installing';write()
removed=0
for actor in list(AA.get_all_level_actors()):
    if actor.get_actor_label().startswith(('DGN_B_','DGN_RS_')):
        if not AA.destroy_actor(actor):raise RuntimeError('Cannot replace owned actor '+actor.get_actor_label())
        removed+=1
def position(origin,local=(0,0,0)):return u.Vector((origin[0]+local[0])*100,-(origin[1]+local[1])*100,(origin[2]+local[2])*100)
def own(actor,label,room):
    actor.modify();actor.set_actor_label('DGN_RS_'+label);actor.set_folder_path('DungeonRoomShells/'+room)
    actor.set_editor_property('tags',[u.Name('DungeonRoomShells20260922'),u.Name('DungeonRoom_'+room)])
    return actor
for item in MAN['objects']:
    a=own(AA.spawn_actor_from_class(u.StaticMeshActor,position(item['origin_m']),u.Rotator(pitch=0,yaw=0,roll=0)),item['name'].removeprefix('SM_RS_'),item['room'])
    c=a.static_mesh_component;c.modify();c.set_static_mesh(u.load_asset(IM['meshes'][item['name']]))
    c.set_mobility(u.ComponentMobility.STATIC);c.set_collision_profile_name('BlockAll' if item['collision'] else 'NoCollision')
for room in CFG['rooms']:
    trench=room.get('trench',{});hazard=trench.get('hazard')
    if not hazard:continue
    klass=u.load_class(None,hazard['class'])
    if not klass:raise RuntimeError('Build native dungeon hazard class before scene installation')
    x0,y0,x1,y1=trench['rect']
    a=own(AA.spawn_actor_from_class(klass,position(room['origin_m'],((x0+x1)/2,(y0+y1)/2,-trench['depth']))),room['id']+'_CorrosivePus',room['id'])
    a.set_editor_property('half_size',u.Vector2D(*hazard['half_size_cm']))
    a.set_editor_property('tags',list(a.tags)+[u.Name('CorrosivePus'),u.Name('DungeonPermanentHazard')])
    a.set_editor_property('damage_per_pulse',hazard['damage']);a.set_editor_property('damage_interval',hazard['interval'])
    c=a.get_component_by_class(u.StaticMeshComponent);c.modify();c.set_static_mesh(u.load_asset(hazard['mesh']))
    c.set_material(0,u.load_asset(hazard['material']));c.set_collision_profile_name('NoCollision')
    c.set_mobility(u.ComponentMobility.MOVABLE);c.set_editor_property('evaluate_world_position_offset',True);c.set_cast_shadow(False)
    c.set_editor_property('visible_in_ray_tracing',False);c.set_editor_property('affect_distance_field_lighting',False)
for room in CFG['rooms']:
    recipe=room.get('pipe_slime',{})
    for item in recipe.get('objects',[]):
        surface=item['half_size_cm'] is not None
        klass=u.load_class(None,'/Script/FPSGAME.DungeonPusChannel') if surface else u.StaticMeshActor
        a=own(AA.spawn_actor_from_class(klass,position(room['origin_m'],item['local_m'])),room['id']+'_'+item['name'].removeprefix('SM_'),room['id'])
        if surface:
            h=item['half_size_cm'];a.set_editor_property('half_size',u.Vector2D(h[0]*.95,h[1]*.95));a.set_editor_property('damage_per_pulse',recipe['damage']);a.set_editor_property('damage_interval',recipe['interval'])
            if item.get('radial_footprint'):a.set_editor_property('tags',list(a.tags)+[u.Name('PusRadialFootprint')])
        c=a.get_component_by_class(u.StaticMeshComponent);c.modify();c.set_static_mesh(u.load_asset(item['destination']+'/'+item['name']));c.set_collision_profile_name('NoCollision');c.set_cast_shadow(False)
        if item.get('material_override'):c.set_material(0,u.load_asset(item['material_override']))
        c.set_mobility(u.ComponentMobility.MOVABLE);c.set_editor_property('evaluate_world_position_offset',True);c.set_editor_property('visible_in_ray_tracing',False);c.set_editor_property('affect_distance_field_lighting',False)
for index,lamp in enumerate(MAN['lights']):
    a=own(AA.spawn_actor_from_class(u.PointLight,position(lamp['origin_m'],lamp['local_m'])),'Light_'+str(index),lamp['room'])
    c=a.get_component_by_class(u.PointLightComponent);c.modify();c.set_mobility(u.ComponentMobility.MOVABLE)
    c.set_editor_property('intensity_units',u.LightUnits.LUMENS);c.set_intensity(lamp['lumens']);c.set_attenuation_radius(lamp['radius_cm'])
    c.set_light_color(u.LinearColor(1,.64,.36,1) if lamp['warm'] else u.LinearColor(.73,.84,1,1))
    c.set_editor_property('source_radius',5);c.set_editor_property('source_length',60);c.set_cast_shadows(True)
for index,anchor in enumerate(MAN['anchors']):
    a=own(AA.spawn_actor_from_class(u.TargetPoint,position(anchor['origin_m'],anchor['at'])),'Anchor_'+anchor['role']+'_'+str(index),anchor['room']+'/Anchors')
    a.set_actor_hidden_in_game(True)
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
owned=[p for p in dirty if '/gamemaps/l_dungeon_authoredexpansion' in p.get_name().lower()]
if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('Room external actor save failed')
if not ED.save_current_level():raise RuntimeError('Map save failed')
receipt.update(stage='map_saved',removed_owned_actors=removed,meshes=len(MAN['objects']),lights=len(MAN['lights']),anchors=len(MAN['anchors']),saved_owned_packages=len(owned),floor_datum_cm=94)
write()
# Present the newly added room in the editor without starting gameplay or rendering a preview.
if not globals().get('HEADLESS_AUTHORING'):
    u.EditorLevelLibrary.set_level_viewport_camera_info(u.Vector(2400,-1930,259),u.Rotator(pitch=-3,yaw=-67,roll=0))
print('DISTINCT_ROOM_SHELLS_INSTALLED',json.dumps(receipt))
