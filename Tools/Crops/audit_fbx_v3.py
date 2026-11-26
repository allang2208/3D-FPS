"""Headless Blender readback of all V3 FBX; never saves or modifies sources."""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[2] / 'SourceAssets/CropsV3_20261022'
SOURCE = ROOT / 'Source'
manifest = json.loads((SOURCE / 'variant_manifest.json').read_text(encoding='utf-8'))
lods = {r['name']: r['triangles'] for r in json.loads((SOURCE / 'lod_manifest.json').read_text())}
rows = []
materials = {}

use_derived = '--derived' in sys.argv
use_engine = '--engine' in sys.argv
for original in sorted((SOURCE / 'Models').glob('*.fbx')):
    derived = ROOT / 'Derived/Models' / original.name
    engine = ROOT / 'EngineBasis/Models' / original.name
    path = engine if use_engine and engine.exists() else derived if (use_derived or use_engine) and derived.exists() else original
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path), use_anim=False)
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    assert len(meshes) == 1, (path.name, len(meshes))
    obj = meshes[0]
    mesh = obj.data
    mesh.calc_loop_triangles()
    positions = np.array([obj.matrix_world @ v.co for v in mesh.vertices], dtype=np.float64)
    tri = np.array([list(t.vertices) for t in mesh.loop_triangles])
    area = np.linalg.norm(np.cross(positions[tri[:, 1]] - positions[tri[:, 0]],
                                   positions[tri[:, 2]] - positions[tri[:, 0]]), axis=1)
    assert mesh.uv_layers.active, path.name
    uv = np.array([list(v.uv) for v in mesh.uv_layers.active.data], dtype=np.float64)
    loop_ids = np.array([list(t.loops) for t in mesh.loop_triangles])
    tuv = uv[loop_ids]
    uv_area = np.abs(np.cross(tuv[:, 1] - tuv[:, 0], tuv[:, 2] - tuv[:, 0]))
    normals = np.array([list(c.vector) for c in mesh.corner_normals], dtype=np.float64)
    mesh.calc_tangents(uvmap=mesh.uv_layers.active.name)
    tangents = np.array([list(l.tangent) for l in mesh.loops], dtype=np.float64)
    slots = [m.name for m in mesh.materials]
    for m in mesh.materials:
        principled = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None) if m.node_tree else None
        materials[m.name] = {
            'diffuse': list(m.diffuse_color),
            'roughness': m.roughness, 'metallic': m.metallic,
            'bsdf': {s.name: list(s.default_value) if hasattr(s.default_value, '__len__') else s.default_value
                     for s in principled.inputs if hasattr(s, 'default_value')} if principled else {},
            'images': [n.image.filepath for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image] if m.node_tree else [],
        }
    record = {
        'file': path.name, 'read_path': str(path.relative_to(ROOT)), 'triangles': len(tri), 'vertices': len(positions),
        'bounds_min_m': positions.min(axis=0).tolist(), 'bounds_max_m': positions.max(axis=0).tolist(),
        'dimensions_m': np.ptp(positions, axis=0).tolist(),
        'origin_m': list(obj.matrix_world.translation), 'scale': list(obj.scale),
        'finite': bool(all(np.isfinite(x).all() for x in (positions, uv, normals, tangents))),
        'zero_area_geometry': int((area < 1e-14).sum()), 'zero_area_uv': int((uv_area < 1e-12).sum()),
        'zero_normals': int((np.linalg.norm(normals, axis=1) < .5).sum()),
        'zero_tangents': int((np.linalg.norm(tangents, axis=1) < .5).sum()),
        'slots': slots,
        'material_triangles': dict(Counter(slots[t.material_index] for t in mesh.loop_triangles)),
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    rows.append(record)

by_file = {r['file']: r for r in rows}
errors = []
for row in rows:
    if not row['finite'] or row['zero_area_geometry'] or row['zero_area_uv'] or row['zero_normals'] or row['zero_tangents']:
        errors.append({'file': row['file'], 'reason': 'invalid geometry/UV/basis', 'row': row})
    if max(abs(v) for v in row['origin_m']) > 1e-5:
        errors.append({'file': row['file'], 'reason': 'root origin is not zero'})
    if '_LOD' in row['file'] and row['triangles'] != lods[row['file'][:-4]]:
        errors.append({'file': row['file'], 'reason': 'LOD triangle mismatch'})
for asset in manifest['assets']:
    row = by_file[Path(asset['mesh_file']).name]
    if row['triangles'] != asset['triangles'] or max(abs(x-y) for x,y in zip(row['dimensions_m'], asset['dimensions_m'])) > 2e-5:
        errors.append({'file': row['file'], 'reason': 'LOD0 manifest dimensions/triangle mismatch'})
    low = [by_file[Path(asset[k]).name] for k in ('lod1_file', 'lod2_file')]
    if not row['triangles'] > low[0]['triangles'] > low[1]['triangles'] > 0:
        errors.append({'file': row['file'], 'reason': 'LOD triangle ordering'})
triplets = []
for crop in manifest['crops']:
    for variant in manifest['variant_ids']:
        assets = sorted((a for a in manifest['assets'] if a['crop']==crop and a['variant']==variant), key=lambda a:a['stage'])
        assert [a['stage'] for a in assets] == [1,2,3]
        assert len({a['stable_seed'] for a in assets}) == 1
        r = [by_file[Path(a['mesh_file']).name] for a in assets]
        heights = [x['dimensions_m'][2] for x in r]
        assert heights[0] < heights[1] < heights[2]
        triplets.append({'crop': crop, 'variant': variant, 'stable_seed': assets[0]['stable_seed'],
                         'root_origins_m': [x['origin_m'] for x in r], 'heights_m': heights,
                         'z_ranges_m': [[x['bounds_min_m'][2],x['bounds_max_m'][2]] for x in r]})
report = {'blender_version': bpy.app.version_string, 'fbx_count': len(rows), 'meshes': rows,
          'materials': materials, 'stage_triplets': triplets, 'errors': errors,
          'source_only': True, 'rendered': False}
(ROOT / ('Receipts/fbx-engine-audit.json' if use_engine else 'Receipts/fbx-derived-audit.json' if use_derived else 'Receipts/fbx-audit.json')).write_text(json.dumps(report, indent=2), encoding='utf-8')
print('CROPS_FBX_AUDIT', json.dumps({'count': len(rows), 'materials': list(materials), 'errors': len(errors)}))
if errors:
    raise RuntimeError(json.dumps(errors[:3]))
