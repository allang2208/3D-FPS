"""Background production import: static hammer, PBR textures, UI icon, saved receipt."""
import json
import sys
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
D = '/Game/Weapons/RuneboundWarhammer20261022'
if Path(u.Paths.project_dir()).resolve() != ROOT:
    raise RuntimeError('Wrong Unreal project')
sys.path.insert(0, str(ROOT / 'SourceAssets/SteelWarhammer20261014'))
from warhammer_surface import build_surface

A = u.AssetToolsHelpers.get_asset_tools()
receipt = {'assets': [], 'complete': False, 'tested': False,
           'animation_policy': 'Direct reuse of live shared warhammer first/third-person animations'}

def save(asset):
    if not asset or not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False):
        raise RuntimeError('Save failed: ' + str(asset))
    if asset.get_path_name() not in receipt['assets']:
        receipt['assets'].append(asset.get_path_name())
    (P / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    return asset

def imp(source, name, folder, options=None):
    asset = u.load_asset(folder + '/' + name)
    if asset:
        return asset
    task = u.AssetImportTask()
    task.filename = str(source)
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = False
    task.save = False
    if options:
        task.options = options
    A.import_asset_tasks([task])
    asset = u.load_asset(folder + '/' + name)
    if not asset:
        raise RuntimeError('Import failed: ' + str(source))
    return asset

textures = {}
for key in ('BaseColor', 'MetallicRoughness', 'Normal'):
    tex = imp(P / 'Textures' / (key + '.jpg'), 'T_RuneboundWarhammer_' + key, D + '/Textures')
    tex.set_editor_property('srgb', key == 'BaseColor')
    tex.set_editor_property('compression_settings',
        u.TextureCompressionSettings.TC_NORMALMAP if key == 'Normal' else
        u.TextureCompressionSettings.TC_MASKS if key == 'MetallicRoughness' else
        u.TextureCompressionSettings.TC_DEFAULT)
    if key == 'Normal':
        tex.set_editor_property('flip_green_channel', True)
    textures[key] = save(tex)

mat = u.load_asset(D + '/Materials/M_RuneboundWarhammerSurface')
if not mat:
    mat = A.create_asset('M_RuneboundWarhammerSurface', D + '/Materials', u.Material, u.MaterialFactoryNew())
build_surface(mat, textures)
# This material is used only by rigid static components, including the WPN_root attachment.
mat.set_editor_property('used_with_skeletal_mesh', False)
mat.set_editor_property('used_with_nanite', True)
mat.set_editor_property('two_sided', True)
u.MaterialEditingLibrary.recompile_material(mat)
save(mat)
u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')
options = u.FbxImportUI()
options.automated_import_should_detect_type = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
options.import_mesh = True
options.import_as_skeletal = False
options.import_animations = False
options.import_materials = False
options.import_textures = False
options.static_mesh_import_data.combine_meshes = True
options.static_mesh_import_data.auto_generate_collision = True
options.static_mesh_import_data.generate_lightmap_u_vs = False
options.static_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
mesh = imp(P / 'Export/SM_RuneboundWarhammer.fbx', 'SM_RuneboundWarhammer', D, options)
mesh.set_material(0, mat)
settings = mesh.get_editor_property('nanite_settings')
settings.enabled = True
settings.explicit_tangents = True
settings.fallback_percent_triangles = 1.0
settings.fallback_relative_error = 0.0
mesh.set_editor_property('nanite_settings', settings)
save(mesh)
icon = imp(P / 'Export/ue_runebound_warhammer.png', 'ue_runebound_warhammer', '/Game/ColdSteelData/Icons')
icon.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_UI)
icon.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_EDITOR_ICON)
icon.set_editor_property('srgb', True)
icon.set_editor_property('never_stream', True)
icon.set_editor_property('mip_gen_settings', u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
save(icon)
receipt.update(complete=True, shared_arms='/Game/Weapons/SteelWarhammer20261014/SprintDragV1/SK_Warhammer_BareArmsSprintV1',
               shared_grip_profile='/Game/Weapons/SteelWarhammer20261014/RhythmClearanceV2/DA_Warhammer_Clearance')
(P / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('RUNEBOUND_WARHAMMER_IMPORT_COMPLETE ' + json.dumps(receipt))
