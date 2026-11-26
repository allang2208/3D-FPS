"""Read Normandy entrance geometry for the requested standing-access correction."""
import json
from pathlib import Path
import unreal as u

root = Path('D:/FPS3D/FPSGAME/SourceAssets/TemperateHillsVillage/Upgrade20261114')
root.mkdir(parents=True, exist_ok=True)
report = {}
for name in ('SM_H_OldWall_Door_00A', 'SM_Door_00A', 'SM_WoodenFloor_00A', 'SM_Window_Frame_00A'):
    mesh = u.load_asset('/Game/UnrealNormandy/StaticMeshes/' + name)
    if mesh is None:
        raise RuntimeError(name)
    export = u.AssetExportTask()
    export.object = mesh
    export.filename = str(root / (name + '.obj'))
    export.automated = True
    export.prompt = False
    export.replace_identical = True
    export.exporter = u.StaticMeshExporterOBJ()
    if not u.Exporter.run_asset_export_task(export):
        raise RuntimeError('Geometry export failed ' + name)
    body = mesh.get_editor_property('body_setup')
    aggregate = body.get_editor_property('agg_geom')
    bounds = mesh.get_bounding_box()
    xyz = lambda v: [v.x, v.y, v.z]
    report[name] = dict(bounds=[xyz(bounds.min), xyz(bounds.max)],
                        collision=str(body.get_editor_property('collision_trace_flag')),
                        convex_count=len(aggregate.get_editor_property('convex_elems')),
                        boxes=[box.export_text() for box in aggregate.get_editor_property('box_elems')])
(root / 'entrance-source.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('VILLAGE_ENTRANCE_SOURCE', json.dumps(report))
