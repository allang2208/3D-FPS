"""Update owned room actors in place; move the existing statue with its side room."""
import unreal as u,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ROOMS=ROOT.parent/'DungeonRoomShells20260922';BASE='/Game/Dungeons/CombatExpansion20260922'
CFG=json.loads((ROOT/'Config/rooms.json').read_text(encoding='utf-8'));MAN=json.loads((ROOMS/'Authored/manifest.json').read_text());FLUID=json.loads((ROOT/'Authored/fluids.json').read_text());IM=json.loads((ROOT/'Receipts/meshes.json').read_text())
AA=u.get_editor_subsystem(u.EditorActorSubsystem);ED=u.get_editor_subsystem(u.LevelEditorSubsystem);UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if UE.get_game_world():raise RuntimeError('End current play before scene installation')
target=CFG['target_map']
if UE.get_editor_world().get_path_name().split('.')[0]!=target:
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved current map before dungeon integration')
    if not ED.load_level(target):raise RuntimeError('Cannot open the authored dungeon map')
if IM['stage']!='meshes_saved':raise RuntimeError('Finish mesh authoring/import first')
actors={}
for a in AA.get_all_level_actors():actors.setdefault(a.get_actor_label(),[]).append(a)
changed=[];packages=[]
def own(a):
    a.modify();return a
def position(origin,local=(0,0,0)):return u.Vector((origin[0]+local[0])*100,-(origin[1]+local[1])*100,(origin[2]+local[2])*100)
def actor(label,klass,room,where):
    matches=actors.get(label,[])
    if len(matches)>1:raise RuntimeError('Duplicate owned actor '+label)
    a=own(matches[0] if matches else AA.spawn_actor_from_class(klass,where,u.Rotator(pitch=0,yaw=0,roll=0)))
    a.set_actor_label(label);a.set_folder_path('DungeonRoomShells/'+room);a.set_actor_location(where,False,True)
    a.set_editor_property('tags',list(set(list(a.tags)+[u.Name('DungeonRoomShells20260922'),u.Name('DungeonRoom_'+room)])));changed.append(label)
    return a
for item in MAN['objects']:
    label='DGN_RS_'+item['name'].removeprefix('SM_RS_');a=actor(label,u.StaticMeshActor,item['room'],position(item['origin_m']))
    c=a.static_mesh_component;c.modify();c.set_static_mesh(u.load_asset(IM['meshes'][item['name']]));c.set_editor_property('override_materials',[]);c.set_mobility(u.ComponentMobility.STATIC);c.set_collision_profile_name('BlockAll' if item['collision'] else 'NoCollision')
for i,lamp in enumerate(MAN['lights']):
    a=actor('DGN_RS_Light_'+str(i),u.PointLight,lamp['room'],position(lamp['origin_m'],lamp['local_m']));c=a.get_component_by_class(u.PointLightComponent);c.modify();c.set_mobility(u.ComponentMobility.MOVABLE)
    c.set_editor_property('intensity_units',u.LightUnits.LUMENS);c.set_intensity(lamp['lumens']);c.set_attenuation_radius(lamp['radius_cm']);c.set_light_color(u.LinearColor(1,.64,.36,1) if lamp['warm'] else u.LinearColor(.73,.84,1,1));c.set_editor_property('source_radius',5);c.set_editor_property('source_length',60);c.set_cast_shadows(True)
for i,anchor in enumerate(MAN['anchors']):
    a=actor('DGN_RS_Anchor_'+anchor['role']+'_'+str(i),u.TargetPoint,anchor['room'],position(anchor['origin_m'],anchor['at']));a.set_actor_hidden_in_game(True)

hazard=u.load_class(None,'/Script/FPSGAME.DungeonPusChannel')
if not hazard:raise RuntimeError('Existing dungeon damage actor is unavailable')
dr=CFG['rooms'][1]
for item in FLUID['objects']:
    is_surface=item['half_size_cm'] is not None;name=item['name'];suffix='CorrosivePus' if name=='SM_PusChannelFluid' else name.removeprefix('SM_')
    a=actor('DGN_RS_Drainage_'+suffix,hazard if is_surface else u.StaticMeshActor,'Drainage',position(dr['origin_m'],item['local_m']))
    if is_surface:
        half=item['half_size_cm'];a.set_editor_property('half_size',u.Vector2D(half[0]-(4 if 'Puddle' in name else 0),half[1]-(4 if 'Puddle' in name else 0)));a.set_editor_property('damage_per_pulse',8);a.set_editor_property('damage_interval',.5)
        a.set_editor_property('tags',list(a.tags)+[u.Name('CorrosivePus'),u.Name('DungeonPermanentHazard')])
    c=a.get_component_by_class(u.StaticMeshComponent);c.modify();c.set_static_mesh(u.load_asset(IM['meshes'][name]));c.set_editor_property('override_materials',[]);c.set_collision_profile_name('NoCollision');c.set_cast_shadow(False);c.set_mobility(u.ComponentMobility.MOVABLE)
    c.set_editor_property('evaluate_world_position_offset',True);c.set_editor_property('visible_in_ray_tracing',False);c.set_editor_property('affect_distance_field_lighting',False)

# Use the original captured location on retries so a partial integration cannot shift twice.
sys.path.insert(0,str(ROOT/'Scripts'));from layout import warp,OLD
before=json.loads((ROOT/'Receipts/scene-before.json').read_text());old=OLD['rooms'][2];new=CFG['rooms'][2]
for data in before['actors']:
    if data['label']!='DGN_Prop_GoddessStatue_01':continue
    matches=actors.get(data['label'],[])
    if len(matches)!=1:raise RuntimeError('Keep the user statue until its actor is uniquely available')
    a=own(matches[0]);p=data['location'];local=[p[0]/100-old['origin_m'][0],-p[1]/100-old['origin_m'][1],p[2]/100-old['origin_m'][2]];local=warp(old,new['combat_expansion_factor'],local)
    a.set_actor_location(position(new['origin_m'],local),False,True);changed.append(data['label'])

# External actor packages are saved explicitly. Do not save unrelated dirty project packages.
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
owned=[p for p in dirty if '/gamemaps/l_dungeon_authoredexpansion' in p.get_name().lower()]
if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('Cannot save authored dungeon actors')
if not ED.save_current_level():raise RuntimeError('Cannot save the dungeon map')
receipt=dict(stage='map_saved',map=target,updated=changed,saved_packages=len(owned),area_budget=json.loads((ROOT/'Config/area-budget.json').read_text()),tests_run=False)
(ROOT/'Receipts/install.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('COMBAT_DUNGEON_MAP_SAVED',len(changed),'actors',len(owned),'packages')
