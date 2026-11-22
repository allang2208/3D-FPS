"""Save the production head with the resident body bind pose and the Meshy skin weights."""
import gzip
import json
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[2] / "SourceAssets/VillageGunsmith"
DEST = "/Game/Characters/VillageGunsmith"
SMITH = "/Game/Characters/VillageBlacksmithNPC20261118"
assets = u.EditorAssetLibrary
tools = u.AssetToolsHelpers.get_asset_tools()
editor = u.MaterialEditingLibrary
packages = []


def save(obj):
    path = obj.get_path_name().split(".")[0]
    if not path.startswith(DEST + "/") or not assets.save_loaded_asset(obj, False):
        raise RuntimeError("Cannot save " + path)
    packages.append(path)
    return obj


def texture(filename, kind):
    src = Path(filename)
    name = src.stem.replace("Baker_Native", "Gunsmith_Native")
    task = u.AssetImportTask()
    task.filename = str(src)
    task.destination_path = DEST + "/Textures"
    task.destination_name = name
    task.factory = u.TextureFactory()
    task.automated = True
    tex = assets.load_asset(task.destination_path + "/" + name) if assets.does_asset_exist(task.destination_path + "/" + name) else None
    if tex is None:
        tools.import_asset_tasks([task])
        tex = assets.load_asset(task.destination_path + "/" + name)
    if not tex:
        raise RuntimeError("No imported texture for " + str(src))
    tex.set_editor_property("srgb", kind == "BC")
    tex.set_editor_property("compression_settings", u.TextureCompressionSettings.TC_DEFAULT if kind == "BC" else
                            u.TextureCompressionSettings.TC_NORMALMAP if kind == "N" else u.TextureCompressionSettings.TC_MASKS)
    tex.set_editor_property("lod_group", u.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP if kind == "N"
                            else u.TextureGroup.TEXTUREGROUP_CHARACTER)
    if kind == "N":
        tex.set_editor_property("flip_green_channel", True)
    return save(tex)


def material(name, maps):
    path = DEST + "/" + name
    mat = assets.load_asset(path) if assets.does_asset_exist(path) else tools.create_asset(name, DEST, u.Material, u.MaterialFactoryNew())
    editor.delete_all_material_expressions(mat)
    editor.set_material_usage(mat, u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    slab = editor.create_material_expression(mat, u.MaterialExpressionSubstrateShadingModels)
    spec = editor.create_material_expression(mat, u.MaterialExpressionConstant)
    spec.set_editor_property("r", .32)
    editor.connect_material_expressions(spec, "", slab, "Specular")
    for kind, filename in maps.items():
        slot = {"BC": "BaseColor", "N": "Normal", "R": "Roughness", "M": "Metallic"}[kind]
        node = editor.create_material_expression(mat, u.MaterialExpressionTextureSample)
        node.texture = texture(filename, kind)
        sampler = u.MaterialSamplerType
        node.sampler_type = sampler.SAMPLERTYPE_COLOR if kind == "BC" else sampler.SAMPLERTYPE_NORMAL if kind == "N" else sampler.SAMPLERTYPE_MASKS
        if not editor.connect_material_expressions(node, "RGB" if kind in ("BC", "N") else "R", slab, slot):
            raise RuntimeError("Cannot bind " + slot)
    if not editor.connect_material_property(slab, "", u.MaterialProperty.MP_FRONT_MATERIAL):
        raise RuntimeError("Cannot bind Substrate")
    editor.recompile_material(mat)
    return save(mat)


def main():
    cfg = json.loads((ROOT / "Assembly/setup.json").read_text())
    materials = {}
    for i, maps in enumerate(cfg["materials"]):
        name = "M_Gunsmith_Neck" if i == len(cfg["materials"]) - 1 else "M_Gunsmith_FaceHair_" + str(i)
        materials[name] = material(name, maps)
    with gzip.open(ROOT / "Assembly/bound_head.json.gz", "rt") as stream:
        data = json.load(stream)
    body = assets.load_asset(SMITH + "/SK_Smith_Body")
    ref, status = u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(body, u.DynamicMesh(),
        u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError("Cannot read the production resident bind pose")
    dm = u.DynamicMesh()
    buffers = u.GeometryScriptSimpleMeshBuffers(vertices=[u.Vector(*p) for p in data.pop("p")],
        normals=[u.Vector(*n) for n in data.pop("n")], uv0=[u.Vector2D(*uv) for uv in data.pop("uv")],
        triangles=[u.IntVector(*t) for t in data.pop("tri")])
    u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm, buffers, 0, True)
    bones = u.GeometryScript_BoneWeights
    bones.copy_bones_from_mesh(ref, dm)
    bones.mesh_create_bone_weights(dm)
    for i, row in enumerate(data.pop("w")):
        bones.set_vertex_bone_weights(dm, i, [u.GeometryScriptBoneWeight(bone_index=j, weight=w) for j, w in row])
    ids = u.GeometryScript_List.convert_array_to_index_list(data.pop("m"), u.GeometryScriptIndexType.MATERIAL_ID)
    methods = u.GeometryScript_Materials
    getattr(methods, next(n for n in dir(methods) if n.lower().replace("_", "") == "setalltrianglematerialids"))(dm, ids, True)
    opts = u.GeometryScriptCreateNewSkeletalMeshAssetOptions(use_mesh_bone_proportions=True,
        enable_recompute_normals=False, enable_recompute_tangents=True, materials=materials)
    mesh, result = u.GeometryScript_NewAssetUtils.create_new_skeletal_mesh_asset_from_mesh(
        dm, body.skeleton, DEST + "/SK_Gunsmith_Head", opts)
    if result != u.GeometryScriptOutcomePins.SUCCESS or not mesh:
        raise RuntimeError("Cannot save the bound gunsmith head")
    mesh.set_editor_property("lod_settings", assets.load_asset(SMITH + "/HeadParts/DA_Smith_FaceLOD"))
    u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).regenerate_lod(mesh, 3, True, False)
    save(mesh)
    (ROOT / "Host/saved.json").write_text(json.dumps({"mesh": mesh.get_path_name(),
        "skeleton": mesh.skeleton.get_path_name(), "packages": packages}, indent=2))


main()
