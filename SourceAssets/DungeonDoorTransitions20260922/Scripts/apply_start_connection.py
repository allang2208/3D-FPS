"""Apply only the fixed start connector; caller owns the map save and map selection."""
import unreal as u,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
recipe=json.loads((ROOT/'Config/transition.json').read_text())
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem);aa=u.get_editor_subsystem(u.EditorActorSubsystem)
if ue.get_game_world():raise RuntimeError('Preserve running game')
if ue.get_editor_world().get_path_name().split('.')[0]!=recipe['map']:raise RuntimeError('Different target map')
actors={a.get_actor_label():a for a in aa.get_all_level_actors()}
generator=actors.get('DGN_RouteGenerator')
if generator:
    recipe=json.loads(generator.get_editor_property('module_catalog_json')).get('start_connection',recipe)
link=actors[recipe['actor']];mesh=u.load_asset(recipe['mesh'])
if not mesh:raise RuntimeError('Import transition before scene integration')
link.modify();c=link.get_component_by_class(u.StaticMeshComponent);c.modify();c.set_static_mesh(mesh);c.set_collision_profile_name('BlockAll')
light=actors.get('DGN_Link_InspectionLight')
if light:
    light.modify();light.set_actor_location(u.MathLibrary.transform_location(link.get_actor_transform(),u.Vector(0,-80,214)),False,True)
print('START_TRANSITION_APPLIED',recipe['actor'],recipe['entry_clear_m'],recipe['exit_clear_m'])
