"""Read actual saved mesh surfaces in a fresh UE commandlet, without opening the map."""
import hashlib
import json
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
    raise RuntimeError('Wrong project')
report = dict(source='fresh UE process; saved static mesh LOD0 geometry',
              coordinate_conversion='UE centimetres to Blender metres (x/100,-y/100,z/100)',
              meshes={}, assets_modified=False, map_loaded=False, rendered=False, gameplay_tested=False)
service = u.ModelingService
for kind in ('Walls', 'Frames', 'WindowGaskets'):
    name = 'SM_Ward_' + kind
    path = '/Game/Dungeons/IsolationWard20260929/Meshes/' + name
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError('Missing saved asset: ' + path)
    result = service.load_mesh_from_static_mesh(path, 0)
    handle = result.handle
    if handle < 0:
        raise RuntimeError('Cannot read mesh: ' + path)
    try:
        dynamic_mesh = service.get_dynamic_mesh(handle)
        _, ids, _ = dynamic_mesh.get_all_triangle_i_ds()
        triangles = []
        for tid in ids.convert_index_list_to_array():
            ok, a, b, c = dynamic_mesh.get_triangle_positions(int(tid))
            if not ok:
                raise RuntimeError('Cannot read triangle: ' + str(tid))
            triangles.append([[p.x*.01, -p.y*.01, p.z*.01] for p in (a, b, c)])
        if not triangles:
            raise RuntimeError('Saved mesh has no triangles: ' + path)
        package = PROJECT / 'Content/Dungeons/IsolationWard20260929/Meshes' / (name + '.uasset')
        settings = asset.get_editor_property('nanite_settings')
        report['meshes'][kind] = dict(
            path=path, saved_package_sha256=hashlib.sha256(package.read_bytes()).hexdigest(),
            triangles_m=triangles,
            nanite_enabled=settings.enabled, explicit_tangents=settings.explicit_tangents,
            fallback_percent_triangles=settings.fallback_percent_triangles,
            collision_trace_flag=str(asset.get_editor_property('body_setup').get_editor_property('collision_trace_flag')),
            materials=[str(slot.material_interface.get_path_name()) for slot in asset.get_editor_property('static_materials')],
        )
        print('WARD_SAVED_MESH_READBACK', kind, len(triangles), flush=True)
    finally:
        service.release_mesh(handle)
(ROOT / 'Receipts/window-reveal-v8-saved-triangles.json').write_text(json.dumps(report), encoding='utf-8')
print('WARD_WINDOW_REVEALS_V8_READBACK_COMPLETE', flush=True)
