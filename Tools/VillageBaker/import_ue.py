"""Build and save the baker on the native R4 mesh reference pose, including his cloth and cap."""
import gzip
import json
import os
from pathlib import Path
import sys

import unreal as u
sys.path.insert(0, str(Path(__file__).resolve().parent))
import surface_response

PROJECT = Path(__file__).resolve().parents[2]
SOURCE = PROJECT / "SourceAssets/VillageBaker"
HOST = Path(os.environ["BAKER_UE_HOST"])
DEST = "/Game/Characters/VillageBaker"
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
L = u.MaterialEditingLibrary
G = u.GeometryScript_AssetUtils
B = u.GeometryScript_BoneWeights
owned = []
sources = [SOURCE / "WardrobeR1/Textures", SOURCE / "CapR1", SOURCE / "AssemblyR1/Textures"]
pngs = {path.stem: path for directory in sources for path in directory.glob("*.png")}
textures = {}


def save(obj):
    if not obj or not obj.get_path_name().startswith(DEST + "/") or not E.save_loaded_asset(obj, False):
        raise RuntimeError(f"Could not save the baker package {obj}")
    package = obj.get_path_name().split(".")[0]
    if package not in owned:
        owned.append(package)
    return obj


def texture(name, kind):
    if name in textures:
        return textures[name]
    dest = DEST + "/Textures"
    obj = E.load_asset(dest + "/" + name) if E.does_asset_exist(dest + "/" + name) else None
    if not obj:
        task = u.AssetImportTask()
        task.filename = str(pngs[name])
        task.destination_path = dest
        task.destination_name = name
        task.automated = True
        task.save = False
        task.factory = u.TextureFactory()
        A.import_asset_tasks([task])
        obj = E.load_asset(dest + "/" + name)
    color = kind == "BC"
    normal = kind == "N"
    compression = u.TextureCompressionSettings
    obj.set_editor_property("compression_settings", compression.TC_DEFAULT if color else
                            compression.TC_NORMALMAP if normal else compression.TC_MASKS)
    obj.set_editor_property("srgb", color)
    obj.set_editor_property("lod_group", u.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP if normal else
                            u.TextureGroup.TEXTUREGROUP_CHARACTER)
    if normal:
        obj.set_editor_property("flip_green_channel", True)
    textures[name] = save(obj)
    return obj


