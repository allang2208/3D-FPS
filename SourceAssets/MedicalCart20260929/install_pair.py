"""Install two Sketchfab hospital props into /Game/Props:
- Rusty Medical Cart (3 materials, Arnold-named -> Cart_A/B/C), 4k textures
- Crutch and IV Drip (3 materials: Crutch/Stand/Drip), 2k textures
Both glTF metalRoughness split: G=Roughness, B=Metallic (factors multiplied).
Run via: UnrealEditor-Cmd.exe FPSGAME.uproject -run=pythonscript -script=install_pair.py
"""
import json
from pathlib import Path
import unreal as u

E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
MEL = u.MaterialEditingLibrary

ASSETS = [
    {
        "key": "MedicalCart",
        "src": "Sketchfab 508d17d0d77c4d10a3a9ddc043241d31 'Rusty medical cart'",
        "root": "/Game/Props/MedicalCart20260929",
        "fbx": "D:/FPS3D/FPSGAME/SourceAssets/MedicalCart20260929/Exports/SM_Hospital_MedicalCart.fbx",
        "tex_dir": "D:/FPS3D/FPSGAME/SourceAssets/MedicalCart20260929/textures",
        "mesh_name": "SM_Hospital_MedicalCart",
        "tex_prefix": "T_HospitalCart",
        "mat_prefix": "M_HospitalCart",
        "mats": [  # (slot, gltf material name, metallicFactor, roughnessFactor)
            ("Cart_A", "aiStandardSurface1SG", 1.0, 1.0),
            ("Cart_B", "aiStandardSurface6SG", 1.0, 1.0),
            ("Cart_C", "aiStandardSurface7SG", 0.0, 1.0),
        ],
        "license": "CC-BY-4.0, credit: 'Rusty medical cart' by Turinka_3D (sketchfab.com), CC-BY-4.0",
    },
    {
        "key": "IVDripCrutch",
        "src": "Sketchfab 5cc65c6aed374220b67f7d60e679153e 'Crutch and IV Drip'",
        "root": "/Game/Props/IVDripCrutch20260929",
        "fbx": "D:/FPS3D/FPSGAME/SourceAssets/IVDripCrutch20260929/Exports/SM_Hospital_IVDrip_Crutch.fbx",
        "tex_dir": "D:/FPS3D/FPSGAME/SourceAssets/IVDripCrutch20260929/textures",
        "mesh_name": "SM_Hospital_IVDrip_Crutch",
        "tex_prefix": "T_HospitalIV",
        "mat_prefix": "M_HospitalIV",
        "mats": [
            ("Crutch", "Crutch", 1.0, 1.0),
            ("Stand", "material", 1.0, 1.0),
            ("Drip", "Drip", 0.0, 1.0),
        ],
        "license": "CC-BY-4.0, credit: 'Crutch and IV Drip' by Davide G. Triulzi (sketchfab.com), CC-BY-4.0",
    },
]

