"""Apply the authored altar placement to any existing chapel residents."""
import json
from pathlib import Path
import unreal as u

out = Path('D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115/PlacementR2')
out.mkdir(parents=True, exist_ok=True)
editor_world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
worlds = [editor_world] + list(u.EditorLevelLibrary.get_pie_worlds(False))
report = {'local_position_cm': [665, 0, 20], 'local_yaw_degrees': 180,
          'chapel_scale': 1.25, 'capsule_center_above_floor_cm': 84,
          'location': 'Centered behind the stone altar, facing the entrance',
          'moved': [], 'gameplay_tested': False}
seen = set()
for world in worlds:
    if not world or world.get_path_name() in seen:
        continue
    seen.add(world.get_path_name())
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.TemperateHillsWorld):
        comps = {c.get_name(): c for c in actor.get_components_by_class(u.SceneComponent)}
        altar = comps.get('OldChapel_Altar')
        nun = comps.get('OldChapel_Nun')
        if not altar or not nun or not altar.get_instance_count():
            continue
        transform = altar.get_instance_transform(0, True)
        # Altar origin: (570, 0, 20), resident: (665, 0, 20), actor remains human-sized.
        position = u.MathLibrary.transform_location(transform, u.Vector(95, 0, 0)) + u.Vector(0, 0, 84)
        yaw = transform.rotation.rotator().yaw + 180
        nun.set_world_location_and_rotation(position, u.Rotator(0, yaw, 0), False, False)
        report['moved'].append({'world': world.get_path_name(), 'component': nun.get_path_name(),
                                'location': str(position), 'yaw': yaw})
(out / 'placement.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
