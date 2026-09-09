import json
from pathlib import Path

import unreal

SOURCE_DIR = Path(r"D:\FPS3D\FPSGAME\SourceAssets\AKM")
DESTINATION = "/Game/Weapons/AKM"
REPORT = SOURCE_DIR / "akm_unreal_import_report.json"
CLIPS = ("idle", "aim", "fire", "aim_fire", "reload", "reload_empty", "draw", "holster", "inspect")


def run_task(filename, destination, options):
    task = unreal.AssetImportTask()
    task.filename = str(filename)
    task.destination_path = destination
    task.automated = True
    task.replace_existing = True
    task.save = True
    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return [str(path) for path in task.imported_object_paths]


mesh_options = unreal.FbxImportUI()
mesh_options.automated_import_should_detect_type = False
mesh_options.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
mesh_options.import_as_skeletal = True
mesh_options.import_mesh = True
mesh_options.import_animations = False
mesh_options.import_materials = True
mesh_options.import_textures = True
mesh_options.create_physics_asset = False

mesh_paths = run_task(SOURCE_DIR / "SK_AKM_Viewmodel.fbx", DESTINATION, mesh_options)
mesh_asset = unreal.load_asset(f"{DESTINATION}/SK_AKM_Viewmodel")
if not mesh_asset:
    candidates = [unreal.load_asset(path) for path in mesh_paths]
    mesh_asset = next((asset for asset in candidates if isinstance(asset, unreal.SkeletalMesh)), None)
if not mesh_asset:
    raise RuntimeError(f"AKM skeletal mesh import failed: {mesh_paths}")

skeleton = mesh_asset.get_editor_property("skeleton")
if not skeleton:
    raise RuntimeError("Imported AKM skeletal mesh has no skeleton")

animation_paths = {}
for clip in CLIPS:
    animation_options = unreal.FbxImportUI()
    animation_options.automated_import_should_detect_type = False
    animation_options.mesh_type_to_import = unreal.FBXImportType.FBXIT_ANIMATION
    animation_options.import_as_skeletal = False
    animation_options.import_mesh = False
    animation_options.import_animations = True
    animation_options.import_materials = False
    animation_options.import_textures = False
    animation_options.skeleton = skeleton
    animation_paths[clip] = run_task(SOURCE_DIR / f"A_AKM_{clip}.fbx", DESTINATION, animation_options)

unreal.EditorAssetLibrary.save_directory(DESTINATION, only_if_is_dirty=False, recursive=True)

assets = [str(path) for path in unreal.EditorAssetLibrary.list_assets(DESTINATION, recursive=True, include_folder=False)]
report = {
    "destination": DESTINATION,
    "mesh_paths": mesh_paths,
    "mesh_asset": mesh_asset.get_path_name(),
    "skeleton": skeleton.get_path_name(),
    "animations": animation_paths,
    "assets": assets,
}
REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
unreal.log(json.dumps(report, indent=2))