receipts = {}
for cfg in ASSETS:
    TEX = cfg["root"] + "/Textures"
    MAT_DIR = cfg["root"] + "/Materials"
    MESH = cfg["root"] + "/" + cfg["mesh_name"]
    receipt = {"mesh": MESH, "source": cfg["src"], "license": cfg["license"]}
    r = {}

    # --- textures: per glTF material (baseColor / metallicRoughness / normal) ---
    tex_assets = {}
    for slot, gltf_name, _mf, _rf in cfg["mats"]:
        for kind, suffix, srgb, comp in [
            ("BaseColor", "baseColor", True, u.TextureCompressionSettings.TC_DEFAULT),
            ("MR", "metallicRoughness", False, u.TextureCompressionSettings.TC_MASKS),
            ("Normal", "normal", False, u.TextureCompressionSettings.TC_NORMALMAP),
        ]:
            name = "%s_%s_%s" % (cfg["tex_prefix"], slot, kind)
            path = TEX + "/" + name
            if not E.does_asset_exist(path):
                task = u.AssetImportTask()
                task.filename = "%s/%s_%s.png" % (cfg["tex_dir"], gltf_name, suffix)
                task.destination_path = TEX
                task.destination_name = name
                task.factory = u.TextureFactory()
                task.automated = True
                task.save = False
                A.import_asset_tasks([task])
                t = E.load_asset(path)
                if not t:
                    raise RuntimeError("texture import failed: " + name)
                t.set_editor_property("srgb", srgb)
                t.set_editor_property("compression_settings", comp)
                E.save_loaded_asset(t, False)
            tex_assets[name] = E.load_asset(path)
    receipt["textures"] = sorted(tex_assets.keys())
    print("TEXTURES_DONE", cfg["key"], len(tex_assets), flush=True)

    # --- static mesh ---
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
        task.filename = cfg["fbx"]
        task.destination_path = cfg["root"]
        task.destination_name = cfg["mesh_name"]
        task.options = options
        task.factory = u.FbxFactory()
        task.automated = True
        task.replace_existing = False
        task.save = False
        A.import_asset_tasks([task])
    mesh = E.load_asset(MESH)
    if not mesh:
        raise RuntimeError("mesh import failed: " + cfg["key"])
    print("MESH_DONE", cfg["key"], [str(s.material_slot_name) for s in mesh.static_materials], flush=True)

    # --- materials (gltf MR split) ---
    mat_paths = {}
    for slot, _g, mf, rf in cfg["mats"]:
        mat_name = "%s_%s" % (cfg["mat_prefix"], slot)
        mat_path = MAT_DIR + "/" + mat_name
        mat = E.load_asset(mat_path) if E.does_asset_exist(mat_path) else None
        if not mat or MEL.get_num_material_expressions(mat) == 0:
            mat = mat or A.create_asset(mat_name, MAT_DIR, u.Material, u.MaterialFactoryNew())
            if not mat:
                raise RuntimeError("material create failed: " + mat_name)

            def tex_node(tex_name, sampler_type, y):
                node = MEL.create_material_expression(mat, u.MaterialExpressionTextureSample, -600, y)
                node.set_editor_property("sampler_type", sampler_type)
                node.set_editor_property("texture", tex_assets[tex_name])
                return node

            def scalar(v, y):
                node = MEL.create_material_expression(mat, u.MaterialExpressionConstant, -380, y)
                node.set_editor_property("r", float(v))
                return node

            def connect_prop(src_node, src_pin, prop):
                if not MEL.connect_material_property(src_node, src_pin, prop):
                    raise RuntimeError("connect failed: %s %s" % (mat_name, prop))

            base = tex_node("%s_%s_BaseColor" % (cfg["tex_prefix"], slot),
                            u.MaterialSamplerType.SAMPLERTYPE_COLOR, -250)
            connect_prop(base, "RGB", u.MaterialProperty.MP_BASE_COLOR)

            mr = tex_node("%s_%s_MR" % (cfg["tex_prefix"], slot),
                          u.MaterialSamplerType.SAMPLERTYPE_MASKS, 0)
            rough = MEL.create_material_expression(mat, u.MaterialExpressionMultiply, -380, 0)
            if not (MEL.connect_material_expressions(mr, "G", rough, "A")
                    and MEL.connect_material_expressions(scalar(rf, 120), "", rough, "B")):
                raise RuntimeError("roughness connect failed: " + mat_name)
            connect_prop(rough, "", u.MaterialProperty.MP_ROUGHNESS)

            metal = MEL.create_material_expression(mat, u.MaterialExpressionMultiply, -380, 200)
            if not (MEL.connect_material_expressions(mr, "B", metal, "A")
                    and MEL.connect_material_expressions(scalar(mf, 300), "", metal, "B")):
                raise RuntimeError("metallic connect failed: " + mat_name)
            connect_prop(metal, "", u.MaterialProperty.MP_METALLIC)

            normal = tex_node("%s_%s_Normal" % (cfg["tex_prefix"], slot),
                              u.MaterialSamplerType.SAMPLERTYPE_NORMAL, 400)
            connect_prop(normal, "RGB", u.MaterialProperty.MP_NORMAL)

            errors = MEL.recompile_material(mat)
            if errors:
                raise RuntimeError("material compile errors %s: %s" % (mat_name, errors))
            E.save_loaded_asset(mat, False)
        mat_paths[slot] = mat_path
    receipt["materials"] = mat_paths
    print("MATERIALS_DONE", cfg["key"], mat_paths, flush=True)

    # --- slot write-back by slot name ---
    slots = list(mesh.static_materials)
    for i, s in enumerate(slots):
        key = str(s.material_slot_name)
        if key not in mat_paths:
            key = str(s.get_editor_property("imported_material_slot_name"))
        if key not in mat_paths:
            raise RuntimeError("unmapped slot %s in %s" % (key, cfg["key"]))
        s.material_interface = E.load_asset(mat_paths[key])
        slots[i] = s
    mesh.set_editor_property("static_materials", slots)
    E.set_metadata_tag(mesh, "SourceCredit", cfg["license"])
    saved = bool(E.save_loaded_asset(mesh, False))
    if not saved:
        raise RuntimeError("failed to save " + MESH)

    mesh2 = E.load_asset(MESH)
    rb = {"slots": [{"slot": str(s.material_slot_name),
                     "material": s.material_interface.get_path_name() if s.material_interface else None}
                    for s in mesh2.static_materials],
          "bounds": None}
    try:
        bb = mesh2.get_bounding_box()
        rb["bounds"] = {"min": [round(v, 1) for v in (bb.min.x, bb.min.y, bb.min.z)],
                        "max": [round(v, 1) for v in (bb.max.x, bb.max.y, bb.max.z)]}
    except Exception as e:
        rb["bounds"] = "ERR " + str(e)
    receipt["verify"] = rb
    receipt["saved"] = saved
    receipt["game_tested"] = False
    receipt["acceptance_rendered"] = False
    out = Path(cfg["fbx"]).parent.parent / "install_receipt.json"
    out.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    receipts[cfg["key"]] = rb
    print("SAVED", cfg["key"], json.dumps(rb, ensure_ascii=False), flush=True)

print("ALL_DONE", flush=True)
