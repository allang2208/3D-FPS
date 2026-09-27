"""Background import/save of the derived grille kit; no map or gameplay run."""
import json
import re
import sys
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[1]
BASE = '/Game/Dungeons/EliteGate20260926/Meshes'
if Path(u.Paths.project_dir()).resolve() != ROOT.parents[1].resolve():
    raise RuntimeError('FPSGAME project required')
sys.path.insert(0, str(ROOT.parents[1] / 'Tools/AssetPipeline'))
from dungeon_material_usage import ensure_mesh_material_usage
manifest = json.loads((ROOT / 'Authored/manifest.json').read_text())
receipt = dict(stage='importing', meshes=[], tests_run=False, rendered=False)
receipt_file = ROOT / 'Receipts/import.json'
for item in manifest['objects']:
    path = BASE + '/' + item['name']
    task = u.AssetImportTask()
    task.filename = item['fbx']
    task.destination_path = BASE
    task.destination_name = item['name']
    task.automated = True
    task.replace_existing = True
    task.replace_existing_settings = True
    task.save = False
    options = u.FbxImportUI()
    options.import_mesh = True
    options.import_materials = False
    options.import_textures = False
    options.import_as_skeletal = False
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    data = options.static_mesh_import_data
    data.combine_meshes = True
    data.convert_scene = True
    data.convert_scene_unit = True
    data.transform_vertex_to_absolute = True
    data.auto_generate_collision = False
    data.generate_lightmap_u_vs = False
    data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    data.normal_generation_method = u.FBXNormalGenerationMethod.MIKK_T_SPACE
    data.vertex_color_import_option = u.VertexColorImportOption.REPLACE
    task.options = options
    task.factory = u.FbxFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = u.load_asset(path)
    if not mesh:
        raise RuntimeError('Import failed: ' + path)
    for index, slot in enumerate(mesh.get_editor_property('static_materials')):
        key = re.sub(r'[._][0-9]{3}$', '', str(slot.material_slot_name))
        material_path = item['materials'][key]
        material = u.load_asset(material_path)
        if not material:
            raise RuntimeError('Missing source grille material: ' + material_path)
        mesh.set_material(index, material)
    ensure_mesh_material_usage(mesh)
    # Moving mesh is visual; four runtime box components provide matching collision.
    # Stationary guides stay outside the authored door clear width.
    settings = mesh.get_editor_property('nanite_settings').copy()
    settings.enabled = True
    settings.explicit_tangents = True
    settings.generate_fallback = u.NaniteGenerateFallback.ENABLED
    settings.fallback_target = u.NaniteFallbackTarget.PERCENT_TRIANGLES
    settings.fallback_percent_triangles = 1.
    settings.fallback_relative_error = 0
    mesh.set_editor_property('nanite_settings', settings)
    if not u.PlazaInstanceTools.build_nanite_data(mesh):
        raise RuntimeError('Nanite build failed: ' + path)
    if not u.EditorAssetLibrary.save_loaded_asset(mesh, False):
        raise RuntimeError('Save failed: ' + path)
    receipt['meshes'].append(path)
    receipt_file.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    u.collect_garbage()
receipt['stage'] = 'meshes_saved'
receipt_file.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('ELITE_GRILLE_ASSETS_SAVED', len(receipt['meshes']), flush=True)
