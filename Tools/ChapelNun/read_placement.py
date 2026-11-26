import json
from pathlib import Path
import unreal as u

out = Path('D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115/PlacementR2')
out.mkdir(parents=True, exist_ok=True)
report = {'worlds': []}
worlds = [u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()]
worlds += list(u.EditorLevelLibrary.get_pie_worlds(False))
for world in worlds:
    if not world:
        continue
    entry = {'world': world.get_path_name(), 'chapels': []}
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.TemperateHillsWorld):
        chapel = {'actor': actor.get_path_name(), 'parts': []}
        for comp in actor.get_components_by_class(u.SceneComponent):
            if comp.get_name() not in ('OldChapel_Nun', 'OldChapel_Altar', 'OldChapel_Portal', 'OldChapel_SanctuarySteps'):
                continue
            part = {'name': comp.get_name(), 'transform': str(comp.get_world_transform())}
            if isinstance(comp, u.InstancedStaticMeshComponent):
                part['instances'] = [str(comp.get_instance_transform(i, True)) for i in range(comp.get_instance_count())]
                mesh = comp.get_editor_property('static_mesh')
                part['mesh_bounds'] = str(mesh.get_bounding_box())
            if isinstance(comp, u.ChildActorComponent):
                child = comp.get_child_actor()
                part['child'] = child.get_path_name() if child else None
            chapel['parts'].append(part)
        entry['chapels'].append(chapel)
    report['worlds'].append(entry)
(out / 'placement_before.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
