"""Import the field boonie hat mesh, PBR surfaces, LODs, pickup and icon."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import unreal as u

P = Path("D:/FPS3D/FPSGAME")
SRC = P / "SourceAssets/FieldHat20261019"
DEST = "/Game/Characters/ModularOutfit20260924/FieldHat20261019"
SLOTS = ["Canvas", "CanvasUnder", "Leather", "Brass", "Lining", "Thread"]
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
L = u.MaterialEditingLibrary
G = u.GeometryScript_AssetUtils
S = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
receipt_path = SRC / "saved_assets.json"
receipt = json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path.exists() else {"runtime_tested": False}


def record():
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(P / path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def load(path):
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError("Missing " + path)
    return asset


def save(asset):
    if not asset.get_path_name().startswith(DEST + "/"):
        raise RuntimeError("Asset outside field-hat scope: " + asset.get_path_name())
    asset.modify()
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError("Cannot save " + asset.get_path_name())


def texture_assets():
    folder = DEST + "/Textures"
    E.make_directory(folder)
    result = {}
    for family, size in (("Canvas", 4096), ("Leather", 2048)):
        for channel in ("BaseColor", "Normal", "ORM"):
            name = "T_FieldHat_" + family + "_" + channel
            task = u.AssetImportTask()
            task.filename = str(SRC / "Textures" / (name + ".png"))
            task.destination_path = folder
            task.destination_name = name
            task.automated = True
            task.replace_existing = True
            task.save = False
            A.import_asset_tasks([task])
            tex = load(folder + "/" + name)
            tex.set_editor_property("srgb", channel == "BaseColor")
            tex.set_editor_property("compression_settings",
                                    u.TextureCompressionSettings.TC_NORMALMAP if channel == "Normal"
                                    else u.TextureCompressionSettings.TC_MASKS if channel == "ORM"
                                    else u.TextureCompressionSettings.TC_DEFAULT)
            tex.set_editor_property("flip_green_channel", channel == "Normal")
            tex.set_editor_property("never_stream", False)
            tex.set_editor_property("max_texture_size", size)
            tex.set_editor_property("compression_no_alpha", True)
            tex.set_editor_property("address_x", u.TextureAddress.TA_WRAP)
            tex.set_editor_property("address_y", u.TextureAddress.TA_WRAP)
            save(tex)
            result[family + "_" + channel] = tex
    return result


def create_materials(tex):
    folder = DEST + "/Materials"
    E.make_directory(folder)

    def material(name, family, tint=None, rough_add=0.0):
        mat = u.load_asset(folder + "/" + name) or A.create_asset(name, folder, u.Material, u.MaterialFactoryNew())
        L.delete_all_material_expressions(mat)
        mat.set_editor_property("two_sided", False)
        L.set_material_usage(mat, u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
        L.set_material_usage(mat, u.MaterialUsage.MATUSAGE_STATIC_MESH)
        uv = L.create_material_expression(mat, u.MaterialExpressionTextureCoordinate)
        nodes = {}
        for channel in ("BaseColor", "Normal", "ORM"):
            node = L.create_material_expression(mat, u.MaterialExpressionTextureSampleParameter2D)
            node.set_editor_property("parameter_name", family + "_" + channel)
            node.set_editor_property("texture", tex[family + "_" + channel])
            node.set_editor_property("sampler_type",
                                     u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel == "Normal"
                                     else u.MaterialSamplerType.SAMPLERTYPE_MASKS if channel == "ORM"
                                     else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
            if not L.connect_material_expressions(uv, "", node, "UVs"):
                raise RuntimeError("UV connection failed " + name + " " + channel)
            nodes[channel] = node
        if tint:
            mul = L.create_material_expression(mat, u.MaterialExpressionMultiply)
            tint_node = L.create_material_expression(mat, u.MaterialExpressionConstant3Vector)
            tint_node.set_editor_property("constant", u.LinearColor(tint[0], tint[1], tint[2], 1.0))
            if not L.connect_material_expressions(nodes["BaseColor"], "RGB", mul, "A"):
                raise RuntimeError("Tint A failed")
            if not L.connect_material_expressions(tint_node, "", mul, "B"):
                raise RuntimeError("Tint B failed")
            base_socket = mul
        else:
            base_socket = nodes["BaseColor"]
        if not L.connect_material_property(base_socket, "" if tint else "RGB", u.MaterialProperty.MP_BASE_COLOR):
            raise RuntimeError("BaseColor failed " + name)
        if not L.connect_material_property(nodes["Normal"], "RGB", u.MaterialProperty.MP_NORMAL):
            raise RuntimeError("Normal failed " + name)
        if rough_add:
            add = L.create_material_expression(mat, u.MaterialExpressionAdd)
            const = L.create_material_expression(mat, u.MaterialExpressionConstant)
            const.set_editor_property("r", rough_add)
            if not L.connect_material_expressions(nodes["ORM"], "G", add, "A"):
                raise RuntimeError("Rough A failed")
            if not L.connect_material_expressions(const, "", add, "B"):
                raise RuntimeError("Rough B failed")
            rough_socket = add
        else:
            rough_socket = nodes["ORM"]
        for node, pin, prop in ((nodes["ORM"], "R", u.MaterialProperty.MP_AMBIENT_OCCLUSION),
                                (rough_socket, "G" if not rough_add else "", u.MaterialProperty.MP_ROUGHNESS),
                                (nodes["ORM"], "B", u.MaterialProperty.MP_METALLIC)):
            if not L.connect_material_property(node, pin, prop):
                raise RuntimeError("ORM failed " + name + " " + str(prop))
        errors = L.recompile_material(mat)
        if errors:
            raise RuntimeError("Material compile failed " + name + ": " + str(errors))
        save(mat)
        return mat

    def solid(name, colour, metallic, roughness):
        mat = u.load_asset(folder + "/" + name) or A.create_asset(name, folder, u.Material, u.MaterialFactoryNew())
        L.delete_all_material_expressions(mat)
        mat.set_editor_property("two_sided", False)
        L.set_material_usage(mat, u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
        L.set_material_usage(mat, u.MaterialUsage.MATUSAGE_STATIC_MESH)
        base = L.create_material_expression(mat, u.MaterialExpressionConstant3Vector)
        base.set_editor_property("constant", u.LinearColor(colour[0], colour[1], colour[2], 1.0))
        if not L.connect_material_property(base, "", u.MaterialProperty.MP_BASE_COLOR):
            raise RuntimeError("Solid base failed " + name)
        for value, prop in ((metallic, u.MaterialProperty.MP_METALLIC), (roughness, u.MaterialProperty.MP_ROUGHNESS)):
            node = L.create_material_expression(mat, u.MaterialExpressionConstant)
            node.set_editor_property("r", value)
            if not L.connect_material_property(node, "", prop):
                raise RuntimeError("Solid constant failed " + name)
        errors = L.recompile_material(mat)
        if errors:
            raise RuntimeError("Solid compile failed " + name + ": " + str(errors))
        save(mat)
        return mat

    return [
        material("M_FieldHat_Canvas", "Canvas"),
        material("M_FieldHat_CanvasUnder", "Canvas", tint=(0.66, 0.61, 0.48), rough_add=0.06),
        material("M_FieldHat_Leather", "Leather"),
        solid("M_FieldHat_Brass", (0.62, 0.43, 0.20), 0.85, 0.30),
        solid("M_FieldHat_Lining", (0.055, 0.040, 0.028), 0.0, 0.86),
        solid("M_FieldHat_Thread", (0.46, 0.40, 0.30), 0.0, 0.62),
    ]


def skeletal(mats, d):
    file = SRC / "Exports/FieldHat.fbx"
    sha = hashlib.sha256(file.read_bytes()).hexdigest()
    name = "SK_FieldHat"
    path = DEST + "/" + name
    mesh = u.load_asset(path)
    if mesh and E.get_metadata_tag(mesh, "FieldHatSHA") == sha:
        receipt["mesh"] = mesh.get_path_name()
        receipt["skeleton"] = mesh.skeleton.get_path_name()
        receipt["fbx_sha256"] = sha
        record()
        return mesh
    u.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_as_skeletal = True
    options.import_mesh = True
    options.import_animations = False
    options.import_materials = False
    options.import_textures = False
    options.create_physics_asset = False
    options.skeleton = mesh.skeleton if mesh else None
    data = options.skeletal_mesh_import_data
    data.convert_scene = True
    data.convert_scene_unit = True
    data.import_uniform_scale = 1.0
    data.force_front_x_axis = False
    data.set_editor_property("update_skeleton_reference_pose", False)
    data.set_editor_property("use_t0_as_ref_pose", False)
    data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task = u.AssetImportTask()
    task.filename = str(file)
    task.destination_path = DEST
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    task.options = options
    A.import_asset_tasks([task])
    mesh = load(path)
    slots = list(mesh.get_editor_property("materials"))
    byname = dict(zip(SLOTS, mats))
    for slot in slots:
        slotname = str(slot.get_editor_property("imported_material_slot_name"))
        if slotname not in byname:
            raise RuntimeError("Unknown imported material slot " + slotname + " in " + str([s.get_editor_property("imported_material_slot_name") for s in slots]))
        slot.set_editor_property("material_interface", byname[slotname])
        slot.set_editor_property("material_slot_name", slotname)
    mesh.set_editor_property("materials", slots)
    mesh.set_editor_property("physics_asset", None)
    build = S.get_lod_build_settings(mesh, 0)
    build.set_editor_property("use_full_precision_u_vs", True)
    S.set_lod_build_settings(mesh, 0, build)
    if not S.regenerate_lod(mesh, 3, False, False):
        raise RuntimeError("Cannot allocate hat LOD models")
    factory = u.DataAssetFactory()
    factory.set_editor_property("data_asset_class", u.SkeletalMeshLODSettings)
    policy = u.load_asset(path + "_LODPolicy") or A.create_asset(name + "_LODPolicy", DEST, u.SkeletalMeshLODSettings, factory)
    groups = []
    for ratio, screen in ((1.0, 1.0), (0.55, 0.18), (0.25, 0.075)):
        group = u.SkeletalMeshLODGroupSettings()
        settings = group.get_editor_property("reduction_settings")
        for prop, value in dict(num_of_triangles_percentage=ratio, num_of_vert_percentage=ratio,
                                max_bones_per_vertex=4, lock_edges=True, enforce_bone_boundaries=True,
                                merge_coincident_vert_bones=False, welding_threshold=0.0,
                                recalc_normals=False).items():
            settings.set_editor_property(prop, value)
        group.set_editor_property("reduction_settings", settings)
        group.set_editor_property("screen_size", u.PerPlatformFloat(default=screen))
        groups.append(group)
    policy.set_editor_property("lod_groups", groups)
    save(policy)
    mesh.set_editor_property("lod_settings", policy)
    models = list(mesh.get_editor_property("source_models"))
    for i, model in enumerate(models):
        model.set_editor_property("reduction_settings", groups[min(i, 2)].get_editor_property("reduction_settings"))
    mesh.set_editor_property("source_models", models)
    if not S.regenerate_lod(mesh, 3, True, False):
        raise RuntimeError("Cannot create hat LODs")
    mesh.set_editor_property("positive_bounds_extension", u.Vector(4, 4, 3))
    mesh.set_editor_property("negative_bounds_extension", u.Vector(4, 4, 1))
    E.set_metadata_tag(mesh, "FieldHatSHA", sha)
    E.set_metadata_tag(mesh, "EquipmentDefinition", "ue_field_hat")
    save(mesh.skeleton)
    save(mesh)
    receipt.update(mesh=mesh.get_path_name(), skeleton=mesh.skeleton.get_path_name(), fbx_sha256=sha,
                   lod_count=S.get_lod_count(mesh),
                   material_slots=[str(s.material_slot_name) for s in slots])
    record()
    print("FIELD_HAT_SKELETAL_SAVED", flush=True)
    return mesh


def imported_fits(mesh, d):
    dm, status = G.copy_mesh_from_skeletal_mesh(
        mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError("Cannot resolve imported hat coordinate frame")
    bones = {str(b.name): b.world_transform.translation for b in u.GeometryScript_BoneWeights.get_all_bones_info(dm)[1]}
    names = ["BrimBackBase", "BrimLeft", "BrimBackEnd"]
    if not all(n in bones for n in names):
        names = ["HatRoot", "BrimBackBase", "BrimBackEnd"]
    if not all(n in bones for n in names):
        raise RuntimeError("Missing fit reference bones: " + str(list(bones)))
    source = [u.Vector(*d["bones"][n]["position"]) for n in names]
    actual = [bones[n] for n in names]
    K = u.MathLibrary
    scale = (actual[1] - actual[0]).length() / (source[1] - source[0]).length()
    authored = u.Transform(location=source[0], rotation=K.make_rot_from_xy(source[1] - source[0], source[2] - source[0]),
                           scale=u.Vector(1, 1, 1))
    imported = u.Transform(location=actual[0], rotation=K.make_rot_from_xy(actual[1] - actual[0], actual[2] - actual[0]),
                           scale=u.Vector(scale, scale, scale))
    correction = K.compose_transforms(K.invert_transform(imported), authored)
    fits = json.loads((SRC / "fit.json").read_text())["fits"]
    result = {}
    for key, fit in fits.items():
        pitch, yaw, roll = fit["rotation"]
        target = u.Transform(location=u.Vector(*fit["location"]), rotation=u.Rotator(pitch=pitch, yaw=yaw, roll=roll),
                             scale=u.Vector(*fit["scale"]))
        target = K.compose_transforms(correction, target)
        r = target.rotation.rotator()
        result[key] = dict(location=[target.translation.x, target.translation.y, target.translation.z],
                           rotation=[r.pitch, r.yaw, r.roll],
                           scale=[target.scale3d.x, target.scale3d.y, target.scale3d.z])
    receipt["imported_fit_frame"] = names
    receipt["imported_fit_positions"] = {n: [bones[n].x, bones[n].y, bones[n].z] for n in names}
    return result


def displays(mats, d):
    sys.path.insert(0, str(P / "Tools/BlueMageRobe"))
    io = module("field_dynamic_io", "Tools/BlueMageRobe/save_assets.py")
    static = module("field_static_io", "Tools/ChainmailPants/save_assets.py")
    static.DEST = DEST
    T = u.GeometryScript_MeshTransforms
    center = [(min(p[i] for p in d["positions"]) + max(p[i] for p in d["positions"])) * 0.5 for i in range(3)]
    E.make_directory(DEST + "/Pickups")
    E.make_directory(DEST + "/Icons")
    pickup = io.dynamic(d)
    T.translate_mesh(pickup, u.Vector(*[-v for v in center]))
    receipt["pickup"] = static.static(pickup, DEST + "/Pickups/SM_FieldHat_Pickup", mats)
    icon = io.dynamic(d)
    T.translate_mesh(icon, u.Vector(*[-v for v in center]))
    T.rotate_mesh(icon, u.Rotator(pitch=0, yaw=180, roll=0))
    receipt["icon"] = static.static(icon, DEST + "/Icons/SM_FieldHat_Icon", mats)
    task = u.AssetImportTask()
    task.filename = str(SRC / "ue_field_hat.png")
    task.destination_path = DEST + "/Icons"
    task.destination_name = "T_FieldHat_Icon"
    task.automated = True
    task.replace_existing = True
    task.save = False
    A.import_asset_tasks([task])
    tex = load(DEST + "/Icons/T_FieldHat_Icon")
    for prop, value in dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,
                            compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,
                            mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS, srgb=True).items():
        tex.set_editor_property(prop, value)
    save(tex)
    receipt["icon_texture"] = tex.get_path_name()
    record()


def main():
    if "-run=" not in u.SystemLibrary.get_command_line().lower():
        level = u.get_editor_subsystem(u.LevelEditorSubsystem)
        if level and level.is_in_play_in_editor():
            raise RuntimeError("Preserve assets during PIE")
    receipt["completed"] = False
    record()
    E.make_directory(DEST)
    d = json.loads((SRC / "Authored/hat.json").read_text(encoding="utf-8"))
    mats = create_materials(texture_assets())
    receipt["materials"] = [m.get_path_name() for m in mats]
    record()
    mesh = skeletal(mats, d)
    fits = imported_fits(mesh, d)
    displays(mats, d)
    sys.path.insert(0, str(P / "Tools/FieldHat"))
    from save_icon import apply_item
    item = dict(grid_w=2, grid_h=2, ue_icon="Icons/FieldHat20261019/ue_field_hat.png",
                ue_icon_pitch=0, ue_icon_yaw=-90, ue_icon_roll=0)
    apply_item("ue_field_hat", item)
    receipt.update(completed=True, source_triangles=len(d["triangles"]), fit=fits,
                   tip_bones=["BrimBackBase", "BrimBackMid", "BrimBackEnd"],
                   simulation="local_bounded_angular_spring", runtime_tested=False)
    record()
    print("FIELD_HAT_ASSETS_SAVED", flush=True)


if __name__ == "__main__":
    main()