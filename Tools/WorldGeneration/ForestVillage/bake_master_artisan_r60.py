"""Bake ALL 3 R60 watertight armpit-repaired workwear SkeletalMeshes in isolated Stage UE 5.8,
preserving 100% of existing material interfaces & regenerating 3 LODs:
  - SK_Carpenter_Workwear (Role 0 SplitLog/ChopTree lumberjack)
  - SK_MasterArtisan_Workwear (Role 1 SawLog lumberjack + Village Master Artisan)
  - SK_Smith_Outfit (Role 2 Carrier/Wagon lumberjack + Village Blacksmith)
"""
import gzip
import json
from pathlib import Path
import unreal as ue

BODY_PATH = "/Game/Characters/VillageBlacksmithNPC20261118/SK_Smith_Body"
OUT_RECEIPT = Path("F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillOps-R60/Workwear/baked_all_workwear_r60.json")

TARGETS = [
    (
        "SK_Carpenter_Workwear",
        "/Game/Characters/VillageCarpenterNPC/Outfit/SK_Carpenter_Workwear",
        Path("F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillOps-R59/Workwear/carpenter_workwear_r59.json.gz"),
        "smith_fmt",
        True,   # has wear_uv on UV1
    ),
    (
        "SK_Smith_Outfit",
        "/Game/Characters/VillageBlacksmithNPC20261118/SK_Smith_Outfit",
        Path("F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillOps-R59/Workwear/smith_outfit_r59.json.gz"),
        "smith_fmt",
        False,  # UV0 only
    ),
    (
        "SK_MasterArtisan_Workwear",
        "/Game/Characters/VillageMasterArtisan/SK_MasterArtisan_Workwear",
        Path("F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillOps-R60/Workwear/master_artisan_workwear_r60.json.gz"),
        "artisan_fmt",
        False,  # UV0 only
    ),
]

geo = ue.GeometryScript_AssetUtils
binding = ue.GeometryScript_BoneWeights
mat_api = ue.GeometryScript_Materials
list_api = ue.GeometryScript_List
skel_ed = ue.get_editor_subsystem(ue.SkeletalMeshEditorSubsystem)
lib = ue.EditorAssetLibrary

body = ue.load_asset(BODY_PATH)
if not body:
    raise RuntimeError("Missing SK_Smith_Body: " + BODY_PATH)

ref_dm, ref_res = geo.copy_mesh_from_skeletal_mesh(
    body,
    ue.DynamicMesh(),
    ue.GeometryScriptCopyMeshFromAssetOptions(),
    ue.GeometryScriptMeshReadLOD(lod_index=0),
)
if ref_res != ue.GeometryScriptOutcomePins.SUCCESS:
    raise RuntimeError("Failed reading SK_Smith_Body reference bones")

set_all_mats = next(
    getattr(mat_api, n) for n in dir(mat_api) if n.lower().replace("_", "") == "setalltrianglematerialids"
)

