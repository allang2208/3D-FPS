"""Import the Fab wooden longbow and point bows.json at it."""
from __future__ import annotations

import json
from pathlib import Path

import unreal as u

HERE = Path(__file__).resolve().parent
DEST = "/Game/Weapons/DarkBow20260925/WoodLongbow20260925"
TEX_DEST = DEST + "/Textures"
NAME = "SM_DarkBow_WoodLongbow"
MAT_NAME = "M_WoodLongbow_PBR"
FBX = HERE / "Export" / (NAME + "_cm.fbx")
AUTHOR = json.loads((HERE / "authoring.json").read_text(encoding="utf-8"))
BOWS = Path(u.Paths.project_dir()) / "Content" / "ColdSteelData" / "bows.json"
DRAW_CM = 28.5
ARROW_Z_CM = 1.5
EAL = u.EditorAssetLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
L = u.MaterialEditingLibrary
Q = u.GeometryScript_MeshQueries


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


def read_dm(mesh):
    dm, outcome = u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(
        mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD()
    )
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError("read mesh failed")
    return dm


def remesure_nocks(dm):
    _, verts, _ = Q.get_all_vertex_positions(dm, False)
    pts = list(u.GeometryScript_List.convert_vector_list_to_array(verts))
    upper = [p for p in pts if p.z > 50.0]
    lower = [p for p in pts if p.z < -50.0]
    if len(upper) < 8 or len(lower) < 8:
        raise RuntimeError("tip bands empty: %s %s" % (len(upper), len(lower)))

    def nock_of(band):
        ordered = sorted(band, key=lambda p: (p.x, abs(p.y)))
        pick = ordered[: max(12, len(ordered) // 40)]
        return [
            round(sum(p.x for p in pick) / float(len(pick)), 3),
            round(sum(p.y for p in pick) / float(len(pick)), 3),
            round(sum(p.z for p in pick) / float(len(pick)), 3),
        ]

    nock_u = nock_of(upper)
    nock_l = nock_of(lower)
    brace = [
        round((nock_u[0] + nock_l[0]) * 0.5, 3),
        round((nock_u[1] + nock_l[1]) * 0.5, 3),
        ARROW_Z_CM,
    ]
    return {
        "nock_upper_cm": nock_u,
        "nock_lower_cm": nock_l,
        "brace_nock_cm": brace,
        "draw_anchor_cm": [round(brace[0] - DRAW_CM, 3), brace[1], brace[2]],
        "arrow_rest_cm": [0.0, brace[1], brace[2]],
    }


def import_task(filename, dest, name, options=None):
    task = u.AssetImportTask()
    task.filename = str(filename)
    task.destination_path = dest
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    if options is not None:
        task.options = options
    TOOLS.import_asset_tasks([task])
    asset = u.load_asset(dest + "/" + name)
    if asset is None:
        raise RuntimeError("import did not produce " + dest + "/" + name)
    return asset


def import_texture(src, name, srgb, normal=False):
    tex = import_task(src, TEX_DEST, name)
    tex.set_editor_property("srgb", srgb)
    if normal:
        tex.set_editor_property("compression_settings", u.TextureCompressionSettings.TC_NORMALMAP)
    save_asset(tex)
    return tex


def make_pbr(base, orm, normal):
    path = DEST + "/" + MAT_NAME
    if EAL.does_asset_exist(path):
        EAL.delete_asset(path)
    mat = TOOLS.create_asset(MAT_NAME, DEST, u.Material, u.MaterialFactoryNew())
    samp_base = L.create_material_expression(mat, u.MaterialExpressionTextureSampleParameter2D)
    samp_base.set_editor_property("parameter_name", "BaseColor")
    samp_base.set_editor_property("texture", base)
    samp_orm = L.create_material_expression(mat, u.MaterialExpressionTextureSampleParameter2D)
    samp_orm.set_editor_property("parameter_name", "ORM")
    samp_orm.set_editor_property("texture", orm)
    samp_orm.set_editor_property("sampler_type", u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    samp_n = L.create_material_expression(mat, u.MaterialExpressionTextureSampleParameter2D)
    samp_n.set_editor_property("parameter_name", "Normal")
    samp_n.set_editor_property("texture", normal)
    samp_n.set_editor_property("sampler_type", u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    if not L.connect_material_property(samp_base, "", u.MaterialProperty.MP_BASE_COLOR):
        raise RuntimeError("base color wire failed")
    if not L.connect_material_property(samp_orm, "G", u.MaterialProperty.MP_ROUGHNESS):
        raise RuntimeError("roughness wire failed")
    if not L.connect_material_property(samp_orm, "B", u.MaterialProperty.MP_METALLIC):
        raise RuntimeError("metallic wire failed")
    if not L.connect_material_property(samp_n, "", u.MaterialProperty.MP_NORMAL):
        raise RuntimeError("normal wire failed")
    L.recompile_material(mat)
    save_asset(mat)
    return mat


if not FBX.is_file():
    raise RuntimeError("missing " + str(FBX))

u.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
if EAL.does_directory_exist(DEST):
    for asset_path in list(EAL.list_assets(DEST, True, False) or []):
        EAL.delete_asset(asset_path)
EAL.make_directory(DEST)
EAL.make_directory(TEX_DEST)

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
opt.static_mesh_import_data.build_nanite = False
opt.static_mesh_import_data.import_uniform_scale = 1.0
mesh = import_task(FBX, DEST, NAME, opt)
try:
    nanite = mesh.get_editor_property("nanite_settings")
    nanite.enabled = False
    mesh.set_editor_property("nanite_settings", nanite)
except Exception:
    pass

info = bounds_cm(mesh)
lod0 = int(mesh.get_num_triangles(0))
if lod0 < 15000:
    raise RuntimeError("imported mesh too thin: lod0=%s %s" % (lod0, info))
if info["size"][2] < 120 or info["size"][2] > 170:
    raise RuntimeError("length axis wrong: " + str(info))
if info["size"][1] < 4.0 or info["size"][1] > 14.0:
    raise RuntimeError("limb width unexpected: " + str(info))
if max(info["size"]) < 120 or max(info["size"]) > 180:
    raise RuntimeError("imported size not a longbow: " + str(info))

dm = read_dm(mesh)
nocks = remesure_nocks(dm)
tex_base = import_texture(HERE / "Textures" / "Image_0.png", "T_WoodLongbow_BaseColor", True)
tex_orm = import_texture(HERE / "Textures" / "Image_1.png", "T_WoodLongbow_ORM", False)
tex_n = import_texture(HERE / "Textures" / "Image_2.png", "T_WoodLongbow_Normal", False, True)
material = make_pbr(tex_base, tex_orm, tex_n)
slots = list(mesh.static_materials)
if not slots:
    raise RuntimeError("mesh has no material slots")
for i, slot in enumerate(slots):
    mesh.set_material(i, material)
    slot.set_editor_property("material_interface", material)
    slots[i] = slot
mesh.set_editor_property("static_materials", slots)
save_asset(mesh)

readback = []
for i, slot in enumerate(list(mesh.static_materials)):
    bound = slot.material_interface
    readback.append({
        "index": i,
        "name": str(slot.material_slot_name),
        "material": bound.get_path_name() if bound else None,
    })
    if bound is None or MAT_NAME not in bound.get_path_name():
        raise RuntimeError("pbr bind failed " + str(readback[-1]))

bows = json.loads(BOWS.read_text(encoding="utf-8"))
item = bows["bow_dark"]
replaced = item.get("bow_part_riser_mesh")
item["bow_part_riser_mesh"] = mesh.get_path_name()
item["bow_part_riser_material"] = ""
item["nock_upper_cm"] = "{0},{1},{2}".format(*nocks["nock_upper_cm"])
item["nock_lower_cm"] = "{0},{1},{2}".format(*nocks["nock_lower_cm"])
item["brace_nock_cm"] = "{0},{1},{2}".format(*nocks["brace_nock_cm"])
item["draw_anchor_cm"] = "{0},{1},{2}".format(*nocks["draw_anchor_cm"])
item["arrow_rest_cm"] = "{0},{1},{2}".format(*nocks["arrow_rest_cm"])
item["bow_length_cm"] = round(info["size"][2], 1)
item["bow_depth_cm"] = round(info["size"][0], 1)
item["bow_presentation_revision"] = 13
BOWS.write_text(json.dumps(bows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

receipt = {
    "mesh": mesh.get_path_name(),
    "tris": lod0,
    "bounds_cm": bounds_cm(mesh),
    "fixes": ["fbx_cm_units"],
    "slots": readback,
    "nock_upper_cm": nocks["nock_upper_cm"],
    "nock_lower_cm": nocks["nock_lower_cm"],
    "brace_nock_cm": nocks["brace_nock_cm"],
    "draw_anchor_cm": nocks["draw_anchor_cm"],
    "arrow_rest_cm": nocks["arrow_rest_cm"],
    "material": material.get_path_name(),
    "textures": [tex_base.get_path_name(), tex_orm.get_path_name(), tex_n.get_path_name()],
    "bows_riser": item["bow_part_riser_mesh"],
    "presentation_revision": 13,
    "replaced": replaced,
    "runtime_tested": False,
}
(HERE / "import_receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print("BOW_WOOD_LONGBOW_IMPORTED", json.dumps(receipt), flush=True)