"""Re-import the rebuilt ASH-12 mesh and clips into the RUNNING editor.

The commandlet channel cannot save while the editor holds the assets, so this
runs inside the editor over remote execution (Tools/AssetPipeline/
ue_python_exec.py). Mirrors import_ue.py's options exactly: mesh without
materials, 120 Hz clips, BC_M4Viewmodel bone compression, existing material
bindings preserved slot-by-slot from the live mesh.
"""
import unreal as u

O = r"D:\FPS3D\FPSGAME\SourceAssets\ASH1220260917"
D = "/Game/Weapons/ASH12/Integrated20260917"
COMPRESSION = "/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel"
CLIPS = ["idle", "aim", "fire", "aim_fire", "reload", "reload_empty", "equip_charge"]

tools = u.AssetToolsHelpers.get_asset_tools()
mesh = u.load_asset(D + "/SK_ASH12_Manny")
if not mesh:
    raise RuntimeError("live mesh not found; import the base asset first")
bindings = {str(slot.material_slot_name): slot.material_interface for slot in mesh.materials}

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
data.set_editor_property("update_skeleton_reference_pose", False)
data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
data.normal_generation_method = u.FBXNormalGenerationMethod.MIKK_T_SPACE
task = u.AssetImportTask()
task.filename = O + r"\SK_ASH12_Manny.fbx"
task.destination_path = D
task.destination_name = "SK_ASH12_Manny"
task.options = options
task.automated = True
task.replace_existing = True
task.save = False
tools.import_asset_tasks([task])
mesh = u.load_asset(D + "/SK_ASH12_Manny")
if not mesh:
    raise RuntimeError("mesh re-import failed")

slots = mesh.materials
for i, slot in enumerate(slots):
    name = str(slot.material_slot_name)
    slot.material_interface = bindings.get(name, slot.material_interface)
    slots[i] = slot
mesh.set_editor_property("materials", slots)
try:
    mesh.set_editor_property("bone_compression_settings", u.load_asset(COMPRESSION))
except Exception as error:  # noqa: BLE001
    u.log_warning("ASH12_BONE_COMPRESSION skipped: %s" % error)
if not u.EditorAssetLibrary.save_loaded_asset(mesh, False):
    raise RuntimeError("mesh save failed")
u.log("ASH12_LIVE_MESH slots=%s" % [str(s.material_slot_name) for s in slots])

for kind in CLIPS:
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    options.import_mesh = False
    options.import_animations = True
    options.import_materials = False
    options.import_textures = False
    options.skeleton = mesh.skeleton
    options.anim_sequence_import_data.set_editor_property("use_default_sample_rate", False)
    options.anim_sequence_import_data.set_editor_property("custom_sample_rate", 120)
    task = u.AssetImportTask()
    task.filename = O + ("\\A_ASH12_%s.fbx" % kind)
    task.destination_path = D + "/Animations"
    task.destination_name = "A_ASH12_" + kind
    task.options = options
    task.automated = True
    task.replace_existing = True
    task.save = False
    tools.import_asset_tasks([task])
    clip = u.load_asset(D + "/Animations/A_ASH12_" + kind)
    if not clip:
        raise RuntimeError("clip import failed: " + kind)
    clip.set_editor_property("bone_compression_settings", u.load_asset(COMPRESSION))
    if not u.EditorAssetLibrary.save_loaded_asset(clip, False):
        raise RuntimeError("clip save failed: " + kind)
    u.log("ASH12_LIVE_CLIP %s %.3fs" % (kind, clip.get_play_length()))

u.log("ASH12_LIVE_IMPORT_COMPLETE")
