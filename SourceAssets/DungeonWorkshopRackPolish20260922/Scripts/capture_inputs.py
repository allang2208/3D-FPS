"""Read only the rack actors required for this authored replacement."""
from pathlib import Path
import json,unreal as u
ROOT=Path(__file__).resolve().parents[1];(ROOT/'Sources').mkdir(parents=True,exist_ok=True)
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem);AA=u.get_editor_subsystem(u.EditorActorSubsystem)
if not UE:raise RuntimeError('No editor subsystem')
if UE.get_game_world():u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
rows=[]
for a in AA.get_all_level_actors():
    c=a.get_component_by_class(u.StaticMeshComponent)
    if not c or not c.static_mesh:continue
    mesh=c.static_mesh.get_path_name()
    if not any(k in mesh for k in ('SM_WSDetail_RackStock','SM_WSDetail_Markings','SM_WSRack_Stock','SM_WSRack_Markings')):continue
    rot=a.get_actor_rotation()
    rows.append(dict(label=a.get_actor_label(),mesh=mesh,actor_path=a.get_path_name(),location=list(a.get_actor_location().to_tuple()),rotation=[rot.roll,rot.pitch,rot.yaw],scale=list(a.get_actor_scale3d().to_tuple()),hidden=a.get_editor_property('hidden'),visible=c.is_visible(),materials=[m.get_path_name() if m else None for m in c.get_editor_property('override_materials')]))
data=dict(world=UE.get_editor_world().get_path_name(),actors=rows,dirty_maps=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()])
(ROOT/'Sources/scene-inputs.json').write_text(json.dumps(data,indent=2),encoding='utf-8');print('RACK_PRODUCTION_INPUTS '+json.dumps(data))
