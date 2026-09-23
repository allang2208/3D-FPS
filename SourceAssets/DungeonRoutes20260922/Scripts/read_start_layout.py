"""Read the existing start assembly for the cabinet/shrine integration, without switching maps."""
import unreal as u,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem);AA=u.get_editor_subsystem(u.EditorActorSubsystem)
data=dict(map=UE.get_editor_world().get_path_name(),playing=bool(UE.get_game_world()),actors=[])
for a in AA.get_all_level_actors():
    label=a.get_actor_label()
    if not (label.startswith('DGN_A_') and any(s in label.lower() for s in ['cabinet','chest','tool','ru_','ruin','workbench']) or 'Goddess' in label):continue
    p=a.get_actor_location();r=a.get_actor_rotation();center,extent=a.get_actor_bounds(False)
    data['actors'].append(dict(label=label,location=[p.x,p.y,p.z],yaw=r.yaw,bounds_center=[center.x,center.y,center.z],extent=[extent.x,extent.y,extent.z],meshes=[c.static_mesh.get_path_name() for c in a.get_components_by_class(u.StaticMeshComponent) if c.static_mesh]))
(ROOT/'Receipts/start-layout.json').write_text(json.dumps(data,indent=2))
print(json.dumps(data))
