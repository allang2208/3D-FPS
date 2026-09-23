"""Install persistent contact damage, and rotate only the explicitly selected statue."""
import json,gc
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];BASE='/Game/Dungeons/HazardPolish20260922'
CFG=json.loads((ROOT/'Authored/channel.json').read_text());actions=json.loads((ROOT/'Config/scene-actions.json').read_text())
AA=u.get_editor_subsystem(u.EditorActorSubsystem);ED=u.get_editor_subsystem(u.LevelEditorSubsystem);UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
target='/Game/GameMaps/L_Dungeon_AuthoredExpansion'
if UE.get_game_world():raise RuntimeError('End play before installing dungeon content')
if UE.get_editor_world().get_path_name().split('.')[0]!=target:
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved map')
    if not ED.load_level(target):raise RuntimeError('Dungeon map load failed')
klass=u.load_class(None,'/Script/FPSGAME.DungeonPusChannel')
if not klass:raise RuntimeError('Native dungeon hazard class is not built')
actors=list(AA.get_all_level_actors());statue_action=actions['statue']
statues=[a for a in actors if a.get_path_name()==statue_action['actor_path']]
if len(statues)!=1:raise RuntimeError('Specified statue is not available')
statue=statues[0];statue.modify();center=statue.get_actor_bounds(False)[0];old_rot=statue.get_actor_rotation()
statue.set_actor_rotation(u.Rotator(**statue_action['rotation']),False)
shift=center-statue.get_actor_bounds(False)[0];statue.set_actor_location(statue.get_actor_location()+shift,False,True)
label='DGN_RS_Drainage_CorrosivePus'
existing=[a for a in actors if a.get_actor_label()==label]
if len(existing)>1:raise RuntimeError('Multiple channel actors; preserve scene for explicit resolution')
a=existing[0] if existing else AA.spawn_actor_from_class(klass,u.Vector(*CFG['location_cm']),u.Rotator(pitch=0,yaw=0,roll=0))
a.modify();a.set_actor_label(label);a.set_folder_path('DungeonRoomShells/Drainage')
a.set_actor_location(u.Vector(*CFG['location_cm']),False,True)
a.set_editor_property('half_size',u.Vector2D(*CFG['half_size_cm']))
a.set_editor_property('damage_per_pulse',CFG['damage_per_pulse']);a.set_editor_property('damage_interval',CFG['interval'])
a.set_editor_property('tags',[u.Name(t) for t in ['CorrosivePus','DungeonPermanentHazard','DungeonRoomShells20260922','DungeonRoom_Drainage']])
c=a.get_component_by_class(u.StaticMeshComponent);c.modify();c.set_static_mesh(u.load_asset(BASE+'/Meshes/'+CFG['mesh']))
c.set_material(0,u.load_asset(BASE+'/Materials/MI_DungeonViscousPus'));c.set_collision_profile_name('NoCollision');c.set_cast_shadow(False)
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
owned=[p for p in dirty if '/gamemaps/l_dungeon_authoredexpansion' in p.get_name().lower()]
if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('Owned external actor save failed')
if not ED.save_current_level():raise RuntimeError('Dungeon map save failed')
receipt={'stage':'map_saved','map':target,'hazard_actor':label,'damage_per_pulse':CFG['damage_per_pulse'],'interval':CFG['interval'],'damage_type':CFG['damage_type'],'statue':statue_action,'previous_rotation':dict(pitch=old_rot.pitch,yaw=old_rot.yaw,roll=old_rot.roll),'saved_packages':len(owned),'tests_run':False}
(ROOT/'Receipts/install.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('DUNGEON_HAZARD_AND_STATUE_SAVED',json.dumps(receipt))
