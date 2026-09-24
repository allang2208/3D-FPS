"""Persist one tagged altar; preserve a dirty active map and never start PIE."""
import json
import math
from pathlib import Path
import unreal

HERE = Path(__file__).parent
MAP = '/Game/GameMaps/DayNight_Lighting'
TAG = 'ColdSteel.ExpeditionAltar'
LABEL = 'Expedition_SquareAltar'
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world = editor.get_editor_world()
if world is None:
    raise RuntimeError('Editor has not loaded a world yet; placement has not started.')
if editor.get_game_world() is not None:
    raise RuntimeError('PIE is active; placement has not started.')
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
previous_map = world.get_path_name().split('.')[0]
if previous_map != MAP:
    dirty_maps = [p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    if dirty_maps:
        raise RuntimeError('Preserve unsaved level edits before switching maps: ' + ', '.join(dirty_maps))
    if not level.load_level(MAP):
        raise RuntimeError('Could not open the main map for placement.')
    world = editor.get_editor_world()
api = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = api.get_all_level_actors()
matches = [a for a in actors if TAG in [str(t) for t in a.tags]]
if len(matches) > 1:
    raise RuntimeError('Multiple expedition altars already exist; preserve them for manual choice.')
starts = [a for a in actors if isinstance(a, unreal.PlayerStart)]
if len(starts) != 1:
    raise RuntimeError('Expected the main map PlayerStart as the placement anchor.')
floor = next((a for a in actors if a.get_actor_label() == 'Floor'), None)
if floor is None:
    raise RuntimeError('The authored main-map Floor is missing; no guessed ground height.')
mesh = unreal.load_asset('/Game/Props/SquareAltar20260922/SM_SquareAltar')
if mesh is None:
    raise RuntimeError('The migrated square altar mesh is missing.')

origin = starts[0].get_actor_location()
yaw = starts[0].get_actor_rotation().yaw
angle = math.radians(yaw)
forward = unreal.Vector(math.cos(angle), math.sin(angle), 0)
right = unreal.Vector(-math.sin(angle), math.cos(angle), 0)
position = origin + forward * 650.0 - right * 400.0
center, extent = floor.get_actor_bounds(False)
if abs(position.x-center.x)+150 > extent.x or abs(position.y-center.y)+150 > extent.y:
    raise RuntimeError('The chosen altar footprint falls outside the authored floor.')
position.z = center.z + extent.z - mesh.get_bounding_box().min.z

# Resume the single actor created by this script if an editor API failure interrupted setup before tagging.
if not matches:
    partial = [a for a in actors if isinstance(a, unreal.StaticMeshActor)
        and a.static_mesh_component.static_mesh == mesh and (a.get_actor_location()-position).length() < 0.1]
    if len(partial) > 1:
        raise RuntimeError('More than one actor occupies this exact altar placement; preserve the scene.')
    matches = partial

# Leave an existing altar where the user placed it. Only newly authored placement uses the anchor offset.
with unreal.ScopedEditorTransaction('Place expedition square altar'):
    altar = matches[0] if matches else api.spawn_actor_from_class(unreal.StaticMeshActor, position,
        unreal.Rotator(pitch=0, yaw=yaw+180.0, roll=0))
    if altar is None:
        raise RuntimeError('Altar spawn failed.')
    altar.modify()
    altar.set_actor_label(LABEL)
    altar.tags = list(dict.fromkeys([str(t) for t in altar.tags] + [TAG]))
    component = altar.static_mesh_component
    component.set_mobility(unreal.ComponentMobility.MOVABLE)
    component.set_static_mesh(mesh)
    component.set_collision_profile_name('BlockAll')
    component.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    component.set_editor_property('generate_overlap_events', False)
    component.set_mobility(unreal.ComponentMobility.STATIC)
    altar.set_folder_path('Main Hub/Expedition')
    altar.set_editor_property('is_spatially_loaded', False)

if not level.save_current_level():
    raise RuntimeError('Main map save failed; keep the current editor placement intact.')
p = altar.get_actor_location()
receipt = dict(map=MAP, actor=altar.get_path_name(), label=LABEL, tag=TAG,
    mesh=mesh.get_path_name(), location_cm=[p.x,p.y,p.z],
    anchor=starts[0].get_actor_label(), anchor_offset_cm=[650,-400],
    input='Aim at the altar within 250 cm, press E; Escape closes the panel.',
    saved=True, runtime_tested=False)
(HERE/'hub_altar_placement.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('HUB_ALTAR_SAVED ' + json.dumps(receipt, ensure_ascii=False))
if previous_map != MAP:
    if not level.load_level(previous_map):
        unreal.log_warning('Altar saved; the previous editor map could not be restored: ' + previous_map)
