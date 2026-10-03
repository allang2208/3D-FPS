"""Install the Fab Hospital Waiting Bench (AshenCut, CC-BY-4.0) into /Game/Props.

Single mesh + single material; separate grayscale maps (Metallic/Roughness/AO
are standalone textures, no MR channel splitting needed).
Run via: UnrealEditor-Cmd.exe FPSGAME.uproject -run=pythonscript -script=install.py
"""
import json
from pathlib import Path
import unreal as u

O = Path(__file__).resolve().parent
ROOT = "/Game/Props/HospitalWaitingBench20260929"
TEX = ROOT + "/Textures"
MAT_DIR = ROOT + "/Materials"
MESH = ROOT + "/SM_Hospital_Waiting_Bench"
FBX = O / "Exports/SM_Hospital_Waiting_Bench.fbx"
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
MEL = u.MaterialEditingLibrary

TEXTURES = [  # (file, asset name, sRGB, compression)
    ("T_Hospital_Waiting_Bench_BaseColor.png", "T_Hospital_Waiting_Bench_BaseColor", True, u.TextureCompressionSettings.TC_DEFAULT),
    ("T_Hospital_Waiting_Bench_Metallic.png", "T_Hospital_Waiting_Bench_Metallic", False, u.TextureCompressionSettings.TC_DEFAULT),
    ("T_Hospital_Waiting_Bench_Roughness.png", "T_Hospital_Waiting_Bench_Roughness", False, u.TextureCompressionSettings.TC_DEFAULT),
    ("T_Hospital_Waiting_Bench_Normal.png", "T_Hospital_Waiting_Bench_Normal", False, u.TextureCompressionSettings.TC_NORMALMAP),
    ("T_Hospital_Waiting_Bench_AO.png", "T_Hospital_Waiting_Bench_AO", False, u.TextureCompressionSettings.TC_DEFAULT),
]

receipt = {"mesh": MESH,
           "source": "Fab listing 05f7dccc-ecee-4bd4-9cc1-189ab2f42cc5, Hospital Waiting Bench - AshenCut",
           "license": "CC-BY-4.0, credit required: 'Hospital Waiting Bench - AshenCut' (fab.com), CC-BY-4.0"}

# --- 1. textures ---
tex_assets = {}
for fname, name, srgb, comp in TEXTURES:
    path = TEX + "/" + name
    if not E.does_asset_exist(path):
        task = u.AssetImportTask()
        task.filename = str(O / fname)
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
    task.destination_name = "SM_Hospital_Waiting_Bench"
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

# --- 3. material (separate maps) ---
mat_name = "M_Hospital_Waiting_Bench"
mat_path = MAT_DIR + "/" + mat_name
mat = E.load_asset(mat_path) if E.does_asset_exist(mat_path) else None
if not mat or MEL.get_num_material_expressions(mat) == 0:
    mat = mat or A.create_asset(mat_name, MAT_DIR, u.Material, u.MaterialFactoryNew())
    if not mat:
        raise RuntimeError("material create failed")

    def tex_node(tex_name, sampler_type, y):
        node = MEL.create_material_expression(mat, u.MaterialExpressionTextureSample, -600, y)
        node.set_editor_property("sampler_type", sampler_type)
        node.set_editor_property("texture", tex_assets[tex_name])
        return node

    def connect_prop(src_node, src_pin, prop):
        if not MEL.connect_material_property(src_node, src_pin, prop):
            raise RuntimeError("connect_property failed: " + str(prop))

    base = tex_node("T_Hospital_Waiting_Bench_BaseColor",
                    u.MaterialSamplerType.SAMPLERTYPE_COLOR, -200)
    connect_prop(base, "RGB", u.MaterialProperty.MP_BASE_COLOR)

    metal = tex_node("T_Hospital_Waiting_Bench_Metallic",
                     u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR, 0)
    connect_prop(metal, "R", u.MaterialProperty.MP_METALLIC)

    rough = tex_node("T_Hospital_Waiting_Bench_Roughness",
                     u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR, 200)
    connect_prop(rough, "R", u.MaterialProperty.MP_ROUGHNESS)

    normal = tex_node("T_Hospital_Waiting_Bench_Normal",
                      u.MaterialSamplerType.SAMPLERTYPE_NORMAL, 400)
    connect_prop(normal, "RGB", u.MaterialProperty.MP_NORMAL)

    ao = tex_node("T_Hospital_Waiting_Bench_AO",
                  u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR, 600)
    connect_prop(ao, "R", u.MaterialProperty.MP_AMBIENT_OCCLUSION)

    errors = MEL.recompile_material(mat)
    if errors:
        raise RuntimeError("material compile errors: %s" % errors)
    E.save_loaded_asset(mat, False)
receipt["material"] = mat_path
print("MATERIAL_DONE", mat_path, flush=True)

# --- 4. slot write-back ---
slots = list(mesh.static_materials)
for i, s in enumerate(slots):
    s.material_interface = E.load_asset(mat_path)
    slots[i] = s
mesh.set_editor_property("static_materials", slots)
E.set_metadata_tag(mesh, "SourceCredit",
                   "Hospital Waiting Bench - AshenCut (fab.com), CC-BY-4.0")
saved = bool(E.save_loaded_asset(mesh, False))
if not saved:
    raise RuntimeError("failed to save " + MESH)

# --- 5. read-back ---
mesh2 = E.load_asset(MESH)
readback = {
    "slots": [{"slot": str(s.material_slot_name),
               "material": s.material_interface.get_path_name() if s.material_interface else None}
              for s in mesh2.static_materials],
    "bounds": None,
}
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
(O / "install_receipt.json").write_text(
    json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
print("BENCH_SAVED", json.dumps(readback, ensure_ascii=False), flush=True)
