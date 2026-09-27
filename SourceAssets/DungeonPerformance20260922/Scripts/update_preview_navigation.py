"""Apply the runtime tile-navigation policy to the saved preview without regenerating it."""
import json
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1]
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if UE.get_game_world():
    raise RuntimeError('Preserve running play')
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
if UE.get_editor_world().get_path_name().split('.')[0]!=TARGET:
    if not u.EditorLoadingAndSavingUtils.save_dirty_packages(True,True):
        raise RuntimeError('Preserve current level until saving finishes')
    if not u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(TARGET):
        raise RuntimeError('Cannot open the authored dungeon for the navigation update')
actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
generators=[a for a in actors if a.get_class().get_name()=='AuthoredDungeonGenerator']
if not generators:raise RuntimeError('Authored generator is not loaded; preserve the map')
explicit_navigation=set()
for generator in generators:
    catalog=json.loads(generator.get_editor_property('module_catalog_json'))
    for module in catalog['modules']:
        parts=list(module['parts'])
        for side in module.get('side_sockets',[]):parts+=side.get('parts',[])
        explicit_navigation.update(p['mesh'].split('.')[0] for p in parts if p.get('affects_navigation') is True)
changed=[]
for actor in actors:
    if actor.get_owner() not in generators or not actor.actor_has_tag('DungeonRouteGenerated'):continue
    for component in actor.get_components_by_class(u.StaticMeshComponent):
        mesh=component.static_mesh
        if not mesh or not mesh.get_name().endswith(('_Tiles','_Fixtures')):continue
        if mesh.get_path_name().split('.')[0] in explicit_navigation:continue
        if not component.get_editor_property('can_ever_affect_navigation'):continue
        component.modify()
        component.set_editor_property('can_ever_affect_navigation',False)
        changed.append(component.get_path_name())
if not u.EditorLoadingAndSavingUtils.save_dirty_packages(True,True):
    raise RuntimeError('Could not save preview navigation policy')
(ROOT/'Receipts/preview-navigation.json').write_text(json.dumps({'updated_components':changed,'physics_collision':'unchanged','tests_run':False},indent=2),encoding='utf-8')
print('DUNGEON_PREVIEW_NAVIGATION_SAVED',len(changed))
