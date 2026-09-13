"""Import the authored Manny/tool viewmodels and their shared animation clock assets."""
import json
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
SOURCE = ROOT / 'SourceAssets/ProductionToolGrip20260913'
DEST = '/Game/Items/ProductionTools/GripMotion20260913'
TOOLS = u.AssetToolsHelpers.get_asset_tools()
EAL = u.EditorAssetLibrary
receipt = {'saved': [], 'runtime_tested': False}
u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')


def save(asset):
    if not EAL.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save: ' + str(asset))
    receipt['saved'].append(asset.get_path_name())


def import_asset(file, name, options=None):
    task = u.AssetImportTask()
    task.filename = str(file)
    task.destination_path = DEST
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    if options:
        task.options = options
    TOOLS.import_asset_tasks([task])
    asset = u.load_asset(DEST + '/' + name)
    if not asset:
        raise RuntimeError('Could not import: ' + str(file))
    return asset


EAL.make_directory(DEST)
current_arms = u.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416')
bindings = {str(slot.material_slot_name): slot.material_interface for slot in current_arms.get_editor_property('materials')}
for kind in ['Axe', 'Pickaxe']:
    original = f'/Game/Items/ProductionTools/FreeFab20260913/{kind}/M_Free{kind}'
    name = 'M_Harvest_' + kind
    material = u.load_asset(DEST + '/' + name) or EAL.duplicate_asset(original, DEST + '/' + name)
    material.set_editor_property('used_with_skeletal_mesh', True)
    u.MaterialEditingLibrary.recompile_material(material)
    save(material)
    bindings[name] = material
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_as_skeletal = True
    options.import_mesh = True
    options.import_animations = False
    options.import_materials = False
    options.import_textures = False
    options.create_physics_asset = False
    options.skeletal_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    options.skeletal_mesh_import_data.vertex_color_import_option = u.VertexColorImportOption.REPLACE
    mesh = import_asset(SOURCE / f'Export/SK_Harvest_{kind}.fbx', 'SK_Harvest_' + kind, options)
    slots = mesh.get_editor_property('materials')
    for i, slot in enumerate(slots):
        slot.material_interface = bindings[str(slot.material_slot_name)]
        slots[i] = slot
    mesh.set_editor_property('materials', slots)
    mesh.set_editor_property('positive_bounds_extension', u.Vector(80, 80, 80))
    mesh.set_editor_property('negative_bounds_extension', u.Vector(80, 80, 80))
    save(mesh)
    for clip in ['Idle', 'Walk', 'Equip', 'Swing', 'HitRecover']:
        options = u.FbxImportUI()
        options.automated_import_should_detect_type = False
        options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
        options.import_mesh = False
        options.import_animations = True
        options.import_materials = False
        options.import_textures = False
        options.skeleton = mesh.skeleton
        options.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
        options.anim_sequence_import_data.set_editor_property('custom_sample_rate', 150)
        name = f'A_Harvest_{kind}_{clip}'
        animation = import_asset(SOURCE / f'Export/{name}.fbx', name, options)
        compression = u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
        if compression:
            animation.set_editor_property('bone_compression_settings', compression)
        save(animation)
sound = import_asset(ROOT / 'SourceAssets/RuneSword20260913/Reference/Sword_Swing.wav', 'S_Harvest_Swing')
sound.set_editor_property('loading_behavior', u.SoundWaveLoadingBehavior.FORCE_INLINE)
save(sound)
(SOURCE / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
u.log('HARVEST_SINGLE_HAND_ASSETS_IMPORTED')
