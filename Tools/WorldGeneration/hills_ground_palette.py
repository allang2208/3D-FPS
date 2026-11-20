"""Author the fixed hills' cosmetic underfoot palettes. The caller saves the DA."""
from pathlib import Path

import unreal as ue


PROJECT = Path(__file__).resolve().parents[2]
HILLS = "/Game/WorldGeneration/TemperateHills"
DEST = HILLS + "/GroundPalette"
NIAGARA_SCANS = "/Game/NiagaraExamples/StaticMesh/"
GROUND_PLANTS = "/Game/PN_FoliageCollection/Meshes/groundPlantMesh/"
SOURCE = PROJECT / "SourceAssets/HillsGroundPalette"
E = ue.EditorAssetLibrary
M = ue.MaterialEditingLibrary
REVISION_TAG = "HillsGroundPaletteVersion"
REVISION = "1"


def require_mesh(path):
    mesh = ue.load_asset(path)
    if not isinstance(mesh, ue.StaticMesh):
        raise RuntimeError("Missing ground palette mesh " + path)
    return mesh


def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError("Could not save " + asset.get_path_name())


def limestone(name):
    path = DEST + "/" + name
    mesh = require_mesh(path) if E.does_asset_exist(path) else import_stone(name)
    if E.get_metadata_tag(mesh, REVISION_TAG) == REVISION:
        return mesh
    return finish_stone(mesh)


def import_stone(name):
    options = ue.FbxImportUI()
    options.import_mesh = True
    options.import_materials = False
    options.import_textures = False
    options.mesh_type_to_import = ue.FBXImportType.FBXIT_STATIC_MESH
    settings = options.static_mesh_import_data
    settings.combine_meshes = True
    settings.auto_generate_collision = False
    settings.generate_lightmap_u_vs = False
    settings.normal_import_method = ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS

    task = ue.AssetImportTask()
    task.filename = str(SOURCE / (name + ".fbx"))
    task.destination_path = DEST
    task.destination_name = name
    task.options = options
    task.automated = True
    task.save = False
    ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return require_mesh(DEST + "/" + name)


def finish_stone(mesh):
    material = ue.load_asset(HILLS + "/WhiteCliffs/Materials/M_LimestoneSpoil")
    if not material or len(mesh.static_materials) != 1:
        raise RuntimeError("Missing limestone scan binding for " + mesh.get_name())
    mesh.set_material(0, material)
    mesh.set_editor_property("support_ray_tracing", False)
    nanite = mesh.get_editor_property("nanite_settings")
    nanite.enabled = False
    mesh.set_editor_property("nanite_settings", nanite)
    lods = ue.StaticMeshReductionOptions()
    lods.auto_compute_lod_screen_size = False
    levels = []
    for fraction, screen_size in ((1.0, 1.0), (0.45, 0.045), (0.18, 0.012)):
        level = ue.StaticMeshReductionSettings()
        level.percent_triangles = fraction
        level.screen_size = screen_size
        levels.append(level)
    lods.reduction_settings = levels
    editor = ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem) or ue.new_object(ue.StaticMeshEditorSubsystem)
    if editor.set_lods(mesh, lods) < 1:
        raise RuntimeError("Could not author stone LODs for " + mesh.get_name())
    E.set_metadata_tag(mesh, REVISION_TAG, REVISION)
    save(mesh)
    return mesh


def woodland_plant(source_name):
    # Every source is a distinct mesh with four imported LODs, and all use the
    # same leaf atlas. Preserve each source's UVs and material parameters.
    path = DEST + "/SM_" + source_name
    original = require_mesh(GROUND_PLANTS + source_name)
    mesh = require_mesh(path) if E.does_asset_exist(path) else E.duplicate_asset(original.get_path_name(), path)
    if E.get_metadata_tag(mesh, REVISION_TAG) == REVISION:
        return mesh
    for i, slot in enumerate(original.static_materials):
        source_mat = slot.material_interface
        mat_path = DEST + "/MI_" + source_mat.get_name()
        mat = (ue.load_asset(mat_path) if E.does_asset_exist(mat_path)
               else E.duplicate_asset(source_mat.get_path_name(), mat_path))
        parent = mat.get_editor_property("parent")
        scalars = set(map(str, M.get_scalar_parameter_names(parent)))
        for key, value in (("Brightness", 0.84), ("Saturation", 0.76), ("Subsurface Strengh", 0.5)):
            if key in scalars:
                M.set_material_instance_scalar_parameter_value(mat, key, value)
        switches = set(map(str, M.get_static_switch_parameter_names(parent)))
        # Retain the original leaf atlas and restrict bending to the primary
        # wind motion for these low, noninteractive plants.
        for level in (1, 2, 3):
            for key, enabled in ((f"Level {level} Bending", False), (f"Level {level} Wind", level == 1)):
                if key in switches:
                    M.set_material_instance_static_switch_parameter_value(mat, key, enabled)
        M.update_material_instance(mat)
        save(mat)
        mesh.set_material(i, mat)
    mesh.set_editor_property("support_ray_tracing", False)
    E.set_metadata_tag(mesh, REVISION_TAG, REVISION)
    save(mesh)
    return mesh


def build_ground_meshes():
    if "-run=pythonscript" in ue.SystemLibrary.get_command_line().lower():
        editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem) or ue.new_object(ue.UnrealEditorSubsystem)
        ue.SystemLibrary.execute_console_command(editor.get_editor_world(), "Editor.AsyncStaticMeshCompilation 0")
    E.make_directory(DEST)
    return {
        "river_pebbles": [require_mesh(NIAGARA_SCANS + "S_Rock_shopk")],
        "quarry_shore_chips": [limestone("SM_ShoreLimestoneFlat"), limestone("SM_ShoreLimestoneLong")],
        "rainforest_twigs": [require_mesh(NIAGARA_SCANS + "S_Tree_Debris_wjtuagls"),
                            require_mesh(NIAGARA_SCANS + "S_Wood_Debris_vb2mfeliw")],
        "rainforest_herbs": [woodland_plant(name) for name in ("ground_05_01", "ground_10_01", "ground_13_01")],
        "river_ground_cover": [woodland_plant("ground_09_01")],
    }


def assign_ground_palette(assets):
    """Append distinct variants without reordering the wet-pebble slot or resource rocks."""
    paths = {}
    for role, meshes in build_ground_meshes().items():
        current = list(assets.get_editor_property(role))
        existing = {item.get_path_name() for item in current}
        additions = [mesh for mesh in meshes if mesh.get_path_name() not in existing]
        if additions:
            assets.set_editor_property(role, current + additions)
        paths[role] = [mesh.get_path_name() for mesh in meshes]
    return paths
