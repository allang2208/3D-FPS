"""Import the repaired AKM-only attachment at its existing shared runtime path."""
import json
from pathlib import Path
import unreal as u

OUT = Path(__file__).resolve().parent
DEST = '/Game/Weapons/AKMIntegration/SovietFab/GripErgonomic'
NAME = 'SM_AKM_angled'
steel = u.load_asset('/Game/Weapons/AKMIntegration/SovietFab/ArmSupport/M_AKM_Soviet_MountSteel')
polymer = u.load_asset('/Game/Weapons/M4InfimaV3/Grip_Default_001')
if not steel or not polymer:
    raise RuntimeError('Existing AKM metal or grip polymer material is unavailable')
opt = u.FbxImportUI()
opt.automated_import_should_detect_type = False
opt.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
opt.import_as_skeletal = False
opt.import_materials = False
opt.import_textures = False
opt.import_animations = False
data = opt.static_mesh_import_data
data.combine_meshes = True
data.auto_generate_collision = False
data.generate_lightmap_u_vs = False
data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
task = u.AssetImportTask()
task.filename = str(OUT / (NAME + '.fbx'))
task.destination_path = DEST
task.destination_name = NAME
task.options = opt
task.automated = True
task.replace_existing = True
task.save = True
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
mesh = u.load_asset(DEST + '/' + NAME)
if not task.imported_object_paths or not mesh:
    raise RuntimeError('AKM Resonance II mesh import did not produce an asset')
slots = mesh.static_materials
for i, slot in enumerate(slots):
    slot.material_interface = polymer if 'Grip' in str(slot.material_slot_name) and 'Steel' not in str(slot.material_slot_name) else steel
    slots[i] = slot
mesh.set_editor_property('static_materials', slots)
if not u.EditorAssetLibrary.save_loaded_asset(mesh, False):
    raise RuntimeError('AKM Resonance II asset could not be saved')
(OUT / 'import_receipt.json').write_text(json.dumps({
    'asset': mesh.get_path_name(), 'source': task.filename,
    'materials': {str(s.material_slot_name): s.material_interface.get_path_name() for s in slots},
    'runtime_tested': False, 'rendered': False,
}, indent=2), encoding='utf-8')
u.log('AKM_RESONANCE_IMPORTED ' + mesh.get_path_name())
