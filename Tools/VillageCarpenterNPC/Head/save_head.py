"""UE commandlet authoring for the carpenter's R4-compatible skeletal head and PBR materials."""
import gzip
import json
from pathlib import Path

import unreal as u


PROJECT = Path(__file__).resolve().parents[3]
WORK = PROJECT / "SourceAssets/VillageCarpenterNPC/Head"
DEST = "/Game/Characters/VillageCarpenterNPC/Head"
SMITH = "/Game/Characters/VillageBlacksmithNPC20261118"
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
L = u.MaterialEditingLibrary
P = u.MaterialProperty
packages = []


def save(asset):
    path = asset.get_path_name().split(".")[0]
    if not path.startswith(DEST + "/") or not E.save_loaded_asset(asset, False):
        raise RuntimeError("Could not save owned package " + path)
    if path not in packages:
        packages.append(path)
    return asset


def texture(name, compression, group, srgb=False, flip_green=False):
    task = u.AssetImportTask()
    task.filename = str(WORK / (name + ".png"))
    task.destination_path = DEST + "/Textures"
    task.automated = True
    task.replace_existing = True
    task.save = False
    A.import_asset_tasks([task])
    obj = u.load_asset(task.destination_path + "/" + name)
    if not obj:
        raise RuntimeError("Texture import failed for " + name)
    obj.set_editor_property("compression_settings", compression)
    obj.set_editor_property("lod_group", group)
    obj.set_editor_property("srgb", srgb)
    if flip_green:
        obj.set_editor_property("flip_green_channel", True)
    return save(obj)