def material(name):
    dest = DEST + "/Materials"
    path = dest + "/" + name
    mat = E.load_asset(path) if E.does_asset_exist(path) else None
    mat = mat or A.create_asset(name, dest, u.Material, u.MaterialFactoryNew())
    L.delete_all_material_expressions(mat)
    L.set_material_usage(mat, u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    slab = L.create_material_expression(mat, u.MaterialExpressionSubstrateShadingModels, 0, 0)
    if name == "M_VillageBaker_FaceHair_0":
        maps = {ch: "T_Baker_Head_0_" + ch for ch in ("BC", "N", "R", "M")}
    elif name == "M_VillageBaker_Neck":
        maps = {"BC": "T_Baker_Neck_BC", "N": "T_Baker_NativeNeck_N", "ORM": "T_Baker_NativeNeck_ORM"}
    elif name == "M_VillageBaker_CapLinen":
        maps = {"BC": "T_VillageBaker_Cap_BC", "N": "T_VillageBaker_Cap_N_GL", "ORM": "T_VillageBaker_Cap_ORM"}
    else:
        maps = {ch: "T_" + name[2:] + "_" + ch for ch in ("BC", "N", "ORM")}
    for i, (kind, filename) in enumerate(maps.items()):
        sample = L.create_material_expression(mat, u.MaterialExpressionTextureSample, -550, i * 240)
        sample.texture = texture(filename, kind)
        st = u.MaterialSamplerType
        sample.sampler_type = st.SAMPLERTYPE_COLOR if kind == "BC" else st.SAMPLERTYPE_NORMAL if kind == "N" else st.SAMPLERTYPE_MASKS
        pins = {"BC": [("RGB", "BaseColor")], "N": [("RGB", "Normal")], "ORM": [("G", "Roughness"), ("B", "Metallic")],
                "M": [("R", "Metallic")], "R": [("R", "Roughness")]}[kind]
        if kind == "ORM":
            L.connect_material_property(sample, "R", u.MaterialProperty.MP_AMBIENT_OCCLUSION)
        for channel, pin in pins:
            if not L.connect_material_expressions(sample, channel, slab, pin):
                raise RuntimeError(f"Cannot bind {filename} to {pin}")
    surface_response.connect(mat, slab)
    if not L.connect_material_property(slab, "", u.MaterialProperty.MP_FRONT_MATERIAL):
        raise RuntimeError("Cannot bind substrate surface " + name)
    L.recompile_material(mat)
    return save(mat)


def mesh_asset(data, r4, materials):
    lod = u.GeometryScriptMeshReadLOD()
    ref, status = G.copy_mesh_from_skeletal_mesh(r4, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), lod)
    if status != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError("Missing the native R4 reference pose")
    dm = u.DynamicMesh()
    points = [u.Vector(*v) for v in data.pop("p")]
    buffers = u.GeometryScriptSimpleMeshBuffers(vertices=points, normals=[u.Vector(*n) for n in data.pop("n")],
        uv0=[u.Vector2D(*uv) for uv in data.pop("uv")], triangles=[u.IntVector(*t) for t in data.pop("tri")])
    u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm, buffers, 0, True)
    B.copy_bones_from_mesh(ref, dm)
    B.mesh_create_bone_weights(dm)
    rigid = {}
    for i, row in enumerate(data.pop("w")):
        if len(row) == 1:
            bone = row[0][0]
            if bone not in rigid:
                rigid[bone] = [u.GeometryScriptBoneWeight(bone_index=bone, weight=1)]
            weights = rigid[bone]
        else:
            weights = [u.GeometryScriptBoneWeight(bone_index=b, weight=w) for b, w in row]
        B.set_vertex_bone_weights(dm, i, weights)
    values = u.GeometryScript_List.convert_array_to_index_list(data.pop("m"), u.GeometryScriptIndexType.MATERIAL_ID)
    methods = u.GeometryScript_Materials
    set_ids = next(getattr(methods, n) for n in dir(methods) if n.lower().replace("_", "") == "setalltrianglematerialids")
    set_ids(dm, values, True)
    opts = u.GeometryScriptCreateNewSkeletalMeshAssetOptions()
    opts.use_mesh_bone_proportions = True
    opts.enable_recompute_normals = False
    opts.enable_recompute_tangents = True
    opts.materials = materials
    mesh, status = u.GeometryScript_NewAssetUtils.create_new_skeletal_mesh_asset_from_mesh(
        dm, r4.skeleton, DEST + "/SK_VillageBaker_R1", opts)
    if status != u.GeometryScriptOutcomePins.SUCCESS or not mesh:
        raise RuntimeError("Cannot create the baker skeletal mesh")
    if data["correctives"]:
        morph_opts = u.GeometryScriptCopyMorphTargetToAssetOptions(overwrite_existing_target=True, emit_transaction=False, copy_normals=False)
        for name, deltas in data["correctives"].items():
            modified = list(points)
            for i, x, y, z in deltas:
                modified[i] = points[i] + u.Vector(x, y, z)
            u.GeometryScript_MeshEdits.set_all_mesh_vertex_positions(dm, u.GeometryScript_List.convert_array_to_vector_list(modified))
            _, status = G.copy_morph_target_to_skeletal_mesh(dm, mesh, name, morph_opts, u.GeometryScriptMeshWriteLOD(lod_index=0))
            if status != u.GeometryScriptOutcomePins.SUCCESS:
                raise RuntimeError("Could not store baker corrective " + name)
        src_graph = r4.get_editor_property("post_process_anim_blueprint").get_path_name().split(".")[0]
        graph_path = DEST + "/ABP_Baker_R4_Correctives"
        graph = E.load_asset(graph_path) if E.does_asset_exist(graph_path) else E.duplicate_asset(src_graph, graph_path)
        try:
            graph.set_editor_property("preview_skeletal_mesh", mesh)
        except Exception:
            pass  # Some engine builds keep this editor-only field private.
        save(graph)
        mesh.set_editor_property("post_process_anim_blueprint", E.load_blueprint_class(graph_path))
    policy_name = "DA_BakerLOD"
    factory = u.DataAssetFactory()
    factory.set_editor_property("data_asset_class", u.SkeletalMeshLODSettings)
    policy = A.create_asset(policy_name, DEST, u.SkeletalMeshLODSettings, factory)
    groups = []
    for ratio, screen in ((1., 1.), (.43, .35), (.17, .18), (.055, .065)):
        item = u.SkeletalMeshLODGroupSettings()
        reduction = item.get_editor_property("reduction_settings")
        for key, value in dict(num_of_triangles_percentage=ratio, num_of_vert_percentage=ratio, max_bones_per_vertex=8,
                               lock_edges=True, enforce_bone_boundaries=True, merge_coincident_vert_bones=False,
                               welding_threshold=0., recalc_normals=False, remap_morph_targets=True).items():
            reduction.set_editor_property(key, value)
        item.set_editor_property("reduction_settings", reduction)
        item.set_editor_property("screen_size", u.PerPlatformFloat(default=screen))
        groups.append(item)
    policy.set_editor_property("lod_groups", groups)
    mesh.set_editor_property("lod_settings", save(policy))
    u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).regenerate_lod(mesh, 4, True, False)
    return save(mesh)


with gzip.open(HOST / "geometry.json.gz", "rt", encoding="utf-8") as stream:
    data = json.load(stream)
r4_info = json.loads((PROJECT / "SourceAssets/JasonStrong20261117/R4_PoseRefined/variant_saved.json").read_text())
r4 = E.load_asset(r4_info["asset"])
materials = {slot: material(slot) for slot in data["slots"]}
mesh = mesh_asset(data, r4, materials)
(HOST / "saved.json").write_text(json.dumps({"mesh": mesh.get_path_name(), "skeleton": mesh.skeleton.get_path_name(),
    "packages": owned, "correctives": list(data["correctives"]), "material_slots": list(materials)}, indent=2))
