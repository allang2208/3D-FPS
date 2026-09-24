"""Replace Highland ricasso meshes. Delete first so import settings are not reused."""
import json
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
ROOT = "/Game/Weapons/HighlandClaymore20260922"
SURFACE = ROOT + "/Materials/M_HighlandClaymoreSurface.M_HighlandClaymoreSurface"
JOBS = [(name, ROOT + "/Meshes") for name in [
    "SM_Highland_Blade_factory", "SM_Highland_Blade_extended_edge", "SM_Highland_Blade_heavy_spine",
    "SM_Highland_Blade_feather_edge", "SM_Highland_Guard_factory", "SM_Highland_Guard_bastion_guard",
    "SM_Highland_Guard_riposte_guard", "SM_Highland_Guard_light_guard",
]] + [
    ("SM_Highland_Blade_Broadblade_ThickV2", ROOT + "/BroadbladeThicknessV2_20260922"),
    ("SM_Highland_Guard_Cloven", ROOT + "/ClovenGuard"),
]
assets = u.AssetToolsHelpers.get_asset_tools()
library = u.EditorAssetLibrary
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world() is not None:
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
    print("PIE_END_REQUESTED")
    raise SystemExit(0)
world = editor.get_editor_world() if editor else None
if world:
    u.SystemLibrary.execute_console_command(world, "Interchange.FeatureFlags.Import.FBX 0")
static = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
surface = u.load_asset(SURFACE)
if not surface:
    raise RuntimeError("Missing Highland surface material")
receipt = []
for name, folder in JOBS:
    fbx = P / "Export" / (name + ".fbx")
    if not fbx.exists():
        raise RuntimeError("Missing FBX " + str(fbx))
    path = folder + "/" + name
    previous = []
    old = u.load_asset(path)
    if old:
        previous = [old.get_material(i) for i in range(len(old.static_materials))]
        if not library.delete_asset(path):
            raise RuntimeError("Could not delete " + path)
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    options.import_as_skeletal = False
    options.import_mesh = True
    options.import_materials = False
    options.import_textures = False
    options.import_animations = False
    config = options.static_mesh_import_data
    config.combine_meshes = True
    config.auto_generate_collision = False
    config.generate_lightmap_u_vs = False
    config.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    config.vertex_color_import_option = u.VertexColorImportOption.REPLACE
    task = u.AssetImportTask()
    task.filename = str(fbx)
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = False
    task.save = False
    task.options = options
    assets.import_asset_tasks([task])
    mesh = u.load_asset(path)
    if not mesh:
        raise RuntimeError("Import failed " + name)
    slots = len(mesh.static_materials)
    for index in range(slots):
        mesh.set_material(index, previous[index] if index < len(previous) and previous[index] else surface)
    settings = static.get_lod_build_settings(mesh, 0)
    settings.recompute_normals = False
    settings.recompute_tangents = False
    settings.use_full_precision_u_vs = True
    static.set_lod_build_settings(mesh, 0, settings)
    if not library.save_loaded_asset(mesh, False):
        raise RuntimeError("Save failed " + path)
    bounds = mesh.get_bounding_box()
    size = bounds.max - bounds.min
    if name.startswith("SM_Highland_Blade") and not (80.0 <= size.z <= 110.0):
        raise RuntimeError(name + " length cm " + str(size.z))
    receipt.append({"asset": mesh.get_path_name(), "slots": slots, "size_cm": [round(size.x, 2), round(size.y, 2), round(size.z, 2)], "saved": True})
out = P / "import_receipt.json"
out.write_text(json.dumps({"assets": receipt, "tested": False}, indent=2), encoding="utf-8")
print("RICASSO_IMPORT_COMPLETE " + str(len(receipt)))
