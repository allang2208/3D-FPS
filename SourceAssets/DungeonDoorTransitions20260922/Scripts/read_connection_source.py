import unreal as u,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];(root/'Receipts').mkdir(exist_ok=True)
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem)
p,r=u.EditorLevelLibrary.get_level_viewport_camera_info()
result=dict(map=ue.get_editor_world().get_path_name(),playing=bool(ue.get_game_world()),camera=[p.x,p.y,p.z],rotation=[r.pitch,r.yaw,r.roll],nearby=[])
for a in actors.get_all_level_actors():
    label=a.get_actor_label()
    if not label.startswith(('DGN_G_','DGN_RS_','DGN_Link_')):continue
    center,extent=a.get_actor_bounds(False)
    if (center-p).length()>2300:continue
    result['nearby'].append(dict(label=label,position=[a.get_actor_location().x,a.get_actor_location().y,a.get_actor_location().z],rotation=a.get_actor_rotation().yaw,scale=[a.get_actor_scale3d().x,a.get_actor_scale3d().y,a.get_actor_scale3d().z],center=[center.x,center.y,center.z],extent=[extent.x,extent.y,extent.z],tags=[str(t) for t in a.tags],meshes=[c.static_mesh.get_path_name() for c in a.get_components_by_class(u.StaticMeshComponent) if c.static_mesh]))
(root/'Receipts/connection-source.json').write_text(json.dumps(result,indent=2))
print('CONNECTION_SOURCE',result['map'],result['playing'],result['camera'],len(result['nearby']))
