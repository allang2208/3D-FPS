"""Import the reviewed combined mesh into a new asset, retaining shared clips/materials."""
import unreal, json
from pathlib import Path

root = Path(r'D:/FPS3D/FPSGAME')
out = root / 'SourceAssets/ArmsRepair20260909/Integrated'
destination = '/Game/Weapons/AKMReplacement/HandsRepair'
path = destination + '/SK_AKM_HandsRepair'
reference = unreal.load_asset('/Game/Weapons/AKMReplacement/Rendering/SK_AKM_Replacement_Game')
skeleton = reference.get_editor_property('skeleton')
readback = '-HandsRepairReadback' in unreal.SystemLibrary.get_command_line()
if not readback:
    assert not unreal.EditorAssetLibrary.does_asset_exist(path), 'Do not overwrite an existing reviewed revision'
    options = unreal.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_as_skeletal = True
    options.import_mesh = True
    options.import_animations = False
    options.import_materials = False
    options.import_textures = False
    options.create_physics_asset = False
    options.skeleton = skeleton
    options.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose', False)
    options.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose', False)
    task = unreal.AssetImportTask()
    task.filename = str(out / 'SK_AKM_HandsRepair.fbx')
    task.destination_path = destination
    task.automated = True
    task.replace_existing = False
    task.save = True
    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
mesh = unreal.load_asset(path)
assert isinstance(mesh, unreal.SkeletalMesh), path
assert mesh.get_editor_property('skeleton') == skeleton
slots = mesh.get_editor_property('materials')
reference_slots = reference.get_editor_property('materials')
materials = {str(s.get_editor_property('material_slot_name')).split('.')[0]: s.get_editor_property('material_interface') for s in reference_slots}
if not readback:
    for i, slot in enumerate(slots):
        name = str(slot.get_editor_property('material_slot_name')).split('.')[0]
        assert name in materials, ('Unknown material slot', name, list(materials))
        slot.set_editor_property('material_interface', materials[name])
        slots[i] = slot
    mesh.set_editor_property('materials', slots)
    assert unreal.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False)
assert len(slots) == len(reference_slots) == 7
for slot in slots:
    material = slot.get_editor_property('material_interface')
    assert material and unreal.MaterialEditingLibrary.has_material_usage(material, unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)
report = {'mesh': mesh.get_path_name(), 'shared_skeleton': skeleton.get_path_name(),
          'materials': [s.get_editor_property('material_interface').get_path_name() for s in slots],
          'independent_readback': readback, 'passed': True}
(out / ('ue_readback.json' if readback else 'ue_import.json')).write_text(json.dumps(report, indent=2), encoding='utf8')
unreal.log('HANDS_REPAIR_UE_OK ' + json.dumps(report))
