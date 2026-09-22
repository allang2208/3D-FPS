from pathlib import Path
import json,unreal as u
ROOT=Path(__file__).resolve().parents[1]
for folder in ('Sources','Authored','Receipts'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem);world=UE.get_editor_world()
labels=['DGN_Room_WS_RepairMotor','DGN_WSTools_BenchTop','DGN_Room_WS_TaskLight',
        'DGN_WSTools_TaskCable','DGN_Room_WS_LocalWear','DGN_WSTools_TaskSpot']
rows=[]
for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    if a.get_actor_label() not in labels:continue
    c=a.get_component_by_class(u.StaticMeshComponent)
    row=dict(label=a.get_actor_label(),mesh=c.static_mesh.get_path_name() if c and c.static_mesh else None,
             location=list(a.get_actor_location().to_tuple()),rotation=list(a.get_actor_rotation().to_tuple()),
             scale=list(a.get_actor_scale3d().to_tuple()))
    light=a.get_component_by_class(u.SpotLightComponent)
    if light:row.update(intensity=light.intensity,inner=light.inner_cone_angle,outer=light.outer_cone_angle)
    rows.append(row)
state=dict(world=world.get_path_name() if world else None,gameplay_active=bool(UE.get_game_world()),
           dirty_maps=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],actors=rows)
(ROOT/'Receipts/inputs.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
print(json.dumps(state))
