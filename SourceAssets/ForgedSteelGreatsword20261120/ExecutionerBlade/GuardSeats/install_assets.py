"""Import the four blade-specific guards into an isolated Unreal authoring host."""
import json
import os
from pathlib import Path

import unreal as u


here = Path(__file__).resolve().parent
project = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()
host = Path(os.environ["FORGED_GUARD_AUTHOR_HOST"]).resolve()
if project != host or "-run=pythonscript" not in u.SystemLibrary.get_command_line().lower():
    raise RuntimeError("Run the background commandlet in the GuardAuthor host")

exports = json.loads((here / "exports.json").read_text(encoding="utf8"))
material = u.load_asset(exports["material"])
if not material:
    raise RuntimeError("Stage the original guard material and its textures before importing")
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
u.SystemLibrary.execute_console_command(world, "Interchange.FeatureFlags.Import.FBX 0")
options = u.FbxImportUI()
options.automated_import_should_detect_type = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
options.import_mesh = True
options.import_as_skeletal = False
options.import_materials = False
options.import_textures = False
options.import_animations = False
settings = options.static_mesh_import_data
settings.combine_meshes = True
settings.auto_generate_collision = False
settings.generate_lightmap_u_vs = False
settings.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
settings.normal_generation_method = u.FBXNormalGenerationMethod.MIKK_T_SPACE
settings.build_nanite = True

assets = {}
for option, row in exports["guards"].items():
    task = u.AssetImportTask()
    task.filename = str(here / row["fbx"])
    task.destination_path = exports["destination"]
    task.destination_name = row["mesh"]
    task.options = options
    task.automated = True
    task.replace_existing = True
    task.replace_existing_settings = True
    task.save = False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if row["object_path"] not in list(task.imported_object_paths):
        raise RuntimeError(f"Missing mesh on import: {option} {task.imported_object_paths}")
    mesh = u.load_asset(row["object_path"])
    if [str(slot.material_slot_name) for slot in mesh.static_materials] != [exports["material_slot"]]:
        raise RuntimeError("Guard material slot changed: " + option)
    mesh.set_material(0, material)
    nanite = mesh.get_editor_property("nanite_settings")
    nanite.enabled = True
    nanite.explicit_tangents = True
    nanite.fallback_relative_error = 0
    mesh.set_editor_property("nanite_settings", nanite)
    if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()], False):
        raise RuntimeError("Could not save " + row["object_path"])
    package = mesh.get_outermost().get_name()
    file = project / "Content" / (package.removeprefix("/Game/") + ".uasset")
    if not file.is_file():
        raise RuntimeError("Missing saved mesh " + str(file))
    box = mesh.get_bounds()
    minimum, maximum = box.origin - box.box_extent, box.origin + box.box_extent
    assets[option] = {"mesh": mesh.get_path_name(), "material": mesh.get_material(0).get_path_name(),
                      "nanite": nanite.enabled, "explicit_tangents": nanite.explicit_tangents,
                      "bounds_cm": [minimum.to_tuple(), maximum.to_tuple()], "file": str(file)}
(project.parent / "imported.json").write_text(json.dumps(assets, indent=2) + "\n", encoding="utf8")
print("EXECUTIONER_GUARD_SEATS_SAVED")
