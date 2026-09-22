from pathlib import Path
import unreal as u, json
ROOT=Path(__file__).resolve().parents[1]
(ROOT/'Receipts').mkdir(parents=True,exist_ok=True)
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=UE.get_editor_world()
labels=['DGN_Room_WS_HandTools','DGN_Room_WS_BenchDetail','DGN_WSTools_ToolMarkings','DGN_WSTools_ToolWear','DGN_Room_WS_Toolboard']
rows=[]
for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    if a.get_actor_label() not in labels:continue
    c=a.get_component_by_class(u.StaticMeshComponent)
    rows.append(dict(label=a.get_actor_label(),mesh=c.static_mesh.get_path_name() if c and c.static_mesh else None,
                     location=list(a.get_actor_location().to_tuple()),rotation=list(a.get_actor_rotation().to_tuple()),
                     scale=list(a.get_actor_scale3d().to_tuple())))
state=dict(world=world.get_path_name() if world else None,gameplay_active=bool(UE.get_game_world()),
           dirty_maps=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],actors=rows)
(ROOT/'Receipts/scene-inputs.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
print(json.dumps(state))
