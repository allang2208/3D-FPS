"""Export source wall geometry and read loaded wall transforms; no world mutations."""
import json
from pathlib import Path
import unreal as u

root = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
out = root/'SourceAssets/TemperateHillsVillage/WallSupport20261114'
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
world, game = editor.get_editor_world(), editor.get_game_world()
report = dict(editor_world=world.get_path_name() if world else None,
              game_world=game.get_path_name() if game else None,
              dirty_maps=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
              loaded_walls=[], exports=[])
def xyz(v): return [v.x, v.y, v.z]
for actor in u.GameplayStatics.get_all_actors_of_class(game or world, u.Actor):
    for comp in actor.get_components_by_class(u.StaticMeshComponent):
        mesh = comp.static_mesh
        if not mesh or 'StoneWall' not in mesh.get_name(): continue
        transforms = ([comp.get_instance_transform(i, True) for i in range(comp.get_instance_count())]
                      if isinstance(comp, u.InstancedStaticMeshComponent) else [comp.get_world_transform()])
        for t in transforms:
            r = t.rotation.rotator()
            report['loaded_walls'].append(dict(actor=actor.get_path_name(), mesh=mesh.get_name(),
                pos=xyz(t.translation), rot=[r.pitch,r.yaw,r.roll], scale=xyz(t.scale3d)))
demo = json.loads((root/'SourceAssets/TemperateHillsVillage/DemoRevision20261114/demo-walls.json').read_text())
for name, row in demo['meshes'].items():
    mesh = u.load_asset(row['path'])
    task = u.AssetExportTask()
    task.object = mesh
    task.filename = str(out/'Geometry'/(name+'.obj'))
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    task.exporter = u.StaticMeshExporterOBJ()
    ok = u.Exporter.run_asset_export_task(task)
    report['exports'].append(dict(mesh=name, ok=ok))
(out/'read.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='loaded_walls'}))
print('LOADED_WALLS',len(report['loaded_walls']))
