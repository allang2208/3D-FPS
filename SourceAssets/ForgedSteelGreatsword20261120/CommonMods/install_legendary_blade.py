"""Save a fitted legendary blade mesh and its matching workbench icon."""
import json
from pathlib import Path

import unreal as u


def import_asset(source, folder, name, options=None):
    task = u.AssetImportTask()
    task.filename = str(source)
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    if options:
        task.options = options
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    path = f'{folder}/{name}.{name}'
    if path not in task.imported_object_paths:
        raise RuntimeError('Import did not produce ' + path)
    return u.load_asset(path)


def install(here, module, option, stage_name):
    project = here.parents[2]
    mesh_name = 'SM_ForgedSteelGreatsword_' + module
    mesh_folder = '/Game/Weapons/ForgedSteelGreatsword20261120/' + module
    icon_key = 'ue_forged_steel_greatsword_blade_1_' + option
    icon_folder = '/Game/ColdSteelData/AttachmentIcons20260913'
    surface = json.loads((here.parent / 'CommonMods/blade_materials.json').read_text(encoding='utf-8'))

    host = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()
    stage = project / 'Saved/ForgedSteelGreatsword20261120' / stage_name
    if host not in (project, stage):
        raise RuntimeError('Unexpected asset import project: ' + str(host))
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
        if not editor or editor.is_in_play_in_editor():
            raise RuntimeError('Asset import requires an idle editor or a background commandlet')
    targets = {mesh_folder + '/' + mesh_name, icon_folder + '/' + icon_key}
    for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        if package.get_name() in targets:
            raise RuntimeError('Unsaved work in ' + package.get_name())

    material = u.load_asset(surface['base'])
    if not material:
        raise RuntimeError('Missing forged steel finish ' + surface['base'])
    worlds = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    u.SystemLibrary.execute_console_command(worlds.get_editor_world() if worlds else None,
                                           'Interchange.FeatureFlags.Import.FBX 0')
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    options.import_mesh = True
    options.import_as_skeletal = options.import_animations = False
    options.import_materials = options.import_textures = False
    settings = options.static_mesh_import_data
    settings.combine_meshes = True
    settings.auto_generate_collision = settings.generate_lightmap_u_vs = False
    settings.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    settings.normal_generation_method = u.FBXNormalGenerationMethod.MIKK_T_SPACE
    settings.build_nanite = True
    mesh = import_asset(here / (mesh_name + '.fbx'), mesh_folder, mesh_name, options)
    for index, slot in enumerate(mesh.static_materials):
        if str(slot.material_slot_name) not in surface['slots']['factory']:
            raise RuntimeError('Unexpected forged steel material slot: ' + str(slot.material_slot_name))
        mesh.set_material(index, material)
    nanite = mesh.get_editor_property('nanite_settings')
    nanite.enabled = nanite.explicit_tangents = True
    nanite.fallback_relative_error = 0
    mesh.set_editor_property('nanite_settings', nanite)
    icon = import_asset(project / 'Content' / icon_folder.removeprefix('/Game/') / (icon_key + '.png'),
                        icon_folder, icon_key)
    icon.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_UI)
    icon.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_EDITOR_ICON)
    icon.set_editor_property('mip_gen_settings', u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    icon.set_editor_property('srgb', True)
    icon.set_editor_property('never_stream', True)
    if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost(), icon.get_outermost()], False):
        raise RuntimeError('Could not save ' + module + ' and its workbench card')
    receipt = {'assets': [mesh.get_path_name(), icon.get_path_name()], 'complete': True}
    receipt_dir = stage if host == stage else here
    (receipt_dir / 'import_receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
