"""Install the Sketchfab Hospital Bed (loxfear, CC-BY-4.0) into /Game/Props.

Order: textures -> static mesh -> 3 materials (gltf metallicRoughness split:
R=AO, G=Roughness, B=Metallic, factors multiplied) -> slot write-back -> save.
Run via: UnrealEditor-Cmd.exe FPSGAME.uproject -run=pythonscript -script=install.py
"""
import hashlib
import json
import os
from pathlib import Path
import unreal as u

O = Path(__file__).resolve().parent          # SourceAssets/HospitalBed20260929
ROOT = "/Game/Props/HospitalBed20260929"
TEX = ROOT + "/Textures"
MAT_DIR = ROOT + "/Materials"
MESH = ROOT + "/SM_HospitalBed"
FBX = O / "Exports/SM_HospitalBed.fbx"
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
MEL = u.MaterialEditingLibrary

# glTF factors (read from scene.gltf at authoring time, 2026-09-29)
FACT = {
    "pillow": {"color": (0.27592356247286554, 0.27592356247286554, 0.27592356247286554),
               "metallic": 0.0, "roughness": 0.42},
    "lagen": {"color": (0.17854420731707318, 0.17854420731707318, 0.17854420731707318),
              "metallic": 0.2943978658536585, "roughness": 0.42},
    "material": {"color": None, "metallic": 1.0, "roughness": 0.7617316941186485},
}

TEXTURES = [  # (file, asset name, sRGB, compression)
    ("lagen_baseColor.png", "T_HospitalBed_LinenBaseColor", True, u.TextureCompressionSettings.TC_DEFAULT),
    ("lagen_metallicRoughness.png", "T_HospitalBed_LinenMR", False, u.TextureCompressionSettings.TC_MASKS),
    ("lagen_normal.png", "T_HospitalBed_LinenNormal", False, u.TextureCompressionSettings.TC_NORMALMAP),
    ("material_baseColor.png", "T_HospitalBed_FrameBaseColor", True, u.TextureCompressionSettings.TC_DEFAULT),
    ("material_metallicRoughness.png", "T_HospitalBed_FrameMR", False, u.TextureCompressionSettings.TC_MASKS),
]

receipt = {"mesh": MESH,
           "source": "Sketchfab f8c13a19e84343e7b644c19f7b9488d3 by loxfear",
           "license": "CC-BY-4.0, credit required: 'Hospital Bed' by loxfear (sketchfab.com/loxfear), licensed under CC-BY-4.0",
           "license_file": str(O / "license.txt")}

# --- 1. textures ---
tex_assets = {}
for fname, name, srgb, comp in TEXTURES:
    path = TEX + "/" + name
    if not E.does_asset_exist(path):
        task = u.AssetImportTask()
        task.filename = str(O / "textures" / fname)
        task.destination_path = TEX
        task.destination_name = name
        task.factory = u.TextureFactory()
        task.automated = True
        task.save = False
        A.import_asset_tasks([task])
        t = E.load_asset(path)
        if not t:
            raise RuntimeError("texture import failed: " + fname)
        t.set_editor_property("srgb", srgb)
        t.set_editor_property("compression_settings", comp)
        E.save_loaded_asset(t, False)
    tex_assets[name] = E.load_asset(path)
receipt["textures"] = sorted(tex_assets.keys())
print("TEXTURES_DONE", len(tex_assets), flush=True)

# --- 2. static mesh ---
u.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
if not E.does_asset_exist(MESH):
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    options.import_as_skeletal = False
    options.import_materials = False
    options.import_textures = False
    options.import_animations = False
    options.set_editor_property("reset_to_fbx_on_material_conflict", True)
    d = options.static_mesh_import_data
    d.combine_meshes = True
    d.auto_generate_collision = True
    d.generate_lightmap_u_vs = False
    d.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task = u.AssetImportTask()
    task.filename = str(FBX)
    task.destination_path = ROOT
    task.destination_name = "SM_HospitalBed"
    task.options = options
    task.factory = u.FbxFactory()
    task.automated = True
    task.replace_existing = False
    task.save = False
    A.import_asset_tasks([task])
