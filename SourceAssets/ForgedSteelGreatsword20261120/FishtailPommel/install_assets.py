"""Save the approved fish-tail mesh and workbench card with the stock sword bindings."""
import json
import runpy
from pathlib import Path

import unreal as u


here = Path(__file__).resolve().parent
project = here.parents[2]
active = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    raise RuntimeError('Use a background Python commandlet')
if active != project.resolve() and not (active/'FishtailAuthor.uproject').is_file():
    raise RuntimeError('Use FPSGAME or the isolated FishtailAuthor project')

root = '/Game/Weapons/ForgedSteelGreatsword20261120'
mesh_name = 'SM_ForgedSteelGreatsword_FishtailPommel'
icon_name = 'ue_forged_steel_greatsword_pommel_fishtail_pommel'
icon_folder = '/Game/ColdSteelData/AttachmentIcons20260913'
artwork = project/'Content'/icon_folder.removeprefix('/Game/')/(icon_name+'.png')
fbx = here/(mesh_name+'.fbx')
material_name = 'M_ForgedSteelGreatsword_Surface_V1'
material = u.load_asset(f'{root}/V1/Materials/{material_name}.{material_name}')
if not material:
    raise RuntimeError('Missing the original forged sword material')

world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
u.SystemLibrary.execute_console_command(world, 'Interchange.FeatureFlags.Import.FBX 0')
options = u.FbxImportUI()
options.automated_import_should_detect_type = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
options.import_mesh = True
options.import_as_skeletal = options.import_animations = False
options.import_materials = options.import_textures = False
settings = options.static_mesh_import_data
settings.combine_meshes = True
settings.auto_generate_collision = settings.generate_lightmap_u_vs = False
settings.build_nanite = True
settings.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
settings.normal_generation_method = u.FBXNormalGenerationMethod.MIKK_T_SPACE
import_asset = runpy.run_path(str(here.parent/'CommonMods/install_legendary_blade.py'))['import_asset']
mesh = import_asset(fbx, root+'/FishtailPommel', mesh_name, options)
if [str(slot.material_slot_name) for slot in mesh.static_materials] != [material_name]:
    raise RuntimeError('Unexpected fish-tail material slot')
mesh.set_material(0, material)
nanite = mesh.get_editor_property('nanite_settings')
nanite.enabled = nanite.explicit_tangents = True
nanite.fallback_relative_error = 0
mesh.set_editor_property('nanite_settings', nanite)

card = import_asset(artwork, icon_folder, icon_name)
card.set_editor_properties({
    'lod_group': u.TextureGroup.TEXTUREGROUP_UI,
    'compression_settings': u.TextureCompressionSettings.TC_EDITOR_ICON,
    'mip_gen_settings': u.TextureMipGenSettings.TMGS_NO_MIPMAPS,
    'never_stream': True,
    'srgb': True,
})
assets = [mesh, card]
if not u.EditorLoadingAndSavingUtils.save_packages([a.get_outermost() for a in assets],False):
    raise RuntimeError('Could not save fish-tail mesh and icon')

receipt = {'complete': True, 'assets': [a.get_path_name() for a in assets],
           'material': mesh.get_material(0).get_path_name(),
           'sources': [a.get_editor_property('asset_import_data').get_first_filename() for a in assets],
           'icon_pixels': [card.blueprint_get_size_x(),card.blueprint_get_size_y()]}
receipt_dir = here if active == project.resolve() else active.parent
(receipt_dir/'import_receipt.json').write_text(json.dumps(receipt, indent=2)+'\n',encoding='utf-8')
print('FISHTAIL_POMMEL_ASSETS_SAVED')
