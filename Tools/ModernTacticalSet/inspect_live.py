"""Read the affected player components without changing the running game."""
import json
from pathlib import Path
import unreal as u

root=Path('D:/FPS3D/FPSGAME/SourceAssets/ModernTacticalSet20261113/Integration/QualityR3')
root.mkdir(exist_ok=True)
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
report={'playing':bool(world),'components':[]}
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Pawn):
        if not actor.is_player_controlled():continue
        for component in actor.get_components_by_class(u.SkeletalMeshComponent):
            mesh=component.get_editor_property('skeletal_mesh_asset')
            if not mesh:continue
            leader=component.get_editor_property('leader_pose_component')
            record=dict(actor=actor.get_name(),component=component.get_name(),mesh=mesh.get_path_name(),
                        tags=[str(t) for t in component.component_tags],visible=component.is_visible(),
                        hidden=component.get_editor_property('hidden_in_game'),
                        owner_only=component.get_editor_property('only_owner_see'),
                        leader=leader.get_name() if leader else None,
                        lod=component.get_predicted_lod_level(),
                        materials=[component.get_material(i).get_path_name() if component.get_material(i) else None
                                   for i in range(component.get_num_materials())])
            report['components'].append(record)
path=root/'live-before.json'
path.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('TS01_LIVE_READ',report['playing'],len(report['components']),str(path))