mesh = E.load_asset(MESH)
if not mesh:
    raise RuntimeError("mesh import failed")
print("MESH_DONE slots:", [str(s.material_slot_name) for s in mesh.static_materials], flush=True)

# --- 3. materials ---
mat_names = {}


def make_material(name, build):
    path = MAT_DIR + "/" + name
    mat = E.load_asset(path) if E.does_asset_exist(path) else None
    if mat and MEL.get_num_material_expressions(mat) > 0:
        mat_names[name] = path
        return mat  # already built; never rebuild a referenced material
    mat = mat or A.create_asset(name, MAT_DIR, u.Material, u.MaterialFactoryNew())
    if not mat:
        raise RuntimeError("material create failed: " + name)
    build(mat)
    errors = MEL.recompile_material(mat)
    if errors:
        raise RuntimeError("material compile errors %s: %s" % (name, errors))
    E.save_loaded_asset(mat, False)
    mat_names[name] = path
    return mat


def tex_node(mat, tex_name, sampler_type, x, y):
    node = MEL.create_material_expression(mat, u.MaterialExpressionTextureSample, x, y)
    node.set_editor_property("sampler_type", sampler_type)
    node.set_editor_property("texture", tex_assets[tex_name])
    return node


def scalar(mat, v, x, y):
    node = MEL.create_material_expression(mat, u.MaterialExpressionConstant, x, y)
    node.set_editor_property("r", float(v))
    return node


def connect_prop(src_node, src_pin, prop):
    if not MEL.connect_material_property(src_node, src_pin, prop):
        raise RuntimeError("connect_property failed: %s <- %s" % (prop, src_pin))


def connect_expr(a, a_pin, b, b_pin):
    if not MEL.connect_material_expressions(a, a_pin, b, b_pin):
        raise RuntimeError("connect_expressions failed")


def build_pillow(mat):
    f = FACT["pillow"]
    color = MEL.create_material_expression(
        mat, u.MaterialExpressionConstant3Vector, -500, -150)
    color.set_editor_property("constant", f["color"])
    connect_prop(color, "", u.MaterialProperty.MP_BASE_COLOR)
    connect_prop(scalar(mat, f["roughness"], -500, 150), "",
                 u.MaterialProperty.MP_ROUGHNESS)
    connect_prop(scalar(mat, f["metallic"], -500, 300), "",
                 u.MaterialProperty.MP_METALLIC)


def build_linen(mat):
    f = FACT["lagen"]
    base = tex_node(mat, "T_HospitalBed_LinenBaseColor",
                    u.MaterialSamplerType.SAMPLERTYPE_COLOR, -700, -200)
    mul_c = MEL.create_material_expression(
        mat, u.MaterialExpressionConstant3Vector, -700, 200)
    mul_c.set_editor_property("constant", f["color"])
    mul = MEL.create_material_expression(mat, u.MaterialExpressionMultiply, -450, -100)
    connect_expr(base, "RGB", mul, "A")
    connect_expr(mul_c, "", mul, "B")
    connect_prop(mul, "", u.MaterialProperty.MP_BASE_COLOR)

    mr = tex_node(mat, "T_HospitalBed_LinenMR",
                  u.MaterialSamplerType.SAMPLERTYPE_MASKS, -700, 400)
    rough = MEL.create_material_expression(mat, u.MaterialExpressionMultiply, -450, 400)
    connect_expr(mr, "G", rough, "A")
    connect_expr(scalar(mat, f["roughness"], -450, 550), "", rough, "B")
    connect_prop(rough, "", u.MaterialProperty.MP_ROUGHNESS)

    metal = MEL.create_material_expression(mat, u.MaterialExpressionMultiply, -450, 600)
    connect_expr(mr, "B", metal, "A")
    connect_expr(scalar(mat, f["metallic"], -450, 700), "", metal, "B")
    connect_prop(metal, "", u.MaterialProperty.MP_METALLIC)

    normal = tex_node(mat, "T_HospitalBed_LinenNormal",
                      u.MaterialSamplerType.SAMPLERTYPE_NORMAL, -700, -450)
    connect_prop(normal, "RGB", u.MaterialProperty.MP_NORMAL)

    connect_prop(mr, "R", u.MaterialProperty.MP_AMBIENT_OCCLUSION)


