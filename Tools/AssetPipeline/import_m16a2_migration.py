"""Import only the M16A2 migration assets; does not alter live weapon data."""
import json
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / "SourceAssets/M16A2Migration20260919"
DEST = "/Game/Weapons/M16A2Migration"
ASSETS = u.AssetToolsHelpers.get_asset_tools()
LIB = u.EditorAssetLibrary
MAT = u.MaterialEditingLibrary


def import_file(filename, folder, name, options=None):
    task = u.AssetImportTask()
    task.filename = str(filename)
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    if options:
        task.options = options
        task.factory = u.FbxFactory()
    ASSETS.import_asset_tasks([task])
    asset = u.load_asset(folder + "/" + name)
    if not asset:
        raise RuntimeError("Import did not create " + folder + "/" + name)
    return asset


def fbx_options(skeletal=False):
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_SKELETAL_MESH if skeletal else u.FBXImportType.FBXIT_STATIC_MESH
    options.import_as_skeletal = skeletal
    options.import_mesh = True
    options.import_animations = False
    options.import_materials = False
    options.import_textures = False
    options.create_physics_asset = False
    data = options.skeletal_mesh_import_data if skeletal else options.static_mesh_import_data
    data.set_editor_property("convert_scene", False)
    data.set_editor_property("force_front_x_axis", False)
    data.set_editor_property("convert_scene_unit", True)
    data.set_editor_property("import_uniform_scale", 1.0)
    data.set_editor_property("normal_import_method", u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    if not skeletal:
        data.set_editor_property("combine_meshes", True)
        data.set_editor_property("auto_generate_collision", False)
        data.set_editor_property("generate_lightmap_u_vs", False)
    return options


textures = {}
for kind in ["BaseColor", "Metallic", "Roughness", "Normal", "AO"]:
    texture = import_file(CASE / "Textures" / f"m16a2_{kind}.png", DEST + "/Textures", "T_M16A2_" + kind)
    texture.set_editor_property("srgb", kind == "BaseColor")
    if kind == "Normal":
        texture.set_editor_property("compression_settings", u.TextureCompressionSettings.TC_NORMALMAP)
        texture.set_editor_property("flip_green_channel", True)
    elif kind != "BaseColor":
        texture.set_editor_property("compression_settings", u.TextureCompressionSettings.TC_GRAYSCALE)
    LIB.save_loaded_asset(texture, False)
    textures[kind] = texture

material_path = DEST + "/Materials/M_M16A2_PBR"
material = u.load_asset(material_path) if LIB.does_asset_exist(material_path) else ASSETS.create_asset("M_M16A2_PBR", DEST + "/Materials", u.Material, u.MaterialFactoryNew())
MAT.delete_all_material_expressions(material)
MAT.set_material_usage(material, u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
for index, (kind, property_name) in enumerate([
    ("BaseColor", u.MaterialProperty.MP_BASE_COLOR),
    ("Metallic", u.MaterialProperty.MP_METALLIC),
    ("Roughness", u.MaterialProperty.MP_ROUGHNESS),
    ("Normal", u.MaterialProperty.MP_NORMAL),
    ("AO", u.MaterialProperty.MP_AMBIENT_OCCLUSION),
]):
    node = MAT.create_material_expression(material, u.MaterialExpressionTextureSampleParameter2D, -500, index * 220)
    node.set_editor_property("parameter_name", kind)
    node.set_editor_property("texture", textures[kind])
    if kind == "Normal":
        node.set_editor_property("sampler_type", u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    elif kind != "BaseColor":
        node.set_editor_property("sampler_type", u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
    MAT.connect_material_property(node, "RGB" if kind in {"BaseColor", "Normal"} else "R", property_name)
MAT.recompile_material(material)
LIB.save_loaded_asset(material, False)

options = fbx_options(True)
mesh_path = DEST + "/SK_M16A2_Mechanical"
if LIB.does_asset_exist(mesh_path):
    options.skeleton = u.load_asset(mesh_path).skeleton
mesh = import_file(CASE / "Export/SK_M16A2_Mechanical.fbx", DEST, "SK_M16A2_Mechanical", options)
slots = mesh.get_editor_property("materials")
for index, slot in enumerate(slots):
    slot.material_interface = material
    slots[index] = slot
mesh.set_editor_property("materials", slots)
LIB.set_metadata_tag(mesh, "M16A2_MigrationScope", "Gun-only mechanical asset; no hands, animation or gameplay integration")
LIB.save_loaded_asset(mesh, False)

manifest = json.loads((CASE / "manifest.json").read_text(encoding="utf-8"))
static_assets = []
entries = [("Assembled", CASE / "Export/SM_M16A2_Assembled.fbx", DEST)]
entries += [(p["name"], CASE / "Export/Parts" / ("SM_M16A2_" + p["name"] + ".fbx"), DEST + "/Parts") for p in manifest["parts"]]
for label, filename, folder in entries:
    static = import_file(filename, folder, "SM_M16A2_" + label, fbx_options())
    for index in range(len(static.get_editor_property("static_materials"))):
        static.set_material(index, material)
    if label != "Assembled":
        record = next(p for p in manifest["parts"] if p["name"] == label)
        LIB.set_metadata_tag(static, "M16A2_AssemblyLocationCm", json.dumps(record["assembly_location_cm"]))
        LIB.set_metadata_tag(static, "M16A2_MechanicalBone", record["bone"])
    LIB.save_loaded_asset(static, False)
    static_assets.append(static.get_path_name())

LIB.save_directory(DEST, only_if_is_dirty=True, recursive=True)
(CASE / "import_result.json").write_text(json.dumps({
    "destination": DEST,
    "skeletal_mesh": mesh.get_path_name(),
    "skeleton": mesh.skeleton.get_path_name(),
    "static_meshes": static_assets,
    "material": material.get_path_name(),
    "textures": {k: v.get_path_name() for k, v in textures.items()},
    "testing": "No render, PIE, runtime, automated test or visual acceptance performed.",
}, indent=2), encoding="utf-8")
u.log("M16A2_IMPORT_COMPLETE: gun, skeleton, 13 parts, assembled static mesh and 5 PBR maps saved")
