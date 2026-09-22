"""Install the authored workshop tools and luminaire revision through the project bridge."""
from pathlib import Path
from datetime import datetime
import json
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonWorkshopTools20260921')
TARGET='/Game/GameMaps/L_Dungeon_Prototype'
manifest=json.loads((ROOT/'Authored/manifest.json').read_text())
assets=json.loads((ROOT/'Receipts/asset-import.json').read_text())
if assets.get('stage')!='assets_saved':raise RuntimeError('Tool assets have not finished saving')
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem);ED=u.get_editor_subsystem(u.LevelEditorSubsystem);AA=u.get_editor_subsystem(u.EditorActorSubsystem)
if UE.get_game_world():raise RuntimeError('Gameplay active; preserve it')
dirty=u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
if dirty:raise RuntimeError('Preserve unsaved maps: '+', '.join(p.get_name() for p in dirty))
world=UE.get_editor_world()
if not world or world.get_path_name().split('.')[0]!=TARGET:
    if not ED.load_level(TARGET):raise RuntimeError('Dungeon load failed')
actors={a.get_actor_label():a for a in AA.get_all_level_actors()}
for entry in manifest['objects']:
    if entry.get('variant_only'):continue
    if entry['replace'] and entry['actor'] not in actors:raise RuntimeError('Required actor missing '+entry['actor'])
for label in manifest['hide_lights']:
    if label not in actors:raise RuntimeError('Existing workshop light missing '+label)
meshes={e['name']:u.load_asset(assets['meshes'][e['name']]) for e in manifest['objects']}
if any(m is None for m in meshes.values()):raise RuntimeError('A saved tool mesh is unavailable')
# The source fixture snapshot determines the exact scope of the surgical replacement.
input_state=json.loads((ROOT/'Receipts/inputs.json').read_text())
old_fixture=next(r['mesh'] for r in input_state['actors'] if r['label']=='DGN_AV2_LightFixtures')
current_fixture=actors['DGN_AV2_LightFixtures'].get_component_by_class(u.StaticMeshComponent).static_mesh.get_path_name()
own_fixture=assets['meshes']['SM_WSTools_OtherFixtures']
room_fixture='/Game/Dungeons/AtmosphereV2/RoomInteriors/Authored/SM_Room_FixturesWithoutRuin.SM_Room_FixturesWithoutRuin'
own_variant=assets['meshes']['SM_WSTools_OtherFixturesWithoutRuin']
if current_fixture not in (old_fixture,own_fixture,room_fixture,own_variant):raise RuntimeError('Shared fixture mesh changed since source export; preserve new edit')
selected_fixture=meshes['SM_WSTools_OtherFixturesWithoutRuin'] if current_fixture in (room_fixture,own_variant) else meshes['SM_WSTools_OtherFixtures']
receipt={'stage':'placing','map':TARGET,'actors':[],'lights':[],'hidden_old_lights':manifest['hide_lights'],
         'tests_run':False,'screenshots_taken':False,'runtime_generator_changed':False}
def write():(ROOT/'Receipts/scene-install.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def own(label,cls):
    a=actors.get(label)
    if not a:
        a=AA.spawn_actor_from_class(cls,u.Vector());a.set_actor_label(label)
        a.set_editor_property('tags',[u.Name('DungeonWorkshopTools20260921')]);actors[label]=a
    a.modify();a.set_folder_path('DungeonAtmosphereV2/RoomInteriors/Workshop/ToolsAndLights')
    return a
write()
for entry in manifest['objects']:
    if entry.get('variant_only'):continue
    a=own(entry['actor'],u.StaticMeshActor);c=a.get_component_by_class(u.StaticMeshComponent);c.modify()
    # The combined luminaire mesh retains its existing organizational folder.
    if entry['actor']=='DGN_AV2_LightFixtures':a.set_folder_path('DungeonAtmosphereV2/Lighting')
    a.set_actor_location_and_rotation(u.Vector(),u.Rotator(roll=0,pitch=0,yaw=0),False,True)
    a.set_actor_scale3d(u.Vector(1,1,1));a.set_actor_hidden_in_game(False);a.set_is_temporarily_hidden_in_editor(False)
    a.set_actor_enable_collision(entry['collision']);c.set_mobility(u.ComponentMobility.STATIC)
    mesh=selected_fixture if entry['actor']=='DGN_AV2_LightFixtures' else meshes[entry['name']]
    c.set_static_mesh(mesh);c.set_editor_property('override_materials',[]);c.set_visibility(True)
    c.set_collision_profile_name('BlockAll' if entry['collision'] else 'NoCollision')
    c.set_editor_property('cast_shadow',entry['cast_shadow'])
    receipt['actors'].append({'label':entry['actor'],'mesh':mesh.get_path_name(),'collision':entry['collision']})
for label in manifest['hide_lights']:
    a=actors[label];a.modify();c=a.get_component_by_class(u.LightComponent);c.modify()
    c.set_visibility(False);c.set_intensity(0);a.set_actor_hidden_in_game(True);a.set_is_temporarily_hidden_in_editor(True)
for e in manifest['lights']:
    isrect=e['kind']=='rect';a=own(e['label'],u.RectLight if isrect else u.SpotLight)
    c=a.get_component_by_class(u.RectLightComponent if isrect else u.SpotLightComponent);c.modify()
    location=u.Vector(*e['position'])
    rotation=u.Rotator(roll=0,pitch=-90,yaw=90) if isrect else u.MathLibrary.find_look_at_rotation(location,u.Vector(*e['target']))
    a.set_actor_location_and_rotation(location,rotation,False,True);a.set_actor_hidden_in_game(False);a.set_is_temporarily_hidden_in_editor(False)
    c.set_mobility(u.ComponentMobility.MOVABLE);c.set_visibility(True)
    c.set_editor_property('intensity_units',u.LightUnits.LUMENS);c.set_intensity(e['lumens'])
    c.set_light_color(u.LinearColor(1,1,1,1));c.set_editor_property('use_temperature',True);c.set_temperature(e['temperature'])
    c.set_attenuation_radius(e['radius']);c.set_cast_shadows(True)
    if isrect:
        c.set_source_width(e['width']);c.set_source_height(e['height']);c.set_barn_door_angle(72);c.set_barn_door_length(8)
    else:
        c.set_inner_cone_angle(29);c.set_outer_cone_angle(48);c.set_editor_property('source_radius',3.8)
    receipt['lights'].append(e)
UE.set_level_viewport_camera_info(u.Vector(805,40,161),u.MathLibrary.find_look_at_rotation(u.Vector(805,40,161),u.Vector(902,287,150)))
if not ED.save_current_level():raise RuntimeError('Workshop save failed; preserve live changes')
receipt.update(stage='map_saved',saved_at=datetime.now().isoformat(),source_blend=manifest['source_blend'])
write();print('WORKSHOP_TOOLS_AND_LIGHTS_SAVED '+json.dumps({'actors':len(receipt['actors']),'lights':len(receipt['lights']),
    'hidden_old_lights':receipt['hidden_old_lights'],'saved_at':receipt['saved_at'],'tests_run':False,'screenshots_taken':False}))
