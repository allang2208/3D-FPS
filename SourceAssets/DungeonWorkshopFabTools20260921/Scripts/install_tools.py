"""Install only workshop tool assets; retain old actors and all unrelated scene work."""
from pathlib import Path
from datetime import datetime
import json,unreal as u
ROOT=Path(__file__).resolve().parents[1];TARGET='/Game/GameMaps/L_Dungeon_Prototype'
manifest=json.loads((ROOT/'Authored/manifest.json').read_text())
assets=json.loads((ROOT/'Receipts/asset-import.json').read_text())
if assets.get('stage')!='assets_saved':raise RuntimeError('Tool import unfinished')
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem);ED=u.get_editor_subsystem(u.LevelEditorSubsystem);AA=u.get_editor_subsystem(u.EditorActorSubsystem)
if UE.get_game_world():raise RuntimeError('Gameplay active; preserve session')
dirty=u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
if dirty:raise RuntimeError('Preserve unsaved maps: '+', '.join(p.get_name() for p in dirty))
world=UE.get_editor_world()
if not world or world.get_path_name().split('.')[0]!=TARGET:
    if not ED.load_level(TARGET):raise RuntimeError('Dungeon load failed')
actors={a.get_actor_label():a for a in AA.get_all_level_actors()}
previous=json.loads((ROOT.parent/'DungeonWorkshopSurface20260921/Receipts/scene-install.json').read_text())
expected={r['label']:r['mesh'] for r in previous['actors']}
for entry in manifest['objects']:
    if not entry.get('replace'):continue
    actor=actors.get(entry['actor'])
    if not actor:raise RuntimeError('Expected workshop actor missing '+entry['actor'])
    mesh=actor.get_component_by_class(u.StaticMeshComponent).static_mesh
    if mesh.get_path_name() not in (expected[entry['actor']],assets['meshes'][entry['name']]):
        raise RuntimeError('Preserve different component revision '+entry['actor'])
hand=actors.get('DGN_Room_WS_HandTools')
if not hand:raise RuntimeError('Workshop placement anchor missing')
if hand.get_component_by_class(u.StaticMeshComponent).static_mesh.get_path_name()!=expected['DGN_Room_WS_HandTools']:
    raise RuntimeError('Preserve different hand-tool revision')
receipt=dict(stage='placing',map=TARGET,actors=[],hidden_actors=[],previous_actors=[],tests_run=False,screenshots_taken=False)
def write():(ROOT/'Receipts/scene-install.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
for entry in manifest['objects']:
    if not entry.get('actor'):continue
    label=entry['actor'];actor=actors.get(label)
    if actor:
        comp=actor.get_component_by_class(u.StaticMeshComponent)
        receipt['previous_actors'].append(dict(label=label,mesh=comp.static_mesh.get_path_name() if comp.static_mesh else None))
    else:
        actor=AA.spawn_actor_from_class(u.StaticMeshActor,u.Vector());actor.set_actor_label(label)
        actor.set_actor_transform(hand.get_actor_transform(),False,True)
        actor.set_editor_property('tags',[u.Name('DungeonWorkshopFabTools20260921')])
    actor.modify();comp=actor.get_component_by_class(u.StaticMeshComponent);comp.modify()
    actor.set_folder_path('DungeonAtmosphereV2/RoomInteriors/Workshop/FabTools')
    comp.set_mobility(u.ComponentMobility.STATIC);comp.set_static_mesh(u.load_asset(assets['meshes'][entry['name']]))
    comp.set_editor_property('override_materials',[]);comp.set_visibility(True)
    comp.set_collision_profile_name('NoCollision');actor.set_actor_enable_collision(False)
    comp.set_editor_property('cast_shadow',entry['cast_shadow'])
    actor.set_actor_hidden_in_game(False);actor.set_is_temporarily_hidden_in_editor(False)
    receipt['actors'].append(dict(label=label,mesh=assets['meshes'][entry['name']]))
for label in manifest['hide_actors']:
    actor=actors.get(label)
    if not actor:continue
    actor.modify();comp=actor.get_component_by_class(u.StaticMeshComponent)
    if comp:comp.modify();comp.set_visibility(False)
    actor.set_actor_hidden_in_game(True);actor.set_is_temporarily_hidden_in_editor(True);actor.set_actor_enable_collision(False)
    receipt['hidden_actors'].append(label)
write()
if not ED.save_current_level():raise RuntimeError('Map save failed; retain live changes')
receipt.update(stage='map_saved',saved_at=datetime.now().isoformat(),source_blend=manifest['source_blend'])
write();print('FAB_WORKSHOP_MAP_SAVED '+json.dumps(dict(actors=len(receipt['actors']),hidden=receipt['hidden_actors'],saved_at=receipt['saved_at'],tests_run=False)))
