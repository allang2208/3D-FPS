"""Scoped component replacement; preserves the layout and existing actual lights."""
from pathlib import Path
from datetime import datetime
import json,unreal as u
ROOT=Path(__file__).resolve().parents[1];TARGET='/Game/GameMaps/L_Dungeon_Prototype'
manifest=json.loads((ROOT/'Authored/manifest.json').read_text());assets=json.loads((ROOT/'Receipts/asset-import.json').read_text())
if assets.get('stage')!='assets_saved':raise RuntimeError('Component asset import unfinished')
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem);ED=u.get_editor_subsystem(u.LevelEditorSubsystem);AA=u.get_editor_subsystem(u.EditorActorSubsystem)
if UE.get_game_world():raise RuntimeError('Gameplay active; preserve session')
dirty=u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
if dirty:raise RuntimeError('Preserve unsaved maps: '+', '.join(p.get_name() for p in dirty))
world=UE.get_editor_world()
if not world or world.get_path_name().split('.')[0]!=TARGET:
    if not ED.load_level(TARGET):raise RuntimeError('Dungeon load failed')
actors={a.get_actor_label():a for a in AA.get_all_level_actors()}
inputs={r['label']:r for r in json.loads((ROOT/'Receipts/inputs.json').read_text())['actors']}
meshes={e['name']:u.load_asset(assets['meshes'][e['name']]) for e in manifest['objects']}
if any(m is None for m in meshes.values()):raise RuntimeError('Component mesh unavailable')
for e in manifest['objects']:
    if not e['replace']:continue
    a=actors.get(e['actor'])
    if not a:raise RuntimeError('Workshop actor missing: '+e['actor'])
    c=a.get_component_by_class(u.StaticMeshComponent)
    if c.static_mesh.get_path_name() not in (inputs[e['actor']]['mesh'],assets['meshes'][e['name']]):raise RuntimeError('Preserve concurrent component change: '+e['actor'])
receipt=dict(stage='placing',map=TARGET,actors=[],hidden_actors=[],tests_run=False,screenshots_taken=False,
    lighting_settings_changed=False,runtime_generator_changed=False,reference=manifest['reference'])
def write():(ROOT/'Receipts/scene-install.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
write()
for e in manifest['objects']:
    a=actors.get(e['actor'])
    if not a:
        a=AA.spawn_actor_from_class(u.StaticMeshActor,u.Vector());a.set_actor_label(e['actor']);a.set_editor_property('tags',[u.Name('DungeonWorkshopSculpt20260921')])
    a.modify();c=a.get_component_by_class(u.StaticMeshComponent);c.modify()
    # Replacements inherit any deliberate actor placement. New world-baked objects use identity.
    a.set_actor_hidden_in_game(False);a.set_is_temporarily_hidden_in_editor(False)
    a.set_folder_path('DungeonAtmosphereV2/RoomInteriors/Workshop/RefinedComponents')
    c.set_mobility(u.ComponentMobility.STATIC);c.set_static_mesh(meshes[e['name']]);c.set_editor_property('override_materials',[])
    c.set_visibility(True);a.set_actor_enable_collision(e['collision']);c.set_collision_profile_name('BlockAll' if e['collision'] else 'NoCollision')
    c.set_editor_property('cast_shadow',e['cast_shadow'])
    receipt['actors'].append(dict(label=e['actor'],mesh=meshes[e['name']].get_path_name()))
for label in manifest['hide_actors']:
    a=actors.get(label)
    if a:
        a.modify();c=a.get_component_by_class(u.StaticMeshComponent)
        if c:c.modify();c.set_visibility(False)
        a.set_actor_hidden_in_game(True);a.set_is_temporarily_hidden_in_editor(True);a.set_actor_enable_collision(False)
        receipt['hidden_actors'].append(label)
if not ED.save_current_level():raise RuntimeError('Save failed; retain live scene')
receipt.update(stage='map_saved',saved_at=datetime.now().isoformat(),source_blend=manifest['source_blend'])
write();print('WORKSHOP_COMPONENT_SCENE_SAVED '+json.dumps(dict(actors=len(receipt['actors']),hidden=receipt['hidden_actors'],saved_at=receipt['saved_at'],tests_run=False)))
