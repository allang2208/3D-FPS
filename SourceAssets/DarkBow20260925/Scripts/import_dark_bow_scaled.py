"""Re-import SK_DarkBow at real bow scale, with the axis contract read off the measured bounds.

Measured facts this build (see ue_parts_readback.json, `combine_meshes=False`, scale 1.0):
  size_cm [113.057, 10.385, 414.087]  origin_cm [-19.444, -2.767, 0.452]  5710 tris  3 sections
So in this asset's local space: **length = Z** (not X), **front/back = X**, **thin = Y**.
The Fab thumbnail confirms the orientation: the bow stands vertical with the limbs curving to
one side and a *straight string already baked into the mesh* on the other side.

The author modelled it 4.14 m tall, so the import scale is 140 / 414.087 = 0.3381, which puts
the riser at ~140 cm -- a real bow. Collision is generated, materials are kept as imported
(Material_002 / 003 / 005, three instances of FBXLegacyPhongSurfaceMaterial).
"""

import json
import traceback
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
CASE = ROOT / 'SourceAssets' / 'DarkBow20260925'
FBX = CASE / 'Source' / 'dark_bow.fbx'
DEST = '/Game/Weapons/DarkBow20260925'
MESH = DEST + '/SK_DarkBow'
TARGET_LENGTH_CM = 140.0
MEASURED_LENGTH_CM = 414.087          # 上一轮 split 实测的最长轴（局部 Z）

report = {'runtime_tested': False, 'rendered': False, 'target_length_cm': TARGET_LENGTH_CM,
          'measured_length_cm': MEASURED_LENGTH_CM, 'import_scale': round(TARGET_LENGTH_CM / MEASURED_LENGTH_CM, 5)}


def measure(mesh):
    out = {}
    bounds = mesh.get_bounds()
    extent = bounds.box_extent
    out['size_cm'] = [round(abs(extent.x) * 2, 3), round(abs(extent.y) * 2, 3), round(abs(extent.z) * 2, 3)]
    out['origin_cm'] = [round(bounds.origin.x, 3), round(bounds.origin.y, 3), round(bounds.origin.z, 3)]
    out['triangles'] = int(mesh.get_num_triangles(0))
    out['vertices'] = int(mesh.get_num_vertices(0))
    out['sections'] = int(mesh.get_num_sections(0))
    slots = []
    for entry in (mesh.get_editor_property('static_materials') or []):
        material = entry.get_editor_property('material_interface')
        slots.append([str(entry.get_editor_property('material_slot_name')),
                      material.get_path_name() if material else None])
    out['material_slots'] = slots
    return out


try:
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    options.import_mesh = True
    options.import_materials = True
    options.import_textures = False
    options.import_animations = False
    data = options.static_mesh_import_data
    data.import_uniform_scale = report['import_scale']
    data.combine_meshes = True
    data.auto_generate_collision = True
    data.build_nanite = False
    task = u.AssetImportTask()
    task.filename = str(FBX)
    task.destination_path = DEST
    task.destination_name = 'SK_DarkBow'
    task.automated = True
    task.replace_existing = True
    task.save = True
    task.options = options
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = u.load_asset(MESH)
    if mesh is None:
        report['error'] = 'asset missing after import'
    else:
        report.update(measure(mesh))
        # 弓的挂点以"包围盒中心"为原点：网格自身原点偏向弦侧，直接用会把弓握在偏后的位置。
        extent = mesh.get_bounds().box_extent
        report['grip_trim_cm'] = [-round(v, 3) for v in mesh.get_bounds().origin]
        report['saved'] = bool(u.EditorAssetLibrary.save_loaded_asset(mesh))
except Exception as error:
    report['error'] = str(error)[:300]
    report['trace'] = traceback.format_exc(limit=4)

out_file = CASE / 'ue_import_readback.json'
out_file.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding='utf-8')
u.log('DARKBOW_IMPORT ' + json.dumps(report, ensure_ascii=False)[:1500])
print('DARKBOW_IMPORT_READBACK_WRITTEN')
