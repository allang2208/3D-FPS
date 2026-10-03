import json
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
root = json.loads((P.parents[3] / 'Content/ColdSteelData/tang-dao-modules.json').read_text(encoding='utf-8-sig'))
report = {}
for name in ['factory', 'yanling_edge', 'tengyun_dragon']:
    spec = root['slots']['blade_1'][name]
    mesh = u.load_asset(spec['mesh'])
    if not mesh:
        report[name] = {'path': spec['mesh'], 'loaded': False}
        continue
    b = mesh.get_bounds()
    sm = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    count = sm.get_lod_count(mesh)
    report[name] = {
        'path': mesh.get_path_name(), 'loaded': True,
        'lods': count, 'triangles': [mesh.get_num_triangles(i) for i in range(count)],
        'bounds_cm': {'origin': [b.origin.x, b.origin.y, b.origin.z],
                      'extent': [b.box_extent.x, b.box_extent.y, b.box_extent.z]},
        'slots': [{'name': str(x.material_slot_name),
                   'material': x.material_interface.get_path_name() if x.material_interface else None}
                  for x in mesh.static_materials],
        'nanite': mesh.get_editor_property('nanite_settings').enabled,
    }
(P / 'diagnosis.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('TANG_BLADE_DIAGNOSIS ' + json.dumps(report), flush=True)
