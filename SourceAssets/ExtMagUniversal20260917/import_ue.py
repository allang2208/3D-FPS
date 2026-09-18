"""Import SM_ExtMag_Universal and its materials into
/Game/Weapons/ExtMagUniversal20260917/. Run inside UE:
UnrealEditor-Cmd.exe FPSGAME.uproject -run=pythonscript -script=<this file>
"""
import unreal as u
import json
from pathlib import Path

O = Path(__file__).parent
D = '/Game/Weapons/ExtMagUniversal20260917'
A = u.AssetToolsHelpers.get_asset_tools()
report = {'mesh': None, 'materials': {}, 'bounds': None}


def make_material(name, base, rough, metallic=0.0):
    path = f'{D}/{name}'
    if u.EditorAssetLibrary.does_asset_exist(path):
        mat = u.load_asset(path)
    else:
        mat = A.create_asset(name, D, u.Material, u.MaterialFactoryNew())
    # rebuild graph deterministically
    for existing in u.MaterialEditingLibrary.get_material_expressions(mat):
        u.MaterialEditingLibrary.delete_material_expression(mat, existing)
    node = u.MaterialEditingLibrary.create_material_expression(mat, u.MaterialExpressionVectorParameter, -400, 0)
    node.set_editor_property('parameter_name', 'BaseColor')
    node.set_editor_property('default_value', u.LinearColor(*base))
    u.MaterialEditingLibrary.connect_material_property(node, 'Output', u.MaterialProperty.MP_BASE_COLOR)
    rough_node = u.MaterialEditingLibrary.create_material_expression(mat, u.MaterialExpressionScalarParameter, -400, 200)
    rough_node.set_editor_property('parameter_name', 'Roughness')
    rough_node.set_editor_property('default_value', rough)
    u.MaterialEditingLibrary.connect_material_property(rough_node, 'Output', u.MaterialProperty.MP_ROUGHNESS)
    if metallic:
        met_node = u.MaterialEditingLibrary.create_material_expression(mat, u.MaterialExpressionScalarParameter, -400, 400)
        met_node.set_editor_property('parameter_name', 'Metallic')
        met_node.set_editor_property('default_value', metallic)
        u.MaterialEditingLibrary.connect_material_property(met_node, 'Output', u.MaterialProperty.MP_METALLIC)
    u.MaterialEditingLibrary.recompile_material(mat)
    u.EditorAssetLibrary.save_loaded_asset(mat, False)
    return mat


u.log('EXTMAG_IMPORT_BEGIN')
mat_poly = make_material('M_ExtMag_Polymer', (0.035, 0.036, 0.040, 1.0), 0.52)
mat_metal = make_material('M_ExtMag_Metal', (0.10, 0.10, 0.11, 1.0), 0.40, 0.9)
report['materials'] = {m.get_path_name() for m in (mat_poly, mat_metal)}

opt = u.FbxImportUI()
opt.automated_import_should_detect_type = False
opt.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
opt.import_as_skeletal = False
opt.import_mesh = True
opt.import_animations = False
opt.import_materials = False
opt.import_textures = False
opt.create_physics_asset = False
opt.static_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
opt.static_mesh_import_data.normal_generation_method = u.FBXNormalGenerationMethod.MIKK_T_SPACE
opt.static_mesh_import_data.convert_scene_unit = False
opt.static_mesh_import_data.import_translation = u.Vector(0, 0, 0)
opt.static_mesh_import_data.import_rotation = u.Rotator(0, 0, 0)
opt.static_mesh_import_data.import_uniform_scale = 1.0
opt.static_mesh_import_data.combine_meshes = True

task = u.AssetImportTask()
task.filename = str(O / 'FBX' / 'SM_ExtMag_Universal.fbx')
task.destination_path = D
task.destination_name = 'SM_ExtMag_Universal'
task.options = opt
task.automated = True
task.replace_existing = True
task.save = False
A.import_asset_tasks([task])

mesh = u.load_asset(D + '/SM_ExtMag_Universal')
if not mesh:
    raise RuntimeError('ExtMag import failed')
slots = mesh.get_editor_property('static_materials')
names = [str(s.material_slot_name) for s in slots]
binding = {'M_ExtMag_Polymer': mat_poly, 'M_ExtMag_Metal': mat_metal}
changed = False
for i, slot in enumerate(slots):
    key = str(slot.material_slot_name)
    if key in binding and slot.material_interface != binding[key]:
        slot.material_interface = binding[key]
        slots[i] = slot
        changed = True
if changed:
    mesh.set_editor_property('static_materials', slots)
u.EditorAssetLibrary.save_loaded_asset(mesh, False)

bounds = mesh.get_bounds()
verts = u.EditorStaticMeshLibrary.get_number_verts(mesh, 0)
report['mesh'] = mesh.get_path_name()
report['slot_names'] = names
report['vertices'] = verts
report['bounds'] = {'origin': [round(bounds.origin.x, 2), round(bounds.origin.y, 2), round(bounds.origin.z, 2)],
                    'box_extent': [round(bounds.box_extent.x, 2), round(bounds.box_extent.y, 2), round(bounds.box_extent.z, 2)]}
(O / 'import_receipt.json').write_text(json.dumps(report, indent=2, default=str))
u.log('EXTMAG_IMPORT_DONE ' + json.dumps(report, default=str))
