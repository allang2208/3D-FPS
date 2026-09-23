"""Import owned ceiling/service mesh assets; does not switch maps or touch actors."""
import json
import re
from datetime import datetime
from pathlib import Path
import unreal as u
ROOT = Path(__file__).resolve().parents[1]
BASE = '/Game/Dungeons/AtmosphereV2/Services'
MAN = json.loads((ROOT/'Authored/geometry-manifest.json').read_text())
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
if not u.get_editor_subsystem(u.UnrealEditorSubsystem):
    raise RuntimeError('Mesh import requires editor Python')
if Path(u.Paths.project_dir()).resolve() != ROOT.parents[1].resolve():
    raise RuntimeError('Different project')
if any(p.get_path_name().startswith(BASE+'/Meshes/') for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserve unsaved service mesh edits')
receipt = dict(stage='importing', meshes={}, tests_run=False)
(ROOT/'Receipts').mkdir(exist_ok=True)

def write():
    (ROOT/'Receipts/meshes.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')


def clean(name):
    return re.sub(r'[._][0-9]{3}$', '', name)


for entry in MAN['objects']:
    if globals().get('SERVICES_MESH_NAMES') and entry['name'] not in SERVICES_MESH_NAMES:continue
    path = BASE+'/Meshes/'+entry['name']
    task = u.AssetImportTask()
    task.filename = entry['fbx']
    task.destination_path = BASE+'/Meshes'
    task.destination_name = entry['name']
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
    data.generate_lightmap_u_vs = False
    data.auto_generate_collision = False
    data.set_editor_property('vertex_color_import_option', u.VertexColorImportOption.REPLACE)
    data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task.options = options
    task.factory = u.FbxFactory()
    A.import_asset_tasks([task])
    mesh = u.load_asset(path)
    if not mesh:
        raise RuntimeError('Failed to import '+path)
    for index, slot in enumerate(mesh.get_editor_property('static_materials')):
        name = clean(str(slot.material_slot_name))
        material_path = entry['materials'].get(name)
        if not material_path: raise RuntimeError('Unmapped service material '+name)
        material = u.load_asset(material_path)
        if not material:
            raise RuntimeError('Required material missing: '+name)
        mesh.set_material(index, material)
    body = mesh.get_editor_property('body_setup')
    body.set_editor_property('collision_trace_flag', u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    settings = mesh.get_editor_property('nanite_settings')
    settings.enabled = True
    mesh.set_editor_property('nanite_settings', settings)
    if not E.save_loaded_asset(mesh, False):
        raise RuntimeError('Mesh save failed '+path)
    receipt['meshes'][entry['name']] = mesh.get_path_name()
    write()
    print('DUNGEON_SERVICE_MESH_SAVED '+entry['name'])

receipt.update(stage='meshes_saved', saved_at=datetime.now().isoformat())
write()
print('DUNGEON_SERVICE_MESHES_SAVED '+json.dumps(receipt))