def make_material(name, albedo, normal, masks=None, neck_tint=None):
    m = u.load_asset(DEST + "/" + name) or A.create_asset(name, DEST, u.Material, u.MaterialFactoryNew())
    L.delete_all_material_expressions(m)
    m.set_editor_property("shading_model", u.MaterialShadingModel.MSM_SUBSURFACE)
    L.set_material_usage(m, u.MaterialUsage.MATUSAGE_SKELETAL_MESH)

    def node(cls, **properties):
        obj = L.create_material_expression(m, cls)
        for key, value in properties.items():
            obj.set_editor_property(key, value)
        return obj

    def link(src, channel, dst, pin):
        if not L.connect_material_expressions(src, channel, dst, pin):
            raise RuntimeError("Cannot connect material input " + pin)

    def output(src, channel, prop):
        if not L.connect_material_property(src, channel, prop):
            raise RuntimeError("Cannot connect material output " + str(prop))

    rgb = node(u.MaterialExpressionTextureSample, texture=albedo, sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    diffuse, channel = rgb, "RGB"
    if neck_tint is not None:
        tint = node(u.MaterialExpressionConstant3Vector, constant=u.LinearColor(*neck_tint, 1.))
        corrected = node(u.MaterialExpressionMultiply)
        link(rgb, "RGB", corrected, "A")
        link(tint, "", corrected, "B")
        rest = node(u.MaterialExpressionVertexInterpolator)
        link(node(u.MaterialExpressionPreSkinnedPosition), "", rest, "")
        z = node(u.MaterialExpressionComponentMask, r=False, g=False, b=True, a=False)
        link(rest, "", z, "")
        ramp = node(u.MaterialExpressionSmoothStep, const_min=150.4, const_max=154.5)
        link(z, "", ramp, "Value")
        diffuse, channel = node(u.MaterialExpressionLinearInterpolate), ""
        link(rgb, "RGB", diffuse, "A")
        link(corrected, "", diffuse, "B")
        link(ramp, "", diffuse, "Alpha")
    output(diffuse, channel, P.MP_BASE_COLOR)
    output(node(u.MaterialExpressionTextureSample, texture=normal, sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL),
           "RGB", P.MP_NORMAL)
    scatter = node(u.MaterialExpressionMultiply)
    link(diffuse, channel, scatter, "A")
    link(node(u.MaterialExpressionConstant3Vector, constant=u.LinearColor(.15, .085, .055, 1)), "", scatter, "B")
    if masks:
        mask = node(u.MaterialExpressionTextureSample, texture=masks, sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        output(mask, "G", P.MP_ROUGHNESS)
        output(mask, "B", P.MP_METALLIC)
        scatter_skin = node(u.MaterialExpressionMultiply)
        link(scatter, "", scatter_skin, "A")
        link(mask, "R", scatter_skin, "B")
        scatter = scatter_skin
        for prop, hair, skin in ((P.MP_SPECULAR, .24, .32), (P.MP_OPACITY, 1., .7)):
            mix = node(u.MaterialExpressionLinearInterpolate, const_a=hair, const_b=skin)
            link(mask, "R", mix, "Alpha")
            output(mix, "", prop)
    else:
        for prop, value in ((P.MP_ROUGHNESS, .53), (P.MP_SPECULAR, .32), (P.MP_OPACITY, .70)):
            output(node(u.MaterialExpressionConstant, r=value), "", prop)
    output(scatter, "", P.MP_SUBSURFACE_COLOR)
    L.recompile_material(m)
    return save(m)


def make_lod_policy():
    factory = u.DataAssetFactory()
    factory.set_editor_property("data_asset_class", u.SkeletalMeshLODSettings)
    name = "DA_Carpenter_Head_LOD"
    lods = u.load_asset(DEST + "/" + name) or A.create_asset(name, DEST, u.SkeletalMeshLODSettings, factory)
    groups = []
    for proportion, size in ((1., 1.), (.47, .23), (.19, .08)):
        settings = u.SkeletalMeshLODGroupSettings()
        reduction = settings.get_editor_property("reduction_settings")
        for key, value in {"num_of_triangles_percentage": proportion, "num_of_vert_percentage": proportion,
                           "max_bones_per_vertex": 8, "lock_edges": True, "enforce_bone_boundaries": True,
                           "merge_coincident_vert_bones": False, "welding_threshold": 0.,
                           "recalc_normals": False}.items():
            reduction.set_editor_property(key, value)
        settings.set_editor_property("reduction_settings", reduction)
        settings.set_editor_property("screen_size", u.PerPlatformFloat(default=size))
        groups.append(settings)
    lods.set_editor_property("lod_groups", groups)
    return save(lods)


def make_mesh(face, neck):
    with gzip.open(WORK / "fitted.json.gz", "rt", encoding="utf-8") as data:
        mesh = json.load(data)
    source = u.load_asset(SMITH + "/SK_Smith_Body")
    ref, result = u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(
        source, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if result != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError("Cannot obtain the smith body's R4 reference pose")
    dm = u.DynamicMesh()
    buffers = u.GeometryScriptSimpleMeshBuffers(
        vertices=[u.Vector(*v) for v in mesh["p"]], normals=[u.Vector(*v) for v in mesh["n"]],
        uv0=[u.Vector2D(*v) for v in mesh["uv"]], triangles=[u.IntVector(*v) for v in mesh["tri"]])
    u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm, buffers, 0, True)
    bones = u.GeometryScript_BoneWeights
    bones.copy_bones_from_mesh(ref, dm)
    bones.mesh_create_bone_weights(dm)
    singles = {}
    for index, row in enumerate(mesh["w"]):
        if len(row) == 1:
            idx = row[0][0]
            if idx not in singles:
                singles[idx] = [u.GeometryScriptBoneWeight(bone_index=idx, weight=1.)]
            weights = singles[idx]
        else:
            weights = [u.GeometryScriptBoneWeight(bone_index=i, weight=w) for i, w in row]
        bones.set_vertex_bone_weights(dm, index, weights)
    material_ids = u.GeometryScript_List.convert_array_to_index_list(mesh["m"], u.GeometryScriptIndexType.MATERIAL_ID)
    library = u.GeometryScript_Materials
    setter = next(getattr(library, name) for name in dir(library) if name.replace("_", "").lower() == "setalltrianglematerialids")
    setter(dm, material_ids, True)
    opts = u.GeometryScriptCreateNewSkeletalMeshAssetOptions()
    opts.use_mesh_bone_proportions = True
    opts.enable_recompute_normals = False
    opts.enable_recompute_tangents = True
    opts.materials = {"CarpenterFace": face, "CarpenterNeck": neck}
    path = DEST + "/SK_Carpenter_Head"
    head, result = u.GeometryScript_NewAssetUtils.create_new_skeletal_mesh_asset_from_mesh(dm, source.skeleton, path, opts)
    if result != u.GeometryScriptOutcomePins.SUCCESS or not head:
        raise RuntimeError("Could not create " + path)
    head.set_editor_property("lod_settings", make_lod_policy())
    if not u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).regenerate_lod(head, 3, True, False):
        raise RuntimeError("Could not generate the head LODs")
    return save(head)


def main():
    fit = json.loads((WORK / "fit.json").read_text())
    comp = u.TextureCompressionSettings
    grp = u.TextureGroup
    color = texture("T_Carpenter_Head_BC", comp.TC_DEFAULT, grp.TEXTUREGROUP_CHARACTER, srgb=True)
    normal = texture("T_Carpenter_Head_N", comp.TC_NORMALMAP, grp.TEXTUREGROUP_CHARACTER_NORMAL_MAP, flip_green=True)
    masks = texture("T_Carpenter_Head_SRM", comp.TC_MASKS, grp.TEXTUREGROUP_CHARACTER_SPECULAR)
    face = make_material("M_Carpenter_FaceHair", color, normal, masks=masks)
    neck = make_material("M_Carpenter_Neck", u.load_asset(SMITH + "/HeadParts/Textures/T_Smith_Skin_head_BC"),
                         u.load_asset("/Game/AsianMale_Jason/Texture/T_Head_LOD2_N"), neck_tint=fit["upper_neck_linear_tint"])
    head = make_mesh(face, neck)
    (WORK / "saved.json").write_text(json.dumps({"head": head.get_path_name(), "skeleton": head.skeleton.get_path_name(),
                                                "packages": packages, "lod_count_requested": 3}, indent=2))


main()