baked = {}
for label, asset_path, json_gz, fmt, has_wear_uv in TARGETS:
    target = ue.load_asset(asset_path)
    if not target:
        raise RuntimeError("Missing target SkeletalMesh: " + asset_path)

    orig_mats = list(target.get_editor_property("materials"))
    orig_interfaces = [m.material_interface for m in orig_mats]
    orig_slot_names = [str(m.material_slot_name) for m in orig_mats]

    with gzip.open(json_gz, "rt", encoding="utf-8") as fh:
        data = json.load(fh)

    if fmt == "artisan_fmt":
        if len(data["materials"]) != len(orig_interfaces):
            raise RuntimeError(f"{label}: slot mismatch data={len(data['materials'])} vs asset={len(orig_interfaces)}")
        points = [ue.Vector(*pt) for pt in data["p"]]
        normals = [ue.Vector(*nm) for nm in data["n"]]
        uvs = [ue.Vector2D(*uv) for uv in data["uv"]]
        faces = [ue.IntVector(*tri) for tri in data["tri"]]
        weights = data["w"]
        tri_mats = data["m"]
        wear_uvs = None
    else:
        if len(data["material_slots"]) != len(orig_interfaces):
            raise RuntimeError(f"{label}: slot mismatch data={len(data['material_slots'])} vs asset={len(orig_interfaces)}")
        points, normals, uvs, wear_uvs_list, weights, faces = [], [], [], [], [], []
        indices = {}
        wear_arr = data.get("wear_uv") if has_wear_uv else None
        for i, tri in enumerate(data["triangles"]):
            out_face = []
            for j, v in enumerate(tri):
                uv = data["uv"][i][j]
                n = data["normals"][i][j]
                key = (v, round(uv[0], 5), round(uv[1], 5), round(n[0], 5), round(n[1], 5), round(n[2], 5))
                if key not in indices:
                    indices[key] = len(points)
                    points.append(ue.Vector(*data["positions"][v]))
                    normals.append(ue.Vector(*n))
                    uvs.append(ue.Vector2D(*uv))
                    if wear_arr is not None:
                        wear_uvs_list.append(ue.Vector2D(*wear_arr[v]))
                    weights.append(data["weights"][v])
                out_face.append(indices[key])
            faces.append(ue.IntVector(*out_face))
        tri_mats = data["triangle_materials"]
        wear_uvs = wear_uvs_list if wear_arr is not None else None

    dm = ue.DynamicMesh()
    if wear_uvs is not None:
        buffers = ue.GeometryScriptSimpleMeshBuffers(
            vertices=points, normals=normals, uv0=uvs, uv1=wear_uvs, triangles=faces
        )
    else:
        buffers = ue.GeometryScriptSimpleMeshBuffers(
            vertices=points, normals=normals, uv0=uvs, triangles=faces
        )
    ue.GeometryScript_MeshEdits.append_buffers_to_mesh(dm, buffers, 0, True)
    binding.copy_bones_from_mesh(ref_dm, dm)
    binding.mesh_create_bone_weights(dm)
    for i, row in enumerate(weights):
        binding.set_vertex_bone_weights(
            dm, i, [ue.GeometryScriptBoneWeight(bone_index=int(b), weight=float(w)) for b, w in row if w > 0.0]
        )

    set_all_mats(
        dm,
        list_api.convert_array_to_index_list(tri_mats, ue.GeometryScriptIndexType.MATERIAL_ID),
        True,
    )

    settings = ue.GeometryScriptCopyMeshToAssetOptions(
        replace_materials=True,
        new_materials=orig_interfaces,
        new_material_slot_names=orig_slot_names,
        enable_recompute_normals=False,
        enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=ue.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON,
    )
    _, res = geo.copy_mesh_to_skeletal_mesh(dm, target, settings, ue.GeometryScriptMeshWriteLOD(lod_index=0))
    if res != ue.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError(f"copy_mesh_to_skeletal_mesh failed on {label}")

    if not skel_ed.regenerate_lod(target, 3, True, False):
        raise RuntimeError(f"regenerate_lod failed on {label}")

    if not lib.save_loaded_asset(target, False):
        raise RuntimeError(f"save_loaded_asset failed on {label}")

    baked[label] = {
        "asset": target.get_path_name(),
        "verts": len(points),
        "tris": len(faces),
        "lods": int(skel_ed.get_lod_count(target)),
        "slots": orig_slot_names,
    }
    ue.log(f"[R60-WORKWEAR] Saved {label}: verts={len(points)}, tris={len(faces)}, lods={baked[label]['lods']}")

OUT_RECEIPT.parent.mkdir(parents=True, exist_ok=True)
OUT_RECEIPT.write_text(json.dumps(baked, indent=2), encoding="utf-8")
ue.log("R60_ALL_WORKWEAR_BAKE_OK")
