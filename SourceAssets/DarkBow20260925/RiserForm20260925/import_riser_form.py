"""Import the structured riser as a new asset and point bows.json at it."""
from __future__ import annotations

import json
from pathlib import Path

import unreal as u

HERE = Path(__file__).resolve().parent
DEST = "/Game/Weapons/DarkBow20260925/RiserForm20260925"
NAME = "SM_DarkBow_RiserForm"
FBX = HERE / "Export" / (NAME + ".fbx")
BOWS = Path(u.Paths.project_dir()) / "Content" / "ColdSteelData" / "bows.json"
WOOD = {
    "Body": "/Game/Weapons/DarkBow20260925/ArmsV2/Materials/MI_BowWood_Body",
    "Limb": "/Game/Weapons/DarkBow20260925/ArmsV2/Materials/MI_BowWood_Limb",
    "Inlay": "/Game/Weapons/DarkBow20260925/ArmsV2/Materials/MI_BowWood_Inlay",
}
INDEX_FALLBACK = {0: WOOD["Body"], 1: WOOD["Limb"], 2: WOOD["Inlay"]}
EAL = u.EditorAssetLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
EAL.make_directory(DEST)


def save_asset(asset):
    asset.modify()
    pkg = asset.get_package()
    if not u.EditorLoadingAndSavingUtils.save_packages([pkg], False):
        if not EAL.save_loaded_asset(asset, False):
            raise RuntimeError("save failed " + asset.get_path_name())
    return asset.get_path_name()


def bounds_cm(mesh):
    b = mesh.get_bounds()
    return {
        "extent": [round(b.box_extent.x, 3), round(b.box_extent.y, 3), round(b.box_extent.z, 3)],
        "origin": [round(b.origin.x, 3), round(b.origin.y, 3), round(b.origin.z, 3)],
        "size": [round(b.box_extent.x * 2, 3), round(b.box_extent.y * 2, 3), round(b.box_extent.z * 2, 3)],
    }


def copy_to(mesh, dm):
    options = u.GeometryScriptCopyMeshToAssetOptions()
    options.set_editor_property("enable_recompute_normals", False)
    options.set_editor_property("enable_recompute_tangents", True)
    options.set_editor_property("replace_materials", False)
    _, outcome = u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(
        dm, mesh, options, u.GeometryScriptMeshWriteLOD()
    )
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError("write mesh failed")


def read_dm(mesh):
    dm, outcome = u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(
        mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD()
    )
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError("read mesh failed")
    return dm


u.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
path = DEST + "/" + NAME
if EAL.does_asset_exist(path):
    mesh = u.load_asset(path)
    if mesh is None:
        raise RuntimeError("existing path would not load " + path)
else:
    opt = u.FbxImportUI()
    opt.automated_import_should_detect_type = False
    opt.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_materials = False
    opt.import_textures = False
    opt.import_mesh = True
    opt.import_animations = False
    opt.static_mesh_import_data.combine_meshes = True
    opt.static_mesh_import_data.auto_generate_collision = False
    opt.static_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    try:
        opt.static_mesh_import_data.import_uniform_scale = 1.0
        opt.static_mesh_import_data.build_nanite = False
    except Exception:
        pass
    task = u.AssetImportTask()
    task.filename = str(FBX)
    task.destination_path = DEST
    task.destination_name = NAME
    task.automated = True
    task.replace_existing = False
    task.options = opt
    task.save = False
    TOOLS.import_asset_tasks([task])
    mesh = u.load_asset(path)
    if mesh is None:
        raise RuntimeError("import did not produce " + path)

fixes = []
info = bounds_cm(mesh)
if max(info["size"]) < 20:
    dm = read_dm(mesh)
    u.GeometryScript_MeshTransforms.scale_mesh(dm, u.Vector(100, 100, 100), u.Vector(0, 0, 0), True)
    copy_to(mesh, dm)
    info = bounds_cm(mesh)
    fixes.append("scale_100")
if info["origin"][1] > 0:
    dm = read_dm(mesh)
    u.GeometryScript_MeshTransforms.scale_mesh(dm, u.Vector(1, -1, 1), u.Vector(0, 0, 0), True)
    copy_to(mesh, dm)
    info = bounds_cm(mesh)
    fixes.append("flip_y")
if info["size"][2] < 136 or info["size"][2] > 146:
    if 130 <= max(info["size"]) <= 150:
        pass
    else:
        raise RuntimeError("length axis wrong: " + str(info))
if info["size"][1] < 4.2 or info["size"][1] > 8.5:
    raise RuntimeError("thickness not the structured grip: " + str(info))
if max(info["size"]) < 130 or max(info["size"]) > 160:
    raise RuntimeError("imported size not a 140cm bow: " + str(info))

slots = list(mesh.static_materials)
for i, slot in enumerate(slots):
    name = str(slot.material_slot_name)
    mat_path = WOOD.get(name, INDEX_FALLBACK.get(i))
    material = u.load_asset(mat_path) if mat_path else None
    if material is None:
        raise RuntimeError("wood material missing for " + name)
    mesh.set_material(i, material)
    slot.set_editor_property("material_interface", material)
    slots[i] = slot
mesh.set_editor_property("static_materials", slots)
save_asset(mesh)

readback = []
for i, slot in enumerate(list(mesh.static_materials)):
    material = slot.material_interface
    readback.append(
        {
            "index": i,
            "name": str(slot.material_slot_name),
            "material": material.get_path_name() if material else None,
        }
    )
    wanted = WOOD.get(str(slot.material_slot_name), INDEX_FALLBACK.get(i))
    if not material or material.get_path_name().split(".")[-1] not in wanted:
        raise RuntimeError("slot bind failed " + str(readback[-1]))

bows = json.loads(BOWS.read_text(encoding="utf-8"))
bows["bow_dark"]["bow_part_riser_mesh"] = mesh.get_path_name()
bows["bow_dark"]["bow_presentation_revision"] = 12
BOWS.write_text(json.dumps(bows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

receipt = {
    "mesh": mesh.get_path_name(),
    "bounds_cm": bounds_cm(mesh),
    "fixes": fixes,
    "slots": readback,
    "bows_riser": bows["bow_dark"]["bow_part_riser_mesh"],
    "presentation_revision": 12,
    "replaced": "/Game/Weapons/DarkBow20260925/RiserDetail20260925/SM_DarkBow_RiserDetail.SM_DarkBow_RiserDetail",
    "runtime_tested": False,
}
(HERE / "import_receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print("BOW_RISER_FORM_IMPORTED", json.dumps(receipt), flush=True)
