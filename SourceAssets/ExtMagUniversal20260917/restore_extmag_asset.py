import unreal as u
from pathlib import Path
O = Path(__file__).parent
A = u.AssetToolsHelpers.get_asset_tools()
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
opt.static_mesh_import_data.convert_scene_unit = False
opt.static_mesh_import_data.import_uniform_scale = 1.0
opt.static_mesh_import_data.combine_meshes = True
task = u.AssetImportTask()
task.filename = str(O / 'FBX' / 'SM_ExtMag_Universal.fbx')
task.destination_path = '/Game/Weapons/ExtMagUniversal20260917'
task.destination_name = 'SM_ExtMag_Universal'
task.options = opt
task.automated = True
task.replace_existing = True
task.save = False
A.import_asset_tasks([task])
mesh = u.load_asset('/Game/Weapons/ExtMagUniversal20260917/SM_ExtMag_Universal')
if not mesh: raise RuntimeError('restore import failed')
poly = u.load_asset('/Game/Weapons/ExtMagUniversal20260917/M_ExtMag_Polymer')
metal = u.load_asset('/Game/Weapons/ExtMagUniversal20260917/M_ExtMag_Metal')
slots = mesh.get_editor_property('static_materials')
for i, s in enumerate(slots):
    s.material_interface = metal if str(s.material_slot_name) == 'M_ExtMag_Metal' else poly
    slots[i] = s
mesh.set_editor_property('static_materials', slots)
ok = u.EditorAssetLibrary.save_loaded_asset(mesh, False)
b = mesh.get_bounds()
u.log('EXTMAG_RESTORED saved=%s slots=%s extent=(%.2f,%.2f,%.2f)' % (ok,
      [str(s.material_slot_name) for s in mesh.get_editor_property('static_materials')],
      b.box_extent.x, b.box_extent.y, b.box_extent.z))
