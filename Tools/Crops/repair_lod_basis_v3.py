"""Repair only invalid per-corner shading bases; original attachments stay intact."""
import hashlib
import json
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2] / 'SourceAssets/CropsV3_20261022'
audit = json.loads((ROOT / 'Receipts/fbx-audit.json').read_text())
out = ROOT / 'Derived/Models'
out.mkdir(parents=True, exist_ok=True)
repairs = []
for error in audit['errors']:
    row = error['row']
    assert row['zero_area_geometry'] == row['zero_area_uv'] == 0
    path = ROOT / 'Source/Models' / row['file']
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path), use_anim=False)
    obj = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
    mesh = obj.data
    mesh.calc_tangents(uvmap=mesh.uv_layers.active.name)
    normals = [c.vector.copy() for c in mesh.corner_normals]
    bad_faces = [p for p in mesh.polygons if any(normals[i].length < .5 or mesh.loops[i].tangent.length < .5 for i in p.loop_indices)]
    for polygon in bad_faces:
        for loop in polygon.loop_indices:
            normals[loop] = polygon.normal.copy()
    mesh.normals_split_custom_set(normals)
    mesh.calc_tangents(uvmap=mesh.uv_layers.active.name)
    assert all(n.vector.length > .5 for n in mesh.corner_normals), path.name
    assert all(l.tangent.length > .5 for l in mesh.loops), path.name
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    target = out / path.name
    bpy.ops.export_scene.fbx(filepath=str(target), use_selection=True, object_types={'MESH'},
                             use_mesh_modifiers=False, bake_anim=False, add_leaf_bones=False,
                             axis_forward='-Z', axis_up='Y', apply_unit_scale=True,
                             mesh_smooth_type='OFF', use_tspace=True, path_mode='RELATIVE')
    repairs.append({'file':path.name, 'affected_faces':len(bad_faces),
                    'original_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                    'derived_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
                    'repair':'Use geometric face normals for corners of faces with invalid normal/tangent; regenerate MikkTSpace tangents.'})
(ROOT / 'Receipts/lod-basis-repairs.json').write_text(json.dumps(repairs, indent=2), encoding='utf-8')
print('CROPS_BASIS_REPAIRED', len(repairs))
