import json
import os
import unreal

if os.path.exists(r'D:\FPS3D\FPSGAME\SourceAssets\BackpacksReview20261021\alice_saved_assets.json'):
    raise RuntimeError('This OBJ predates the side-pocket openings. Use Tools/BackpackHarness/save_alice_sides.py; do not overwrite the current mesh with the old source.')

U = unreal
SRC = r"D:\FPS3D\FPSGAME\SourceAssets\PortableBackpackAlice20261019"
TEX = os.path.join(SRC, "Textures")
DETAIL = os.path.join(TEX, "detail_v2")
OUT = "/Game/Characters/PortableBackpackAlice20261019"
MESH_NAME = "SM_AliceBackpack"
MESH_FILE = os.environ.get("ALICE_MESH", "AliceBackpack_ue.obj")

MATS = ["Canvas", "Webbing", "Leather", "Metal"]
TILING = {"Canvas": (5.0, 5.0), "Webbing": (7.0, 7.0), "Leather": (5.0, 5.0), "Metal": (4.0, 4.0)}
NORMAL_BLEND = {"Canvas": 0.38, "Webbing": 0.38, "Leather": 0.34, "Metal": 0.28}
ROUGH_BLEND = 0.24


def say(msg):
    print("ALICE_UE " + msg)


def import_asset(filename, dest, name):
    task = U.AssetImportTask()
    task.filename = filename
    task.destination_path = dest
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    U.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return U.load_asset("%s/%s.%s" % (dest, name, name))


def import_texture_file(name, filename, srgb, compression):
    assert os.path.exists(filename), filename
    tex = import_asset(filename, OUT, name)
    assert tex, "texture missing " + name
    tex.set_editor_property("srgb", srgb)
    tex.set_editor_property("compression_settings", compression)
    U.EditorAssetLibrary.save_loaded_asset(tex)
    say("texture %s srgb=%s" % (name, srgb))
    return tex


def import_texture(mat, kind, srgb, compression):
    name = "T_Alice_%s_%s" % (mat, kind)
    return import_texture_file(name, os.path.join(TEX, name + ".png"), srgb, compression)


def import_detail(mat, kind, filename, srgb, compression):
    name = "T_Alice_%s_%s" % (mat, kind)
    return import_texture_file(name, os.path.join(DETAIL, filename), srgb, compression)


