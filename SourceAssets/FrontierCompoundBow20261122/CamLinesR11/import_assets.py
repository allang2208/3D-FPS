"""Save the repaired visual assemblies with the shipping skeleton and material bindings."""
import json
import os
from pathlib import Path
import unreal as ue

source = Path(__file__).resolve().parent
batch = Path(os.environ["FRONTIER_BATCH"])
root = "/Game/Weapons/FrontierCompoundBow"
skeleton = ue.load_asset(root + "/RigContactR2/SK_Frontier_Assembly_Skeleton")
tools = ue.AssetToolsHelpers.get_asset_tools()
skins = ue.get_editor_subsystem(ue.SkeletalMeshEditorSubsystem)
if not skeleton or not skins:
    raise RuntimeError("Frontier skeleton or skeletal mesh subsystem unavailable")
ue.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
meshes = json.loads((batch / "meshes.json").read_text(encoding="utf-8"))
published = {}
for name, recipe in meshes.items():
    is_factory = name == "SK_Frontier_Assembly"
    old_folder = "RigContactR2" if is_factory else "EclipseFrameR1" if name == "SK_Frontier_Eclipse" else "FrameVariantsR1"
    original = ue.load_asset(f"{root}/{old_folder}/{name}")
    bindings = {str(slot.material_slot_name):slot.material_interface for slot in original.materials}
    original_lods = skins.get_lod_count(original)
    if original.skeleton != skeleton or not all(bindings.values()):
        raise RuntimeError("Incomplete source mesh: " + name)
    options = ue.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = ue.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_as_skeletal = True
    options.import_mesh = True
    options.import_materials = False
    options.import_textures = False
    options.import_animations = False
    options.create_physics_asset = False
    options.skeleton = skeleton
    data = options.skeletal_mesh_import_data
    data.normal_import_method = ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    data.set_editor_property("update_skeleton_reference_pose", False)
    data.set_editor_property("use_t0_as_ref_pose", False)
    # Preserve the base item path embedded in existing inventory and warehouse saves.
    folder = f"{root}/RigContactR2" if is_factory else f"{root}/CamLinesR11"
    task = ue.AssetImportTask()
    task.filename = str(source / "Export" / (name + ".fbx"))
    task.destination_name = name
    task.destination_path = folder
    task.automated = True
    task.replace_existing = True
    task.replace_existing_settings = True
    task.options = options
    tools.import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError("FBX import did not produce " + name)
    mesh = ue.load_asset(folder + "/" + name)
    if mesh.skeleton != skeleton:
        raise RuntimeError("Skeleton changed for " + name)
    slots = list(mesh.materials)
    if [str(slot.material_slot_name) for slot in slots] != list(bindings):
        raise RuntimeError("Material slot order changed for " + name)
    for slot in slots:
        slot.material_interface = bindings[str(slot.material_slot_name)]
    mesh.materials = slots
    if original_lods > 1 and not skins.regenerate_lod(mesh, original_lods, True, False):
        raise RuntimeError("Could not rebuild LODs for " + name)
    if not ue.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()], False):
        raise RuntimeError("Could not save " + name)
    published[name] = {"asset":mesh.get_path_name(), "previous":f"{root}/{old_folder}/{name}.{name}",
        "skeleton":skeleton.get_path_name(), "lods":skins.get_lod_count(mesh), "materials":list(bindings)}
(batch / "imported.json").write_text(json.dumps(published, indent=2), encoding="utf-8")
