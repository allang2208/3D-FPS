"""Import the exclusive broad blade/icon, then merge only its live catalog rows."""
import copy
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
DATA = ROOT / 'Content/ColdSteelData'
spec = json.loads((P / 'authoring.json').read_text(encoding='utf-8'))
ID, OPTION, NAME = spec['weapon'], spec['option'], spec['mesh']
L = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world() is not None:
    raise RuntimeError('Finish active play before broadblade asset import.')
factory = u.load_asset('/Game/Weapons/HighlandClaymore20260922/Meshes/SM_Highland_Blade_factory')
if not factory:
    raise RuntimeError('Installed Highland factory blade is required.')
stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
backup = P / 'Before' / stamp
backup.mkdir(parents=True, exist_ok=True)
receipt = {'time': stamp, 'weapon': ID, 'option': OPTION, 'assets': [],
           'catalogs': [], 'backup': str(backup), 'complete': False, 'tested': False,
           'editor_pid': os.getpid()}


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


def save(asset, source):
    if not L.save_loaded_asset(asset, False):
        raise RuntimeError('Asset save failed: ' + asset.get_path_name())
    receipt['assets'].append({'asset': asset.get_path_name(), 'source': str(source), 'saved': True})
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
fbx = P / 'Export' / (NAME + '.fbx')
mesh = imported(fbx, NAME, spec['ue_folder'], options)
for index, material in enumerate(factory.static_materials):
    mesh.set_material(index, material.material_interface)
static = u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
settings = static.get_lod_build_settings(mesh, 0)
settings.recompute_normals = False
settings.recompute_tangents = False
settings.use_full_precision_u_vs = True
static.set_lod_build_settings(mesh, 0, settings)
save(mesh, fbx)

icon_source = P / 'Icons' / spec['icon']
icon_path = DATA / 'AttachmentIcons20260913' / spec['icon']
if icon_path.exists():
    shutil.copy2(icon_path, backup / icon_path.name)
shutil.copy2(icon_source, icon_path)
icon = imported(icon_path, icon_path.stem, '/Game/ColdSteelData/AttachmentIcons20260913')
icon.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_EDITOR_ICON)
icon.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_UI)
icon.set_editor_property('mip_gen_settings', u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
icon.set_editor_property('srgb', True)
save(icon, icon_path)


def merge(name, update):
    # Read immediately before the narrow merge to retain parallel catalog edits.
    path = DATA / name
    before = path.read_bytes()
    data = json.loads(before.decode('utf-8-sig'))
    update(data)
    if path.read_bytes() != before:
        raise RuntimeError('Catalog changed during update; original preserved: ' + name)
    (backup / name).write_bytes(before)
    temp = path.with_suffix('.broadblade.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)
    receipt['catalogs'].append(str(path.relative_to(ROOT)))
    record()


def add_module(data):
    part = copy.deepcopy(data['slots']['blade_1']['factory'])
    part['mesh'] = mesh.get_path_name()
    part['appearance'] = '高地专属 · 宽肩厚脊重刃'
    # Preserve trace length and rune projection width independently of outer steel.
    data['slots']['blade_1'][OPTION] = part


def add_option(data):
    column = next(c for c in data['columns'] if c['key'] == 'blade_1')
    heavy = next(o for o in column['options'] if o['id'] == 'heavy_spine')
    option = copy.deepcopy(heavy)
    option.update(id=OPTION, name='阔锋重刃', weapons=[ID],
                  description='高地双手剑专属。宽肩钢刃与加厚剑脊形成重剑轮廓，中央符文保留原比例；偏重单次伤害与命中硬直。')
    existing = next((i for i, row in enumerate(column['options']) if row['id'] == OPTION), None)
    if existing is None:
        column['options'].append(option)
    else:
        column['options'][existing] = option
    receipt['stats'] = option['stats']
    receipt['stats_source'] = 'Current heavy_spine option'


merge('highland-claymore-modules.json', add_module)
merge('melee-gunsmith.json', add_option)
receipt['complete'] = True
receipt['native_build_required'] = False
receipt['restart_reason'] = 'ModularSwordVisual static catalog is cached for editor process lifetime'
record()
print('HIGHLAND_BROADBLADE_INSTALLED ' + mesh.get_path_name())