def build_material(mat, bc, normal, orm, detail_n, detail_r):
    lib = U.MaterialEditingLibrary
    name = "M_Alice_%s" % mat
    path = "%s/%s.%s" % (OUT, name, name)
    m = U.load_asset(path)
    if not m:
        m = U.AssetToolsHelpers.get_asset_tools().create_asset(name, OUT, U.Material, U.MaterialFactoryNew())
    else:
        for e in list(lib.get_material_expressions(m)):
            lib.delete_material_expression(m, e)
    m.set_editor_property("two_sided", False)

    bc_node = lib.create_material_expression(m, U.MaterialExpressionTextureSample)
    bc_node.texture = bc
    assert lib.connect_material_property(bc_node, "", U.MaterialProperty.MP_BASE_COLOR)

    n_node = lib.create_material_expression(m, U.MaterialExpressionTextureSample)
    n_node.texture = normal
    n_node.set_editor_property("sampler_type", U.MaterialSamplerType.SAMPLERTYPE_NORMAL)

    orm_node = lib.create_material_expression(m, U.MaterialExpressionTextureSample)
    orm_node.texture = orm
    orm_node.set_editor_property("sampler_type", U.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)

    rough_mask = None
    for channel, prop in [("r", "MP_AMBIENT_OCCLUSION"), ("g", "MP_ROUGHNESS")]:
        mask = lib.create_material_expression(m, U.MaterialExpressionComponentMask)
        mask.set_editor_property("r", channel == "r")
        mask.set_editor_property("g", channel == "g")
        mask.set_editor_property("b", False)
        mask.set_editor_property("a", False)
        lib.connect_material_expressions(orm_node, "", mask, "")
        prop_enum = getattr(U.MaterialProperty, prop, None)
        if prop_enum is None:
            say("missing material property " + prop)
            continue
        assert lib.connect_material_property(mask, "", prop_enum)
        if prop == "MP_ROUGHNESS":
            rough_mask = mask

    mask_b = lib.create_material_expression(m, U.MaterialExpressionComponentMask)
    mask_b.set_editor_property("r", False)
    mask_b.set_editor_property("g", False)
    mask_b.set_editor_property("b", True)
    mask_b.set_editor_property("a", False)
    lib.connect_material_expressions(orm_node, "", mask_b, "")
    assert lib.connect_material_property(mask_b, "", U.MaterialProperty.MP_METALLIC)

    # Tiling micro-normals and micro-roughness, independent of the atlas.
    coord = lib.create_material_expression(m, U.MaterialExpressionTextureCoordinate)
    coord.set_editor_property("coordinate_index", 0)
    coord.set_editor_property("u_tiling", TILING[mat][0])
    coord.set_editor_property("v_tiling", TILING[mat][1])

    dn = lib.create_material_expression(m, U.MaterialExpressionTextureSample)
    dn.texture = detail_n
    dn.set_editor_property("sampler_type", U.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    try:
        lib.connect_material_expressions(coord, "", dn, "Coordinates")
    except Exception as exc:
        say("detail normal coordinate connect failed: %s" % exc)

    blend = lib.create_material_expression(m, U.MaterialExpressionLinearInterpolate)
    lib.connect_material_expressions(n_node, "", blend, "A")
    lib.connect_material_expressions(dn, "", blend, "B")
    alpha_n = lib.create_material_expression(m, U.MaterialExpressionConstant)
    alpha_n.set_editor_property("r", NORMAL_BLEND[mat])
    lib.connect_material_expressions(alpha_n, "", blend, "Alpha")
    assert lib.connect_material_property(blend, "", U.MaterialProperty.MP_NORMAL)

    dr = lib.create_material_expression(m, U.MaterialExpressionTextureSample)
    dr.texture = detail_r
    dr.set_editor_property("sampler_type", U.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    try:
        lib.connect_material_expressions(coord, "", dr, "Coordinates")
    except Exception as exc:
        say("detail roughness coordinate connect failed: %s" % exc)

    if rough_mask:
        rblend = lib.create_material_expression(m, U.MaterialExpressionLinearInterpolate)
        lib.connect_material_expressions(rough_mask, "", rblend, "A")
        lib.connect_material_expressions(dr, "", rblend, "B")
        alpha_r = lib.create_material_expression(m, U.MaterialExpressionConstant)
        alpha_r.set_editor_property("r", ROUGH_BLEND)
        lib.connect_material_expressions(alpha_r, "", rblend, "Alpha")
        assert lib.connect_material_property(rblend, "", U.MaterialProperty.MP_ROUGHNESS)

    errs = lib.recompile_material(m)
    assert len(errs) == 0, "material compile %s: %s" % (name, [str(e) for e in errs])
    U.EditorAssetLibrary.save_loaded_asset(m)
    say("material %s" % name)
    return m


# Textures.
textures = {}
for mat in MATS:
    textures[mat] = {
        "bc": import_texture(mat, "BaseColor", True, U.TextureCompressionSettings.TC_DEFAULT),
        "normal": import_texture(mat, "Normal", False, U.TextureCompressionSettings.TC_NORMALMAP),
        "orm": import_texture(mat, "ORM", False, U.TextureCompressionSettings.TC_DEFAULT),
        "detail_n": import_detail(mat, "DetailNormal", "detail_%s_Normal.png" % mat, False, U.TextureCompressionSettings.TC_NORMALMAP),
        "detail_r": import_detail(mat, "DetailRoughness", "detail_%s_Roughness.png" % mat, False, U.TextureCompressionSettings.TC_DEFAULT),
    }

# Mesh and materials.
mesh = import_asset(os.path.join(SRC, MESH_FILE), OUT, MESH_NAME)
assert mesh, "mesh missing"
say("mesh imported %s" % mesh.get_path_name())
say("mesh bounds %s" % str(mesh.get_bounds()))
say("mesh slots %s" % [str(s.material_slot_name) for s in mesh.static_materials])

materials = {mat: build_material(mat, **textures[mat]) for mat in MATS}
for i, slot in enumerate(mesh.static_materials):
    slot_name = str(slot.material_slot_name)
    matched = next((mat for mat in MATS if mat in slot_name), None)
    if matched:
        mesh.set_material(i, materials[matched])
        say("slot %d %s -> %s" % (i, slot_name, materials[matched].get_path_name()))
    else:
        say("slot %d %s unmatched" % (i, slot_name))

U.EditorAssetLibrary.save_loaded_asset(mesh)

# The OBJ importer creates four unused placeholder materials; remove them.
for mat in MATS:
    placeholder = "%s/AliceExport_%s.AliceExport_%s" % (OUT, mat, mat)
    if U.EditorAssetLibrary.does_asset_exist(placeholder):
        say("remove placeholder %s -> %s" % (placeholder, U.EditorAssetLibrary.delete_asset(placeholder)))

receipt = {
    "mesh": mesh.get_path_name(),
    "mesh_source": MESH_FILE,
    "bounds": str(mesh.get_bounds()),
    "static_materials": [
        {
            "index": i,
            "slot": str(s.material_slot_name),
            "material": s.material_interface.get_path_name() if s.material_interface else None,
        }
        for i, s in enumerate(mesh.static_materials)
    ],
    "materials": {mat: m.get_path_name() for mat, m in materials.items()},
    "detail_tiling": TILING,
    "detail_normal_blend": NORMAL_BLEND,
    "detail_roughness_blend": ROUGH_BLEND,
}
with open(os.path.join(SRC, "ue_build_receipt.json"), "w", encoding="utf-8") as f:
    f.write(json.dumps(receipt, ensure_ascii=False, indent=2, default=str))
say("DONE " + json.dumps(receipt, ensure_ascii=False, default=str))
