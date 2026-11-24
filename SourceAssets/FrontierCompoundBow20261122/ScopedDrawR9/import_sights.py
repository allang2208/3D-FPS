"""Save the two scoped meshes with the existing Frontier finish and optical glass."""
from pathlib import Path
import json
import unreal as u

source = Path(__file__).resolve().parent
manifest = json.loads((source / "parts.json").read_text(encoding="utf-8"))
destination = "/Game/Weapons/FrontierCompoundBow/ScopedDrawR9"
surface = "/Game/Weapons/FrontierCompoundBow/CommonModsR1/M_FrontierMods_Surface"
glass = "/Game/Weapons/DarkBow20260925/SingleLensOptics20260927/M_BowOptic_Glass"
assets = u.AssetToolsHelpers.get_asset_tools()
meshes = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
u.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
for spec in manifest["options"].values():
    name = spec["mesh"]
    opts = u.FbxImportUI()
    opts.automated_import_should_detect_type = False
    opts.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    opts.import_mesh = True
    opts.import_materials = opts.import_textures = opts.import_animations = False
    data = opts.static_mesh_import_data
    data.combine_meshes = True
    data.auto_generate_collision = data.generate_lightmap_u_vs = False
    data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task = u.AssetImportTask()
    task.filename = str(source / "Export" / (name + ".fbx"))
    task.destination_path = destination
    task.destination_name = name
    task.automated = task.replace_existing = True
    task.options = opts
    assets.import_asset_tasks([task])
    mesh = u.load_asset(destination + "/" + name)
    if not mesh or mesh.get_path_name() not in task.imported_object_paths:
        raise RuntimeError("Could not import " + name)
    materials = {path.split("/")[-1]: u.load_asset(path)
                 for path in (surface, glass + str(spec["power"]) + "x")}
    slots = list(mesh.static_materials)
    for slot in slots:
        mat = materials[str(slot.material_slot_name)]
        if not mat:
            raise RuntimeError("Missing optical material " + str(slot.material_slot_name))
        slot.material_interface = mat
    mesh.static_materials = slots
    options = u.StaticMeshReductionOptions()
    options.auto_compute_lod_screen_size = True
    levels = []
    for ratio in (1., .55, .24):
        level = u.StaticMeshReductionSettings()
        level.percent_triangles = ratio
        levels.append(level)
    options.reduction_settings = levels
    meshes.set_lods(mesh, options)
    if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()], False):
        raise RuntimeError("Could not save " + name)
    u.log("Saved scoped Frontier mount " + mesh.get_path_name())
