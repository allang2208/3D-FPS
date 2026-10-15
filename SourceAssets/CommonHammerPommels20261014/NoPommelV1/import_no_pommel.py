"""Save the light end closure and approved removal icon, then publish their option."""
import json
import runpy
import shutil
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
catalog = runpy.run_path(str(P / 'catalog.py'))
D = catalog['MESH_DIR']
ICONS = '/Game/ColdSteelData/AttachmentIcons20260913'
if Path(u.Paths.project_dir()).resolve() != ROOT:
    raise RuntimeError('Wrong target project')
editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
if '-run=' not in u.SystemLibrary.get_command_line().lower() and editor and editor.is_in_play_in_editor():
    raise RuntimeError('PIE is active; defer this asset batch')
row = json.loads((P / 'exports.json').read_text(encoding='utf-8'))['parts'][0]
key = 'pommel_' + row['id']
targets = {D + '/' + row['mesh'], ICONS + '/' + key}
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if package.get_name() in targets:
        raise RuntimeError('Unsaved target: ' + package.get_name())
materials = {
    'M_SteelWarhammerSurface': u.load_asset('/Game/Weapons/SteelWarhammer20261014/Materials/M_SteelWarhammerSurface'),
    'M_CommonHammerHeadSteel': u.load_asset('/Game/Weapons/CommonHammerHeads20261014/Materials/M_CommonHammerHeadSteel')
}
if any(not material for material in materials.values()):
    raise RuntimeError('Existing steel material is unavailable')
A = u.AssetToolsHelpers.get_asset_tools()
receipt = {'complete': False, 'tested': False, 'assets': [], 'revision': 'NoPommelV1'}

def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False):
        raise RuntimeError('Save failed: ' + asset.get_path_name())
    receipt['assets'].append(asset.get_path_name())
    (P / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')

u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')
opt = u.FbxImportUI()
opt.automated_import_should_detect_type = False
opt.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
opt.import_mesh = True
opt.import_as_skeletal = False
opt.import_materials = False
opt.import_textures = False
opt.import_animations = False
data = opt.static_mesh_import_data
data.combine_meshes = True
data.auto_generate_collision = False
data.generate_lightmap_u_vs = False
data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
data.vertex_color_import_option = u.VertexColorImportOption.REPLACE
path = D + '/' + row['mesh']
mesh = u.load_asset(path)
if not mesh:
    task = u.AssetImportTask()
    task.filename = str(P / 'Export' / (row['mesh'] + '.fbx'))
    task.destination_path = D
    task.destination_name = row['mesh']
    task.automated = True
    task.save = False
    task.options = opt
    A.import_asset_tasks([task])
    mesh = u.load_asset(path)
    if not mesh:
        raise RuntimeError('Mesh import failed: ' + path)
for index, slot in enumerate(mesh.get_editor_property('static_materials')):
    name = str(slot.material_slot_name)
    if name not in materials:
        raise RuntimeError('Unknown material slot: ' + name)
    mesh.set_material(index, materials[name])
save(mesh)

source = P / 'Icons/no_pommel.png'
task = u.AssetImportTask()
task.filename = str(source)
task.destination_path = ICONS
task.destination_name = key
task.automated = True
task.replace_existing = True
task.save = False
A.import_asset_tasks([task])
texture = u.load_asset(ICONS + '/' + key)
if not texture:
    raise RuntimeError('Icon import failed: ' + key)
texture.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_UI)
texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_EDITOR_ICON)
texture.set_editor_property('mip_gen_settings', u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
texture.set_editor_property('srgb', True)
texture.set_editor_property('never_stream', True)
save(texture)
shutil.copy2(source, ROOT / 'Content/ColdSteelData/AttachmentIcons20260913' / (key + '.png'))
receipt['complete'] = True
(P / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
runpy.run_path(str(P / 'register_no_pommel.py'), run_name='__main__')
print('NO_POMMEL_ASSETS_SAVED ' + json.dumps(receipt), flush=True)
