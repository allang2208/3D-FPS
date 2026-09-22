"""Read only the existing actors needed to attach the new room assets."""
import unreal as u
import json
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonRoomInteriors20260921')
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=ue.get_editor_world()
r={'world':world.get_path_name() if world else None,'playing':bool(ue.get_game_world()),'game_world':ue.get_game_world().get_path_name() if ue.get_game_world() else None,'dirty_maps':[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],'actors':{}}
for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    label=a.get_actor_label()
    if not label.startswith('DGN_AV2_') or not any(k in label for k in ('Workshop','Ruin','Ancient','Goddess','LightFixtures','Breach','Rubble','Damp_4','Damp_8')):continue
    d={'location':list(a.get_actor_location().to_tuple()),'rotation':list(a.get_actor_rotation().to_tuple()),'scale':list(a.get_actor_scale3d().to_tuple())}
    c=a.get_component_by_class(u.StaticMeshComponent)
    if c and c.static_mesh:
        b=c.static_mesh.get_bounds()
        d.update(mesh=c.static_mesh.get_path_name(),origin=list(b.origin.to_tuple()),extent=list(b.box_extent.to_tuple()))
    light=a.get_component_by_class(u.PointLightComponent)
    if light:d.update(intensity=light.intensity,attenuation_radius=light.attenuation_radius)
    r['actors'][label]=d
(root/'Receipts/room-inputs.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print(json.dumps(r))
