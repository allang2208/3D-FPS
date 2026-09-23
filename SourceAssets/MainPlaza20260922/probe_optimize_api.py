"""Read-only probe: which APIs can build a low-poly floor and add LOD chains here?

Answers three questions before any edit:
  1. what Vibe3D ModelingService operations exist for simplify / load / save / duplicate;
  2. what EditorStaticMeshLibrary exposes for LOD count and reduction settings;
  3. the current LOD/material state of the three heavy plaza assets.
No edits, no save, no PIE.
"""
import json
import traceback
from pathlib import Path

import unreal

HERE = Path(__file__).parent
PROPS = '/Game/Props/RomanColumn20260915'

ASSETS = [
    PROPS + '/SM_MarbleFloorTiles',
    PROPS + '/SM_RomanColumn_Detailed',
    PROPS + '/SM_RomanColumn_Round_20',
    PROPS + '/SM_RomanBaluster_Small',
    PROPS + '/SM_RomanRail_200',
]

WANT_SV = ('simplif', 'decimat', 'lod', 'duplicate', 'load', 'save', 'collision', 'uv', 'remesh')
WANT_ESML = ('lod', 'triangle', 'reduction', 'simplif')


def run():
    out = {}

    sv = [n for n in dir(unreal.ModelingService) if not n.startswith('_')]
    out['modelingservice_simplify'] = sorted(n for n in sv if any(k in n.lower() for k in WANT_SV))
    out['modelingservice_total'] = len(sv)

    esml = [n for n in dir(unreal.EditorStaticMeshLibrary) if not n.startswith('_')]
    out['staticmesh_library_lod'] = sorted(n for n in esml if any(k in n.lower() for k in WANT_ESML))
    out['staticmesh_library_total'] = len(esml)

    comp_methods = [n for n in dir(unreal.StaticMeshComponent) if 'lod' in n.lower()]
    out['component_lod_methods'] = sorted(comp_methods)

    rows = []
    for path in ASSETS:
        mesh = unreal.load_asset(path)
        if mesh is None:
            rows.append(dict(path=path, missing=True))
            continue
        lods = []
        try:
            n = mesh.get_num_lods()
        except Exception:
            n = 1
        for i in range(n):
            try:
                lods.append(dict(index=i, triangles=mesh.get_num_triangles(i),
                                 vertices=mesh.get_num_vertices(i)))
            except Exception:
                lods.append(dict(index=i, triangles=None, vertices=None))
        mats = mesh.get_editor_property('static_materials') or []
        bb = mesh.get_bounding_box()
        rows.append(dict(path=path.split('/')[-1], lod_count=n, lods=lods,
                         materials=[m.get_editor_property('material_interface').get_path_name()
                                    if m.get_editor_property('material_interface') else None
                                    for m in mats],
                         size_cm=[round(bb.max.x - bb.min.x, 1), round(bb.max.y - bb.min.y, 1),
                                  round(bb.max.z - bb.min.z, 1)]))
    out['assets'] = rows

    # Is the reduction-settings type available for building LODs from Python?
    out['has_static_mesh_reduction_settings'] = hasattr(unreal, 'StaticMeshReductionSettings')
    if hasattr(unreal, 'StaticMeshReductionSettings'):
        try:
            out['reduction_settings_fields'] = [p for p in
                                                dir(unreal.StaticMeshReductionSettings)
                                                if not p.startswith('_')]
        except Exception as exc:
            out['reduction_settings_fields'] = str(exc)
    return out


try:
    result = run()
    (HERE / 'optimize_probe.json').write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                              encoding='utf-8')
    print('PROBE_OK sv_total=%d esml_total=%d' % (result['modelingservice_total'],
                                                  result['staticmesh_library_total']))
    print('SV: ' + ', '.join(result['modelingservice_simplify']))
    print('ESML: ' + ', '.join(result['staticmesh_library_lod']))
    print('COMP: ' + ', '.join(result['component_lod_methods']))
    print('reduction_settings=%s' % result['has_static_mesh_reduction_settings'])
    for r in result['assets']:
        if r.get('missing'):
            print('  MISSING %s' % r['path'])
            continue
        print('  %-26s lods=%s mats=%s size=%s' % (r['path'], r['lods'], r['materials'], r['size_cm']))
except Exception:
    (HERE / 'optimize_probe_error.txt').write_text(traceback.format_exc(), encoding='utf-8')
    print('PROBE_FAILED')
    raise
