"""Diagnose the Fab dark bow FBX: import each source node separately and measure.

Why: the merged import produced size_cm [11305.7, 1038.5, 41408.7] -- a 414 m axis for an
asset that must be a hand-held bow. Either the scale factor is wrong or the FBX carries stray
objects whose vertices land far away. `combine_meshes = False` splits the FBX nodes into
separate static meshes so each bounding box can be measured on its own.

Writes SourceAssets/DarkBow20260925/ue_parts_readback.json and saves nothing into the
runtime folder /Game/Weapons/DarkBow20260925 (everything lands under _Diagnose).
"""

import json
import traceback
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
CASE = ROOT / 'SourceAssets' / 'DarkBow20260925'
FBX = CASE / 'Source' / 'dark_bow.fbx'
SCRATCH = '/Game/Weapons/DarkBow20260925/_Diagnose'

report = {'runtime_tested': False, 'rendered': False, 'runs': {}}


def measure(path):
    out = {'path': path}
    mesh = u.load_asset(path)
    if mesh is None:
        out['error'] = 'not found'
        return out
    out['class'] = mesh.get_class().get_name()
    try:
        bounds = mesh.get_bounds()
        extent = bounds.box_extent
        out['size_cm'] = [round(abs(extent.x) * 2, 3), round(abs(extent.y) * 2, 3), round(abs(extent.z) * 2, 3)]
        out['origin_cm'] = [round(bounds.origin.x, 3), round(bounds.origin.y, 3), round(bounds.origin.z, 3)]
        out['triangles'] = int(mesh.get_num_triangles(0))
        out['vertices'] = int(mesh.get_num_vertices(0))
        out['sections'] = int(mesh.get_num_sections(0))
    except Exception as error:
        out['bounds_error'] = str(error)[:200]
    return out


def run(label, scale, combine):
    if u.EditorAssetLibrary.does_directory_exist(SCRATCH):
        u.EditorAssetLibrary.delete_directory(SCRATCH)
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    options.import_mesh = True
    options.import_materials = False
    options.import_textures = False
    options.import_animations = False
    data = options.static_mesh_import_data
    data.import_uniform_scale = scale
    data.combine_meshes = combine
    data.auto_generate_collision = False
    data.build_nanite = False
    task = u.AssetImportTask()
    task.filename = str(FBX)
    task.destination_path = SCRATCH
    task.destination_name = 'PM_DarkBow'
    task.automated = True
    task.replace_existing = True
    task.save = False
    task.options = options
    try:
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    except Exception as error:
        return {'scale': scale, 'combine': combine, 'import_error': str(error)[:200]}
    names = []
    try:
        names = [str(p) for p in (u.EditorAssetLibrary.list_assets(SCRATCH, False, False) or [])]
    except Exception as error:
        return {'scale': scale, 'combine': combine, 'list_error': str(error)[:200]}
    return {'scale': scale, 'combine': combine, 'assets': [measure(name) for name in names]}


try:
    report['runs']['split_scale1'] = run('split_scale1', 1.0, False)
except Exception as error:
    report['runs']['split_scale1'] = {'error': str(error)[:300], 'trace': traceback.format_exc(limit=3)}
u.log('DARKBOW_PARTS split_scale1 -> ' + json.dumps(report['runs']['split_scale1'], ensure_ascii=False)[:1600])

if u.EditorAssetLibrary.does_directory_exist(SCRATCH):
    u.EditorAssetLibrary.delete_directory(SCRATCH)

out_file = CASE / 'ue_parts_readback.json'
out_file.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding='utf-8')
u.log('DARKBOW_PARTS_READBACK ' + str(out_file))
print('DARKBOW_PARTS_READBACK_WRITTEN')
