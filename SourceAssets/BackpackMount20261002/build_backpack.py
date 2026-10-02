# 登山包资产导入（无头 commandlet）：OBJ→静态网格，3 张 PNG→贴图，组装 PBR 材质，
# 并打印 Manny 躯体 spine 骨骼参考姿态（给背包骨挂偏移求值用）。
# 用法：run_ue.ps1 -Script build_backpack.py
import json, os
import unreal

U = unreal
SRC = r"D:\FPS3D\FPSGAME\SourceAssets\BackpackMount20261002"
OUT = "/Game/Characters/SovietBackpack20261002"
MESH_NAME = "SM_SovietBackpack"
BODY = "/Game/Characters/Mannequins/PlayerBodySkin/SKM_Manny_PlayerSkin.SKM_Manny_PlayerSkin"

TEX_SRC = [
    ("T_SovietBackpack_BaseColor.png", "T_SovietBackpack_BaseColor", True),
    ("T_SovietBackpack_Normal.png", "T_SovietBackpack_Normal", False),
    ("T_SovietBackpack_MR.png", "T_SovietBackpack_MR", False),
]


def say(msg):
    print("BACKPACK " + msg)


def import_asset(filename, dest, name, options=None):
    t = U.AssetImportTask()
    t.filename = filename
    t.destination_path = dest
    t.destination_name = name
    t.automated = True
    t.replace_existing = True
    t.save = True
    if options:
        t.options = options
    U.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    return [str(p) for p in t.get_objects()] if hasattr(t, "get_objects") else []


def build_material():
    lib = U.MaterialEditingLibrary
    path = "%s/M_SovietBackpack.M_SovietBackpack" % OUT
    m = U.load_asset(path)
    if m and lib.get_num_material_expressions(m) > 0:
        say("material reuse M_SovietBackpack")
        return m
    m = m or U.AssetToolsHelpers.get_asset_tools().create_asset(
        "M_SovietBackpack", OUT, U.Material, U.MaterialFactoryNew())
    tex_bc = U.load_asset("%s/T_SovietBackpack_BaseColor.T_SovietBackpack_BaseColor" % OUT)
    tex_n = U.load_asset("%s/T_SovietBackpack_Normal.T_SovietBackpack_Normal" % OUT)
    tex_mr = U.load_asset("%s/T_SovietBackpack_MR.T_SovietBackpack_MR" % OUT)
    assert tex_bc and tex_n and tex_mr, "textures missing"

    bc = lib.create_material_expression(m, U.MaterialExpressionTextureSample)
    bc.texture = tex_bc
    assert lib.connect_material_property(bc, "", U.MaterialProperty.MP_BASE_COLOR)

    nm = lib.create_material_expression(m, U.MaterialExpressionTextureSample)
    nm.texture = tex_n
    nm.set_editor_property("sampler_type", U.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    assert lib.connect_material_property(nm, "", U.MaterialProperty.MP_NORMAL)

    mr = lib.create_material_expression(m, U.MaterialExpressionTextureSample)
    mr.texture = tex_mr
    mr.set_editor_property("sampler_type", U.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    mask_g = lib.create_material_expression(m, U.MaterialExpressionComponentMask)
    mask_g.set_editor_property("g", True)
    lib.connect_material_expressions(mr, "", mask_g, "")
    assert lib.connect_material_property(mask_g, "", U.MaterialProperty.MP_ROUGHNESS)
    mask_b = lib.create_material_expression(m, U.MaterialExpressionComponentMask)
    mask_b.set_editor_property("b", True)
    lib.connect_material_expressions(mr, "", mask_b, "")
    assert lib.connect_material_property(mask_b, "", U.MaterialProperty.MP_METALLIC)

    errs = lib.recompile_material(m)
    assert len(errs) == 0, "material compile: %s" % errs
    U.EditorAssetLibrary.save_loaded_asset(m)
    say("material authored M_SovietBackpack")
    return m


def probe_spine():
    body = U.load_asset(BODY)
    assert body, "body mesh missing"
    ref = body.get_ref_skeleton()
    bounds = body.get_bounds()
    say("body bounds origin=%s extent=%s" % (bounds.origin, bounds.box_extent))
    for name in ("spine_01", "spine_02", "spine_03", "spine_04", "spine_05", "pelvis"):
        i = ref.find_bone_index(name)
        if i < 0:
            say("bone %s MISSING" % name)
            continue
        t = ref.get_ref_bone_pose()[i]
        # 累乘到组件空间
        chain = [i]
        p = ref.get_parent_index(i)
        while p >= 0:
            chain.append(p)
            p = ref.get_parent_index(p)
        comp = U.Transform()
        poses = ref.get_ref_bone_pose()
        for b in reversed(chain):
            comp = comp * poses[b]
        say("bone %s comp_loc=%s comp_rot=%s" % (name, comp.translation, comp.rotation.rotator()))


def build():
    for src, name, srgb in TEX_SRC:
        paths = import_asset(os.path.join(SRC, src), OUT, name)
        say("imported %s -> %s" % (src, paths))
        tex = U.load_asset("%s/%s.%s" % (OUT, name, name))
        assert tex, "texture missing " + name
        tex.set_editor_property("srgb", srgb)
        if name == "T_SovietBackpack_Normal":
            tex.set_editor_property("compression_settings", U.TextureCompressionSettings.TC_NORMALMAP)
        U.EditorAssetLibrary.save_loaded_asset(tex)

    paths = import_asset(os.path.join(SRC, "soviet_backpack.obj"), OUT, MESH_NAME)
    say("imported mesh -> %s" % paths)
    sm = U.load_asset("%s/%s.%s" % (OUT, MESH_NAME, MESH_NAME))
    assert sm, "mesh missing"

    mat = build_material()
    for i in range(len(sm.static_materials)):
        sm.set_material(i, mat)
    U.EditorAssetLibrary.save_loaded_asset(sm)

    probe_spine()

    receipt = {
        "mesh": sm.get_path_name(),
        "slots": [{"index": i, "slot": str(s.material_slot_name),
                   "material": s.material_interface.get_path_name() if s.material_interface else None}
                  for i, s in enumerate(sm.static_materials)],
        "bounds": str(sm.get_bounds()),
        "material": mat.get_path_name(),
    }
    with open(os.path.join(SRC, "backpack_receipt.json"), "w") as f:
        f.write(json.dumps(receipt, indent=2, default=str))
    say("receipt " + json.dumps(receipt, default=str))


build()
