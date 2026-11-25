"""Reimport the keeper's dressed mesh without importing an animation or skeleton."""
import json
import os
import sys
from pathlib import Path

import unreal as u
sys.path.insert(0, str(Path(__file__).resolve().parent))
from keeper_workcloth import DEST, save_panels


def main():
    project = Path(__file__).resolve().parents[3]
    assembly = project / "SourceAssets/HillsVillageWindmill/MillKeeper/CharacterR1/Assembly"
    path = json.loads((assembly / "saved.json").read_text())["mesh"]
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError("The editor is in play. Preserve the current session.")
    package = path.split(".")[0]
    dirty = u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    if any(p.get_name() == package or p.get_name().startswith(DEST+"/") for p in dirty):
        raise RuntimeError("A keeper wardrobe package has unsaved edits.")
    mesh = u.load_asset(path)
    sk = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
    lods = sk.get_lod_count(mesh)
    slots = {str(s.material_slot_name): s.material_interface for s in mesh.materials}
    cloth = save_panels()
    slots.update(cloth)
    # A new cloth section changes the section order. Import the base asset with
    # its FBX slot table, rather than transferring a prior LOD's section map.
    opts=u.FbxImportUI()
    opts.automated_import_should_detect_type=False
    opts.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    opts.import_as_skeletal=True
    opts.import_mesh=True
    opts.skeleton=mesh.skeleton
    opts.import_materials=opts.import_textures=opts.import_animations=opts.create_physics_asset=False
    data=opts.skeletal_mesh_import_data
    data.reorder_material_to_fbx_order=True
    data.convert_scene=False
    data.convert_scene_unit=True
    data.set_editor_property("update_skeleton_reference_pose",False)
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task=u.AssetImportTask()
    task.filename=str(assembly/"SK_MillKeeper.fbx")
    task.destination_path=package.rsplit("/",1)[0]
    task.automated=task.replace_existing=task.replace_existing_settings=True
    task.factory=u.FbxFactory()
    task.options=opts
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh=next(obj for obj in task.get_objects() if isinstance(obj,u.SkeletalMesh) and obj.get_path_name()==path)
    materials = list(mesh.materials)
    for slot in materials:
        source_name=str(slot.get_editor_property("imported_material_slot_name"))
        slot.material_interface = slots[source_name] if source_name in cloth else slots[str(slot.material_slot_name)]
    if not set(cloth).issubset({str(s.get_editor_property("imported_material_slot_name")) for s in materials}):
        raise RuntimeError("The reimport did not register both tailored panels")
    mesh.materials = materials
    if not sk.regenerate_lod(mesh, lods, True, False):
        raise RuntimeError("Could not rebuild the keeper's LODs.")
    if not u.EditorAssetLibrary.save_loaded_asset(mesh, False):
        raise RuntimeError("Could not save the dressed keeper.")
    receipt = {"mesh": mesh.get_path_name(), "lods": lods, "skeleton": mesh.skeleton.get_path_name(),
               "robe_donor": "ChapelNun20261115/IdleBackReviewR2/InputsAfter/robe.json",
               "source_fbx": "SK_MillKeeper.fbx", "fabric_master": DEST+"/M_Keeper_Workcloth",
               "cloth_slots": {str(s.material_slot_name):s.material_interface.get_path_name()
                              for s in materials if str(s.material_slot_name) in cloth},
               "runtime_tested": False}
    receipt_path = Path(os.environ.get("KEEPER_IMPORT_RECEIPT", str(assembly/"outfit_workwear_r4.json")))
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print("Saved the keeper robe", mesh.get_path_name(), flush=True)


main()
