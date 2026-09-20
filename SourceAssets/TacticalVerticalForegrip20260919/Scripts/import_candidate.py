"""Import this candidate into the current UE editor; no PIE, screenshots, or runtime swaps."""
import json
from pathlib import Path
import unreal as u

ROOT = Path("D:/FPS3D/FPSGAME/SourceAssets/TacticalVerticalForegrip20260919")
EXPORT = ROOT / "Export"
DEST = "/Game/Weapons/Candidates/TacticalVerticalForegrip20260919"
NAME = "SM_TacticalVerticalForegrip_Candidate"
assets = u.AssetToolsHelpers.get_asset_tools()
editor = u.EditorAssetLibrary
materials = u.MaterialEditingLibrary
receipt = {"status": "importing", "destination": DEST, "saved": {}, "tests_run": False,
           "runtime_references_changed": False}
receipt_path = ROOT / "import_receipt.json"

def record():
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")

def save(asset):
    result = bool(editor.save_loaded_asset(asset, False))
    receipt["saved"][asset.get_path_name()] = result
    record()
    if not result:
        raise RuntimeError("Saving failed: " + asset.get_path_name())

def import_file(file, name, options=None):
    # This task owns only its new candidate directory.
    if editor.does_asset_exist(DEST + "/" + name):
        raise RuntimeError("Candidate path already exists; inspect this task's receipt before rerunning: " + name)
    task = u.AssetImportTask()
    task.filename = str(file)
    task.destination_path = DEST
    task.destination_name = name
    task.options = options
    task.automated = True
    task.replace_existing = False
    task.save = False
    assets.import_asset_tasks([task])
    asset = u.load_asset(DEST + "/" + name)
    if asset is None:
        raise RuntimeError("Import failed: " + str(file))
    return asset

record()
textures = {}
for key in ["BaseColor", "MetalRough", "Normal"]:
    file = EXPORT / "Textures" / ("T_TacticalVerticalForegrip_" + key + ".png")
    if not file.exists():
        raise RuntimeError("Missing authored texture: " + str(file))
    tex = import_file(file, "T_TacticalVerticalForegrip_" + key)
    if key == "MetalRough":
        tex.set_editor_property("srgb", False)
        tex.set_editor_property("compression_settings", u.TextureCompressionSettings.TC_MASKS)
    elif key == "Normal":
        tex.set_editor_property("srgb", False)
        tex.set_editor_property("compression_settings", u.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property("flip_green_channel", True)  # Blender tangent normal -> UE DirectX convention.
    save(tex)
    textures[key] = tex

mat_name = "M_TacticalVerticalForegrip_Candidate"
if editor.does_asset_exist(DEST + "/" + mat_name):
    raise RuntimeError("Candidate material already exists; do not rebuild a referenced material graph.")
mat = assets.create_asset(mat_name, DEST, u.Material, u.MaterialFactoryNew())
if mat is None:
    raise RuntimeError("Could not create candidate material.")

def connect(node, output, prop):
    if not materials.connect_material_property(node, output, prop):
        raise RuntimeError("Material connection failed: " + str(prop))

for index, key in enumerate(["BaseColor", "MetalRough", "Normal"]):
    node = materials.create_material_expression(mat, u.MaterialExpressionTextureSample, -500, index * 220)
    node.set_editor_property("texture", textures[key])
    if key == "BaseColor":
        connect(node, "RGB", u.MaterialProperty.MP_BASE_COLOR)
    elif key == "MetalRough":
        node.set_editor_property("sampler_type", u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        connect(node, "G", u.MaterialProperty.MP_ROUGHNESS)
        connect(node, "B", u.MaterialProperty.MP_METALLIC)
    else:
        node.set_editor_property("sampler_type", u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        connect(node, "RGB", u.MaterialProperty.MP_NORMAL)
materials.recompile_material(mat)
save(mat)
options = u.FbxImportUI()
options.automated_import_should_detect_type = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
options.import_as_skeletal = False
options.import_materials = False
options.import_textures = False
options.import_animations = False
data = options.static_mesh_import_data
data.combine_meshes = True
data.auto_generate_collision = False
data.generate_lightmap_u_vs = False
data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
mesh = import_file(EXPORT / (NAME + ".fbx"), NAME, options)
for slot in range(len(mesh.static_materials)):
    mesh.set_material(slot, mat)
save(mesh)
bounds = mesh.get_bounds()
receipt.update(status="imported_saved_not_tested", mesh=mesh.get_path_name(),
               material=mat.get_path_name(), material_slots=len(mesh.static_materials),
               bounds_extent_cm=[bounds.box_extent.x, bounds.box_extent.y, bounds.box_extent.z],
               bounds_origin_cm=[bounds.origin.x, bounds.origin.y, bounds.origin.z],
               textures={key: tex.get_path_name() for key, tex in textures.items()})
record()
u.log("TACTICAL_VERTICAL_FOREGRIP_IMPORTED " + json.dumps(receipt))