def build_frame(mat):
    f = FACT["material"]
    base = tex_node(mat, "T_HospitalBed_FrameBaseColor",
                    u.MaterialSamplerType.SAMPLERTYPE_COLOR, -600, -150)
    connect_prop(base, "RGB", u.MaterialProperty.MP_BASE_COLOR)
    mr = tex_node(mat, "T_HospitalBed_FrameMR",
                  u.MaterialSamplerType.SAMPLERTYPE_MASKS, -600, 200)
    rough = MEL.create_material_expression(mat, u.MaterialExpressionMultiply, -380, 200)
    connect_expr(mr, "G", rough, "A")
    connect_expr(scalar(mat, f["roughness"], -380, 330), "", rough, "B")
    connect_prop(rough, "", u.MaterialProperty.MP_ROUGHNESS)
    metal = MEL.create_material_expression(mat, u.MaterialExpressionMultiply, -380, 420)
    connect_expr(mr, "B", metal, "A")
    connect_expr(scalar(mat, f["metallic"], -380, 520), "", metal, "B")
    connect_prop(metal, "", u.MaterialProperty.MP_METALLIC)


make_material("M_HospitalBed_Pillow", build_pillow)
make_material("M_HospitalBed_Linen", build_linen)
make_material("M_HospitalBed_Frame", build_frame)
receipt["materials"] = mat_names
print("MATERIALS_DONE", mat_names, flush=True)

# --- 4. slot write-back ---
slots = list(mesh.static_materials)
slot_map = {"Pillow": "M_HospitalBed_Pillow", "Linen": "M_HospitalBed_Linen",
            "Frame": "M_HospitalBed_Frame"}
for i, s in enumerate(slots):
    key = str(s.material_slot_name)
    if key not in slot_map:
        key = str(s.get_editor_property("imported_material_slot_name"))
    if key not in slot_map:
        raise RuntimeError("unmapped material slot: " + key)
    s.material_interface = E.load_asset(MAT_DIR + "/" + slot_map[key])
    slots[i] = s
mesh.set_editor_property("static_materials", slots)
E.set_metadata_tag(mesh, "SourceCredit",
                   "Hospital Bed by loxfear (sketchfab.com/loxfear), CC-BY-4.0")
saved = bool(E.save_loaded_asset(mesh, False))
if not saved:
    raise RuntimeError("failed to save " + MESH)

# --- 5. verify read-back ---
mesh2 = E.load_asset(MESH)
readback = {
    "slots": [{"slot": str(s.material_slot_name),
               "material": s.material_interface.get_path_name() if s.material_interface else None}
              for s in mesh2.static_materials],
    "triangles": None, "bounds": None,
}
try:
    readback["triangles"] = u.EditorStaticMeshLibrary.get_lod_triangle_count(mesh2, 0)
except Exception as e:
    readback["triangles"] = "ERR " + str(e)
try:
    bb = mesh2.get_bounding_box()
    readback["bounds"] = {"min": [round(v, 1) for v in (bb.min.x, bb.min.y, bb.min.z)],
                          "max": [round(v, 1) for v in (bb.max.x, bb.max.y, bb.max.z)]}
except Exception as e:
    readback["bounds"] = "ERR " + str(e)
receipt["verify"] = readback
receipt["saved"] = saved
receipt["game_tested"] = False
receipt["acceptance_rendered"] = False

digest = hashlib.sha256((O / "scene.gltf").read_bytes()).hexdigest()
receipt["source_gltf_sha256"] = digest
(O / "install_receipt.json").write_text(
    json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
print("HOSPITAL_BED_SAVED", json.dumps(readback, ensure_ascii=False), flush=True)
