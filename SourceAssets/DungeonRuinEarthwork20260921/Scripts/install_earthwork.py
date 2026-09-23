"""Replace only the ruin's former earthwork actors and save the dungeon map."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonRuinEarthwork20260921')
TARGET='/Game/GameMaps/L_Dungeon_Prototype'
AA=u.get_editor_subsystem(u.EditorActorSubsystem);UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
ED=u.get_editor_subsystem(u.LevelEditorSubsystem)
manifest=json.loads((ROOT/'Authored/manifest.json').read_text())
retired=set(json.loads((ROOT.parent/'DungeonMaintenance20260922/Config/retirement.json').read_text())['actor_labels'])
manifest['hidden_previous']=[label for label in manifest['hidden_previous'] if label not in retired]
assets=json.loads((ROOT/'Receipts/asset-import.json').read_text())
if assets.get('stage')!='assets_saved':raise RuntimeError('Earthwork import is incomplete')
if UE.get_game_world():raise RuntimeError('Gameplay active; preserve current play')
dirty=u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
if dirty:raise RuntimeError('Unsaved map edits preserved: '+', '.join(p.get_name() for p in dirty))
world=UE.get_editor_world()
if not world or world.get_path_name().split('.')[0]!=TARGET:
    if not ED.load_level(TARGET):raise RuntimeError('Could not load target dungeon')
actors={a.get_actor_label():a for a in AA.get_all_level_actors()}
for name in manifest['hidden_previous']:
    if name not in actors:raise RuntimeError('Expected prior earthwork actor missing '+name)
meshes={e['name']:u.load_asset(assets['meshes'][e['name']]) for e in manifest['objects']}
if any(m is None for m in meshes.values()):raise RuntimeError('An imported earthwork mesh is unavailable')
prior=ROOT/'Receipts/previous-actors.json'
if not prior.exists():
    old={}
    for label in manifest['hidden_previous']:
        a=actors[label];c=a.get_component_by_class(u.StaticMeshComponent)
        old[label]={'mesh':c.static_mesh.get_path_name(),'hidden':a.get_editor_property('hidden'),
          'temporarily_hidden':a.is_temporarily_hidden_in_editor(),'visible':c.get_editor_property('visible'),
          'collision_profile':str(c.get_collision_profile_name()),'collision_enabled':str(c.get_collision_enabled()),
          'location':list(a.get_actor_location().to_tuple()),'rotation':list(a.get_actor_rotation().to_tuple()),
          'scale':list(a.get_actor_scale3d().to_tuple())}
    prior.write_text(json.dumps(old,indent=2),encoding='utf-8')
receipt={'stage':'placing','map':TARGET,'actors':[],'hidden_previous':manifest['hidden_previous'],
         'tests_run':False,'screenshots_taken':False,'runtime_generator_changed':False}
rp=ROOT/'Receipts/scene-install.json'
rp.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
for entry in manifest['objects']:
    a=actors.get(entry['actor'])
    if not a:
        a=AA.spawn_actor_from_class(u.StaticMeshActor,u.Vector())
        a.set_actor_label(entry['actor']);a.set_editor_property('tags',[u.Name('DungeonRuinEarthwork20260921')])
    a.modify()
    a.set_folder_path('DungeonAtmosphereV2/RoomInteriors/Ruin/Earthwork')
    a.set_actor_location_and_rotation(u.Vector(),u.Rotator(roll=0,pitch=0,yaw=0),False,True)
    a.set_actor_scale3d(u.Vector(1,1,1));a.set_actor_hidden_in_game(False);a.set_is_temporarily_hidden_in_editor(False)
    c=a.get_component_by_class(u.StaticMeshComponent);c.modify();c.set_mobility(u.ComponentMobility.STATIC)
    c.set_static_mesh(meshes[entry['name']]);c.set_editor_property('override_materials',[])
    c.set_visibility(True);c.set_collision_profile_name('BlockAll' if entry['collision'] else 'NoCollision')
    c.set_editor_property('cast_shadow',True)
    receipt['actors'].append({'label':entry['actor'],'mesh':meshes[entry['name']].get_path_name(),'collision':entry['collision']})
for name in manifest['hidden_previous']:
    a=actors[name];c=a.get_component_by_class(u.StaticMeshComponent)
    # Runtime visibility/collision setters alone do not dirty existing external actor packages.
    a.modify();c.modify()
    a.set_actor_hidden_in_game(True);a.set_is_temporarily_hidden_in_editor(True)
    a.set_actor_enable_collision(False);c.set_visibility(False)
if not ED.save_current_level():raise RuntimeError('Earthwork save failed; live edits preserved')
receipt['stage']='map_saved';receipt['source_blend']=manifest['source_blend']
rp.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('RUIN_EARTHWORK_MAP_SAVED',len(receipt['actors']),'actors; former banks retained hidden')
