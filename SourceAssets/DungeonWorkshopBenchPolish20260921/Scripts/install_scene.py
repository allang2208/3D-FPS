"""Replace the named workbench components and remove only the rejected motor."""
from pathlib import Path
from datetime import datetime
import json,shutil,unreal as u
ROOT=Path(__file__).resolve().parents[1];TARGET='/Game/GameMaps/L_Dungeon_Prototype'
manifest=json.loads((ROOT/'Authored/manifest.json').read_text());assets=json.loads((ROOT/'Receipts/asset-import.json').read_text())
if assets.get('stage')!='assets_saved':raise RuntimeError('Bench asset import unfinished')
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem);ED=u.get_editor_subsystem(u.LevelEditorSubsystem);AA=u.get_editor_subsystem(u.EditorActorSubsystem)
if UE.get_game_world():raise RuntimeError('Gameplay active; preserve session')
dirty=u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
if dirty:raise RuntimeError('Preserve unsaved maps: '+', '.join(p.get_name() for p in dirty))
world=UE.get_editor_world()
if not world or world.get_path_name().split('.')[0]!=TARGET:
    if not ED.load_level(TARGET):raise RuntimeError('Dungeon load failed')
actors={a.get_actor_label():a for a in AA.get_all_level_actors()}
inputs={r['label']:r for r in json.loads((ROOT/'Receipts/inputs.json').read_text())['actors']}
previous=json.loads((ROOT.parent/'DungeonWorkshopSculpt20260921/Receipts/scene-install.json').read_text())
expected={r['label']:r['mesh'] for r in previous['actors']}
meshes={e['name']:u.load_asset(assets['meshes'][e['name']]) for e in manifest['objects']}
for e in manifest['objects']:
    if e['actor']=='DGN_WSBench_TaskCable':continue
    a=actors.get(e['actor'])
    if not a:raise RuntimeError('Expected workshop component missing '+e['actor'])
    c=a.get_component_by_class(u.StaticMeshComponent)
    if c.static_mesh.get_path_name() not in (expected[e['actor']],assets['meshes'][e['name']]):raise RuntimeError('Preserve different component revision '+e['actor'])
motor=actors.get('DGN_Room_WS_RepairMotor')
if motor and (motor.get_component_by_class(u.StaticMeshComponent).static_mesh.get_path_name()!=inputs['DGN_Room_WS_RepairMotor']['mesh']):raise RuntimeError('Preserve changed motor revision')
spot=actors.get('DGN_WSTools_TaskSpot')
if not spot:raise RuntimeError('Expected task spotlight missing')
backup=ROOT/'Sources/L_Dungeon_Prototype_before_bench_polish.umap'
if not backup.exists():shutil.copy2(ROOT.parents[1]/'Content/GameMaps/L_Dungeon_Prototype.umap',backup)
receipt=dict(stage='placing',map=TARGET,actors=[],removed_actors=[],hidden_actors=[],previous_actors=[],tests_run=False,screenshots_taken=False)
def write():(ROOT/'Receipts/scene-install.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
anchor=actors['DGN_Room_WS_TaskLight']
for e in manifest['objects']:
    a=actors.get(e['actor'])
    if not a:
        a=AA.spawn_actor_from_class(u.StaticMeshActor,u.Vector());a.set_actor_label(e['actor']);a.set_actor_transform(anchor.get_actor_transform(),False,True)
        a.set_editor_property('tags',[u.Name('DungeonWorkshopBenchPolish20260921')])
    a.modify();c=a.get_component_by_class(u.StaticMeshComponent);c.modify()
    receipt['previous_actors'].append(dict(label=e['actor'],mesh=c.static_mesh.get_path_name() if c.static_mesh else None))
    a.set_folder_path('DungeonAtmosphereV2/RoomInteriors/Workshop/BenchPolish')
    c.set_mobility(u.ComponentMobility.STATIC);c.set_static_mesh(meshes[e['name']]);c.set_editor_property('override_materials',[])
    c.set_visibility(True);c.set_editor_property('cast_shadow',e['cast_shadow'])
    c.set_collision_profile_name('BlockAll' if e['collision'] else 'NoCollision');a.set_actor_enable_collision(e['collision'])
    a.set_actor_hidden_in_game(False);a.set_is_temporarily_hidden_in_editor(False)
    receipt['actors'].append(dict(label=e['actor'],mesh=meshes[e['name']].get_path_name()))
for label in manifest['hide_actors']:
    a=actors.get(label)
    if not a:continue
    a.modify();c=a.get_component_by_class(u.StaticMeshComponent)
    if c:c.modify();c.set_visibility(False)
    a.set_actor_hidden_in_game(True);a.set_is_temporarily_hidden_in_editor(True);a.set_actor_enable_collision(False);receipt['hidden_actors'].append(label)
if motor:
    receipt['removed_actors'].append(dict(label=motor.get_actor_label(),mesh=motor.get_component_by_class(u.StaticMeshComponent).static_mesh.get_path_name()))
    motor.modify()
    if not AA.destroy_actor(motor):raise RuntimeError('Motor removal failed')
light=spot.get_component_by_class(u.SpotLightComponent);spot.modify();light.modify();cfg=manifest['task_light']
receipt['previous_light']=dict(location=list(spot.get_actor_location().to_tuple()),rotation=list(spot.get_actor_rotation().to_tuple()),intensity=light.intensity,temperature=light.temperature)
position=u.Vector(*cfg['position']);target=u.Vector(*cfg['target'])
spot.set_actor_location(position,False,True);spot.set_actor_rotation(u.MathLibrary.find_look_at_rotation(position,target),False)
light.set_intensity(cfg['lumens']);light.set_temperature(cfg['temperature']);light.set_editor_property('use_temperature',True)
light.set_editor_property('source_radius',1.4);light.set_inner_cone_angle(38);light.set_outer_cone_angle(64)
receipt['task_light']=cfg;write()
if not ED.save_current_level():raise RuntimeError('Dungeon save failed; retain live changes')
receipt.update(stage='map_saved',saved_at=datetime.now().isoformat(),source_blend=manifest['source_blend']);write()
print('BENCH_POLISH_MAP_SAVED '+json.dumps(dict(actors=len(receipt['actors']),removed=receipt['removed_actors'],saved_at=receipt['saved_at'],tests_run=False)))
