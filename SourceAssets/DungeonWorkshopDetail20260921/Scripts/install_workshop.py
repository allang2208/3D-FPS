"""Install the four user-requested workshop changes, preserving all unrelated room content."""
from pathlib import Path
import json
from datetime import datetime
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonWorkshopDetail20260921')
TARGET='/Game/GameMaps/L_Dungeon_Prototype'
manifest=json.loads((ROOT/'Authored/manifest.json').read_text())
assets=json.loads((ROOT/'Receipts/asset-import.json').read_text())
if assets.get('stage')!='assets_saved':raise RuntimeError('Workshop assets are not saved')
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem);ED=u.get_editor_subsystem(u.LevelEditorSubsystem)
AA=u.get_editor_subsystem(u.EditorActorSubsystem)
if UE.get_game_world():raise RuntimeError('Gameplay active; preserve it')
dirty=u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
if dirty:raise RuntimeError('Preserve existing dirty map edits: '+', '.join(p.get_name() for p in dirty))
world=UE.get_editor_world()
if not world or world.get_path_name().split('.')[0]!=TARGET:
    if not ED.load_level(TARGET):raise RuntimeError('Dungeon load failed')
actors={a.get_actor_label():a for a in AA.get_all_level_actors()}
for entry in manifest['objects']:
    if entry['replace'] and entry['actor'] not in actors:raise RuntimeError('Expected workshop actor missing '+entry['actor'])
meshes={e['name']:u.load_asset(assets['meshes'][e['name']]) for e in manifest['objects']}
if any(mesh is None for mesh in meshes.values()):raise RuntimeError('Missing authored mesh; no scene changes made')
receipt={'stage':'placing','map':TARGET,'actors':[],'removed_actors':[],
         'tests_run':False,'screenshots_taken':False,'runtime_generator_changed':False}
def write():(ROOT/'Receipts/scene-install.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
write()
for e in manifest['objects']:
    a=actors.get(e['actor'])
    if not a:
        a=AA.spawn_actor_from_class(u.StaticMeshActor,u.Vector())
        a.set_actor_label(e['actor']);a.set_editor_property('tags',[u.Name('DungeonWorkshopDetail20260921')])
    a.modify();c=a.get_component_by_class(u.StaticMeshComponent);c.modify()
    a.set_folder_path('DungeonAtmosphereV2/RoomInteriors/Workshop/Detail')
    a.set_actor_location_and_rotation(u.Vector(),u.Rotator(roll=0,pitch=0,yaw=0),False,True)
    a.set_actor_scale3d(u.Vector(1,1,1));a.set_actor_hidden_in_game(False);a.set_is_temporarily_hidden_in_editor(False)
    a.set_actor_enable_collision(e['collision']);c.set_mobility(u.ComponentMobility.STATIC)
    c.set_static_mesh(meshes[e['name']]);c.set_editor_property('override_materials',[]);c.set_visibility(True)
    c.set_collision_profile_name('BlockAll' if e['collision'] else 'NoCollision');c.set_editor_property('cast_shadow',True)
    receipt['actors'].append({'label':e['actor'],'mesh':meshes[e['name']].get_path_name(),'collision':e['collision']})
# Deletion is specifically requested; original meshes and prior transforms remain in source records.
for label in manifest['remove_actors']:
    a=actors.get(label)
    if a:
        a.modify()
        if not AA.destroy_actor(a):raise RuntimeError('Actor removal failed '+label)
        receipt['removed_actors'].append(label)
UE.set_level_viewport_camera_info(u.Vector(725,-65,165),u.MathLibrary.find_look_at_rotation(u.Vector(725,-65,165),u.Vector(680,315,142)))
if not ED.save_current_level():raise RuntimeError('Workshop map save failed; live edits retained')
receipt.update(stage='map_saved',saved_at=datetime.now().isoformat(),source_blend=manifest['source_blend'])
write();print('WORKSHOP_DETAIL_MAP_SAVED '+json.dumps(receipt))
