"""Import the ASH-12 materials, viewmodel mesh and its clips.

Surfaces are authored as plain gunmetal, polymer and steel rather than the
source pack's decal skin, so the materials carry colours and scalars only.

Run headless:
  UnrealEditor-Cmd.exe FPSGAME.uproject -run=pythonscript -script=<this file> -unattended -NullRHI -nosplash
"""
import json
from pathlib import Path

import unreal as u

O = Path(__file__).resolve().parent
D = '/Game/Weapons/ASH12/Integrated20260917'
REFERENCE = '/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416'
COMPRESSION = '/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'

# part -> (base colour, roughness, metallic, identity)
MATERIALS = {
    "Upper": ("upper", (0.085, 0.090, 0.098), 0.45, 0.70, "gunmetal receiver"),
    "Lower": ("lower", (0.080, 0.085, 0.092), 0.47, 0.70, "gunmetal lower"),
    "Front": ("front", (0.090, 0.095, 0.103), 0.45, 0.70, "gunmetal handguard"),
    "Sights": ("sights", (0.065, 0.068, 0.072), 0.50, 0.65, "matte sight housing"),
    "Flash_Hider": ("flash_hider", (0.320, 0.330, 0.340), 0.32, 0.90, "bare steel"),
    "Magazine": ("magazine", (0.050, 0.050, 0.052), 0.60, 0.05, "black polymer"),
    "Magazine_Base": ("magazine_base", (0.044, 0.044, 0.046), 0.62, 0.05, "black polymer"),
}
MATERIALS_DROPPED = ('Upper', 'Lower', 'Front', 'Sights', 'Flash_Hider', 'Magazine', 'Magazine_Base')

tools = u.AssetToolsHelpers.get_asset_tools()
editing = u.MaterialEditingLibrary
reference = u.load_asset(REFERENCE)
bindings = {str(slot.material_slot_name): slot.material_interface for slot in reference.materials}
receipt = {'materials': {}, 'mesh': {}, 'clips': {}, 'removed_textures': []}


def connect(a, out, b, pin):
    if not editing.connect_material_expressions(a, out, b, pin):
        raise RuntimeError('material connection failed: ' + pin)


def output(expr, out, prop):
    if not editing.connect_material_property(expr, out, prop):
        raise RuntimeError('material output failed: ' + str(prop))


def scalar(material, value):
    node = editing.create_material_expression(material, u.MaterialExpressionConstant, -400, 0)
    node.set_editor_property('r', value)
    return node


# The decal skin that shipped with the source pack is not used.
for texture in list(u.EditorAssetLibrary.list_assets(D + '/Textures', True, False)):
    if 'T_ASH12_' in texture:
        u.EditorAssetLibrary.delete_asset(texture)
        receipt['removed_textures'].append(texture)

for part, (slug, colour, roughness, metallic, identity) in MATERIALS.items():
    name = 'M_ASH12_' + part
    path = D + '/Materials/' + name
    material = (u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path)
                else tools.create_asset(name, D + '/Materials', u.Material, u.MaterialFactoryNew()))
    editing.delete_all_material_expressions(material)
    editing.set_material_usage(material, u.MaterialUsage.MATUSAGE_SKELETAL_MESH)

    base = editing.create_material_expression(material, u.MaterialExpressionConstant3Vector, -500, -300)
    base.set_editor_property('constant', u.LinearColor(colour[0], colour[1], colour[2], 1.0))
    output(base, '', u.MaterialProperty.MP_BASE_COLOR)

    output(scalar(material, float(roughness)), '', u.MaterialProperty.MP_ROUGHNESS)
    output(scalar(material, float(metallic)), '', u.MaterialProperty.MP_METALLIC)

    editing.recompile_material(material)
    if not u.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError('material save failed: ' + name)
    receipt['materials'][name] = {'path': material.get_path_name(), 'identity': identity,
                                  'colour': colour, 'roughness': roughness, 'metallic': metallic}

options = u.FbxImportUI()
options.automated_import_should_detect_type = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_SKELETAL_MESH
options.import_as_skeletal = True
options.import_mesh = True
options.import_animations = False
options.import_materials = False
options.import_textures = False
options.create_physics_asset = False
data = options.skeletal_mesh_import_data
data.set_editor_property('update_skeleton_reference_pose', False)
data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
data.normal_generation_method = u.FBXNormalGenerationMethod.MIKK_T_SPACE
task = u.AssetImportTask()
task.filename = str(O / 'SK_ASH12_Manny.fbx')
task.destination_path = D
task.destination_name = 'SK_ASH12_Manny'
task.options = options
task.automated = True
task.replace_existing = True
task.save = False
tools.import_asset_tasks([task])
mesh = u.load_asset(D + '/SK_ASH12_Manny')
if not mesh:
    raise RuntimeError('mesh import failed')

slots = mesh.materials
for i, slot in enumerate(slots):
    slot_name = str(slot.material_slot_name)
    material = receipt['materials'].get(slot_name)
    slot.material_interface = u.load_asset(D + '/Materials/' + slot_name) if material else bindings[slot_name]
    slots[i] = slot
mesh.set_editor_property('materials', slots)
# Bone compression lives on the mesh asset in 5.8, not on the import options.
try:
    mesh.set_editor_property('bone_compression_settings', u.load_asset(COMPRESSION))
except Exception as error:  # noqa: BLE001 - report and keep the engine default
    u.log_warning('ASH12_BONE_COMPRESSION skipped: %s' % error)
if not u.EditorAssetLibrary.save_loaded_asset(mesh, False):
    raise RuntimeError('mesh save failed')
receipt['mesh'] = {'path': mesh.get_path_name(), 'skeleton': mesh.skeleton.get_path_name(),
                   'slots': [str(s.material_slot_name) for s in slots]}

for kind in ['idle', 'aim', 'fire', 'aim_fire', 'reload', 'reload_empty', 'equip_charge']:
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    options.import_mesh = False
    options.import_animations = True
    options.import_materials = False
    options.import_textures = False
    options.skeleton = mesh.skeleton
    options.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
    options.anim_sequence_import_data.set_editor_property('custom_sample_rate', 120)
    task = u.AssetImportTask()
    task.filename = str(O / ('A_ASH12_%s.fbx' % kind))
    task.destination_path = D + '/Animations'
    task.destination_name = 'A_ASH12_' + kind
    task.options = options
    task.automated = True
    task.replace_existing = True
    task.save = False
    tools.import_asset_tasks([task])
    clip = u.load_asset(D + '/Animations/A_ASH12_' + kind)
    if not clip:
        raise RuntimeError('clip import failed: ' + kind)
    clip.set_editor_property('bone_compression_settings', u.load_asset(COMPRESSION))
    if not u.EditorAssetLibrary.save_loaded_asset(clip, False):
        raise RuntimeError('clip save failed: ' + kind)
    receipt['clips'][kind] = {'path': clip.get_path_name(), 'duration': clip.get_play_length()}

u.EditorAssetLibrary.save_directory(D, False, True)
receipt['status'] = 'Imported and saved; gameplay testing pending'
(O / 'import.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
u.log('ASH12_IMPORT_COMPLETE')
