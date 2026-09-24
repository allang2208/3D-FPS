"""Import only the revised stair/gallery groups; usable by a background Python commandlet."""
import json
import re
from pathlib import Path
import unreal as u

root = Path(__file__).resolve().parents[1]
base = '/Game/Dungeons/BossHall20260922/Meshes/'
if Path(u.Paths.project_dir()).resolve() != root.parents[1].resolve():
    raise RuntimeError('Unexpected project')
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():
    raise RuntimeError('Preserve active game; import remains pending')
manifest = json.loads((root/'Authored/manifest.json').read_text(encoding='utf-8'))
items = [r for r in manifest['objects'] if r['kind'] in ('StairWest', 'StairEast', 'GalleryRails')]
if len(items) != 3:
    raise RuntimeError('Expected exactly the two stairs and gallery rails')
paths = [base+r['name'] for r in items]
dirty = u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
if any(p.get_name() in paths for p in dirty):
    raise RuntimeError('Preserve existing unsaved guardrail edits')
receipt = {'stage': 'importing', 'meshes': [], 'map_modified': False, 'runtime_tested': False}
receipt_path = root/'Receipts/guardrails-import-20260923.json'
for item, path in zip(items, paths):
    old = u.load_asset(path)
    if not old:
        raise RuntimeError('Original installed asset missing: '+path)
    nanite = old.get_editor_property('nanite_settings').copy()
    task = u.AssetImportTask()
    task.filename = item['fbx']; task.destination_path = base.rstrip('/'); task.destination_name = item['name']
    task.automated = True; task.replace_existing = True; task.replace_existing_settings = True; task.save = False
    options = u.FbxImportUI()
    options.import_mesh = True; options.import_materials = False; options.import_textures = False
    options.import_as_skeletal = False; options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    data = options.static_mesh_import_data
    data.combine_meshes = True; data.convert_scene = True; data.convert_scene_unit = True
    data.transform_vertex_to_absolute = True; data.auto_generate_collision = False; data.generate_lightmap_u_vs = False
    data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    data.set_editor_property('vertex_color_import_option', u.VertexColorImportOption.REPLACE)
    task.options = options; task.factory = u.FbxFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = u.load_asset(path)
    if not mesh or not task.get_objects():
        raise RuntimeError('Import did not produce mesh: '+path)
    for index, slot in enumerate(mesh.get_editor_property('static_materials')):
        key = re.sub(r'[._][0-9]{3}$', '', str(slot.material_slot_name))
        material = u.load_asset(item['materials'][key])
        if not material:
            raise RuntimeError('Missing material '+item['materials'][key])
        mesh.set_material(index, material)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag', u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    # Property change notification rebuilds the mesh in commandlets as well; the
    # interactive StaticMeshEditorSubsystem is intentionally unavailable there.
    mesh.set_editor_property('nanite_settings', nanite)
    if not u.EditorAssetLibrary.save_loaded_asset(mesh, False):
        raise RuntimeError('Failed to save '+path)
    receipt['meshes'].append(path)
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
receipt['stage'] = 'saved'
receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('BOSS_GUARDRAILS_IMPORTED', json.dumps(receipt), flush=True)
