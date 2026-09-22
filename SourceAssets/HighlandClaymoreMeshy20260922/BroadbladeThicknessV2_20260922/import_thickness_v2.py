"""Install the thickness-only broadblade revision and its matching UI icon."""
import json
import os
import shutil
from pathlib import Path
from datetime import datetime
import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
DATA = ROOT / 'Content/ColdSteelData'
spec = json.loads((P / 'authoring.json').read_text(encoding='utf-8'))
catalog_path = DATA / 'highland-claymore-modules.json'
current = json.loads(catalog_path.read_text(encoding='utf-8-sig'))
source_asset = current['slots']['blade_1']['highland_broadblade']['mesh']
L = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world() is not None:
    raise RuntimeError('End active play before applying broadblade mesh edits.')
original = u.load_asset(source_asset)
if not original:
    raise RuntimeError('The currently installed broadblade mesh is unavailable.')
stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
before_dir = P / 'Before' / stamp
before_dir.mkdir(parents=True, exist_ok=True)
receipt = {'complete': False, 'time': stamp, 'editor_pid': os.getpid(),
           'previous_mesh': source_asset, 'assets': [], 'backup': str(before_dir),
           'gameplay_changes': False, 'tested': False}


def record():
    (P / 'install_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')


def imported(file, name, folder, options=None):
    task = u.AssetImportTask()
    task.filename = str(file)
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    if options:
        task.options = options
    A.import_asset_tasks([task])
    asset = u.load_asset(folder + '/' + name)
    if not asset or not task.imported_object_paths:
        raise RuntimeError('Import failed: ' + str(file))
    return asset


def saved(asset, file):
    if not L.save_loaded_asset(asset, False):
        raise RuntimeError('Asset save failed: ' + asset.get_path_name())
    receipt['assets'].append({'asset': asset.get_path_name(), 'source': str(file), 'saved': True})
    record()


u.SystemLibrary.execute_console_command(editor.get_editor_world(), 'Interchange.FeatureFlags.Import.FBX 0')
options = u.FbxImportUI()
options.automated_import_should_detect_type = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
options.import_as_skeletal = False
options.import_mesh = True
options.import_materials = False
options.import_textures = False
options.import_animations = False
cfg = options.static_mesh_import_data
cfg.combine_meshes = True
cfg.auto_generate_collision = False
cfg.generate_lightmap_u_vs = False
cfg.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
cfg.vertex_color_import_option = u.VertexColorImportOption.REPLACE
fbx = P / 'Export' / (spec['mesh'] + '.fbx')
mesh = imported(fbx, spec['mesh'], spec['ue_folder'], options)
for index, material in enumerate(original.static_materials):
    mesh.set_material(index, material.material_interface)
static = u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
settings = static.get_lod_build_settings(mesh, 0)
settings.recompute_normals = False
settings.recompute_tangents = False
settings.use_full_precision_u_vs = True
static.set_lod_build_settings(mesh, 0, settings)
saved(mesh, fbx)

icon_file = DATA / 'AttachmentIcons20260913' / spec['icon']
if icon_file.exists():
    shutil.copy2(icon_file, before_dir / icon_file.name)
shutil.copy2(P / 'Icons' / spec['icon'], icon_file)
icon = imported(icon_file, icon_file.stem, '/Game/ColdSteelData/AttachmentIcons20260913')
icon.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_EDITOR_ICON)
icon.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_UI)
icon.set_editor_property('mip_gen_settings', u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
icon.set_editor_property('srgb', True)
saved(icon, icon_file)

# Only change this option's appearance; leave stats, traces and other slots intact.
before = catalog_path.read_bytes()
catalog = json.loads(before.decode('utf-8-sig'))
module = catalog['slots']['blade_1']['highland_broadblade']
if module['mesh'] != source_asset:
    raise RuntimeError('Broadblade was replaced during import; live catalog preserved.')
module['mesh'] = mesh.get_path_name()
module['appearance'] = '高地专属 · 加厚剑脊与立体刃面'
if catalog_path.read_bytes() != before:
    raise RuntimeError('Module catalog changed during update; current catalog preserved.')
(before_dir / catalog_path.name).write_bytes(before)
temp = catalog_path.with_suffix('.thickness-v2.tmp')
temp.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
temp.replace(catalog_path)
receipt['catalog'] = str(catalog_path)
receipt['mesh'] = mesh.get_path_name()
receipt['complete'] = True
receipt['native_build_required'] = False
opened = P / 'editor-open-for-import.json'
receipt['fresh_editor_for_import'] = opened.exists() and json.loads(opened.read_text(encoding='utf-8-sig'))['process_id'] == os.getpid()
record()
print('HIGHLAND_BROADBLADE_THICK_V2_INSTALLED ' + mesh.get_path_name())
