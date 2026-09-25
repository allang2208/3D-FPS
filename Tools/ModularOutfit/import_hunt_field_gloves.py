"""Save native-bound hunt gloves and publish only the brown field-glove recipe."""
import hashlib
import json
import time
from pathlib import Path

import unreal as u

PROJECT = Path("D:/FPS3D/FPSGAME")
ROOT = PROJECT / "SourceAssets/ModularOutfit20260925/HuntFieldGlovesV1"
BARE = PROJECT / "SourceAssets/ModularOutfit20260925/BarePalmV7"
DEST = "/Game/Characters/ModularOutfit20260924/HuntFieldGlovesV1"
CONFIG = PROJECT / "Content/ColdSteelData/modular_outfits.json"
ITEM = "ue_field_gloves"
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
G = u.GeometryScript_AssetUtils
B = u.GeometryScript_BoneWeights
S = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
SAVE = u.EditorLoadingAndSavingUtils
RECEIPTS = ROOT / "Saved"
RECEIPTS.mkdir(parents=True, exist_ok=True)


def play_world():
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    if not world:
        return None
    name = world.get_name()
    if "UEDPIE" in name or name.startswith("UEDPIE") or "PIE_" in name:
        return world
    return None


world = play_world()
if world:
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
    for _ in range(80):
        time.sleep(0.25)
        if not play_world():
            break
    else:
        raise RuntimeError("Finish play before saving hunt glove equipment")


def load(path):
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError("Missing glove dependency: " + path)
    return asset


def save(asset):
    asset.modify()
    try:
        asset.post_edit_change()
    except Exception:
        pass
    pkg = asset.get_outer()
    for _ in range(12):
        if SAVE.save_packages([pkg], False):
            return
        if E.save_loaded_asset(asset, False) or E.save_asset(asset.get_path_name(), False):
            return
        time.sleep(0.25)
    raise RuntimeError("Cannot save hunt gloves: " + asset.get_path_name())


material = load("/Game/Characters/ModularOutfit20260924/Materials/M_FieldGloves_Brown")
initial = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
previous = {}
published = {}
manifest = json.loads((ROOT / "manifest.json").read_text())
for entry in manifest:
    name = entry["profile"]
    raw = Path(entry["authored"]).read_bytes()
    data = json.loads(raw)
    sha = hashlib.sha256(raw).hexdigest()
    profile = initial["profiles"][data["source"]]
    if profile.get("native_bare_skin") != data["base_mesh"] or profile.get("glove_covers") != [2]:
        raise RuntimeError("Bare hand base or coverage changed during fitting: " + name)
    if hashlib.sha256((BARE / "Authored" / f"{name}.json").read_bytes()).hexdigest() != data["bare_authored_sha256"]:
        raise RuntimeError("Bare hand authoring changed during fitting: " + name)
    previous[name] = {
        "source": data["source"],
        "item_mesh": initial["items"][ITEM]["rig_meshes"].get(name),
    }
    receipt_file = RECEIPTS / f"{name}.json"
    if receipt_file.exists():
        receipt = json.loads(receipt_file.read_text())
        if receipt["authored_sha256"] == sha and E.does_asset_exist(receipt["mesh"]):
            published[name] = receipt["mesh"]
            continue
    print("HUNT_GLOVES_IMPORT_BEGIN", name, flush=True)
    source = load(data["binding_source"])
    native, status = G.copy_mesh_from_skeletal_mesh(source, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError("Cannot read native glove binding: " + name)
    _, bones = B.get_all_bones_info(native)
    bone_ids = {str(b.name): b.index for b in bones}
    vertices, normals, uv0, weights, triangles = [], [], [], [], []
    lookup = {}
    for fi, face in enumerate(data["triangles"]):
        row = []
        for corner, vi in enumerate(face):
            uv = data["uv"][fi][corner]
            normal = data["normals"][fi][corner]
            key = (vi, *[round(v, 7) for v in (*uv, *normal)])
            if key not in lookup:
                lookup[key] = len(vertices)
                vertices.append(u.Vector(*data["positions"][vi]))
                normals.append(u.Vector(*normal))
                uv0.append(u.Vector2D(*uv))
                weights.append(data["weights"][vi])
            row.append(lookup[key])
        triangles.append(u.IntVector(*row))
    dm = u.DynamicMesh()
    u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm, u.GeometryScriptSimpleMeshBuffers(
        vertices=vertices, normals=normals, uv0=uv0, triangles=triangles), 0, True)
    B.copy_bones_from_mesh(native, dm)
    B.mesh_create_bone_weights(dm)
    for vi, bindings in enumerate(weights):
        B.set_vertex_bone_weights(dm, vi, [u.GeometryScriptBoneWeight(bone_index=bone_ids[n], weight=w) for n, w in bindings.items()])
    folder = DEST + "/" + name
    mesh_name = "SK_" + name + "_HuntFieldGlovesV1"
    mesh = u.load_asset(folder + "/" + mesh_name)
    if not mesh:
        E.make_directory(folder)
        mesh = A.duplicate_asset(mesh_name, folder, source)
    options = u.GeometryScriptCopyMeshToAssetOptions(
        replace_materials=True, new_materials=[material], new_material_slot_names=["HuntFieldLeather"],
        enable_recompute_normals=False, enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _, status = G.copy_mesh_to_skeletal_mesh(dm, mesh, options, u.GeometryScriptMeshWriteLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError("Cannot build hunt glove mesh: " + name)
    try:
        mesh.post_edit_change()
    except Exception:
        pass
    mesh.set_editor_property("physics_asset", None)
    build = S.get_lod_build_settings(mesh, 0)
    build.set_editor_property("use_full_precision_u_vs", True)
    S.set_lod_build_settings(mesh, 0, build)
    E.set_metadata_tag(mesh, "SourceContract", data["contract"])
    save(mesh)
    lod_ok = u.FPSModularOutfitComponent.configure_outfit_lods(mesh) and S.regenerate_lod(mesh, 3, True, False)
    if lod_ok:
        save(mesh)
    else:
        print("HUNT_GLOVES_LOD0_ONLY", name, flush=True)
    receipt = {"profile": name, "mesh": mesh.get_path_name(), "authored_sha256": sha,
               "base_mesh": data["base_mesh"], "native_skeleton": data["skeleton"],
               "new_animations": 0, "runtime_tested": False}
    receipt_file.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    published[name] = mesh.get_path_name()
    print("HUNT_GLOVES_SAVED", name, mesh.get_path_name(), flush=True)

config = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
for name, prior in previous.items():
    if config["profiles"][prior["source"]].get("native_bare_skin") != initial["profiles"][prior["source"]]["native_bare_skin"]:
        raise RuntimeError("Bare hand base changed during import: " + name)
    meshes = config["items"][ITEM]["rig_meshes"]
    if meshes.get(name) not in (prior["item_mesh"], published[name]):
        raise RuntimeError("Equipment recipe changed during import: " + ITEM + "/" + name)
    meshes[name] = published[name]
backup = ROOT / "previous-glove-paths.json"
if not backup.exists():
    backup.write_text(json.dumps(previous, indent=2) + "\n", encoding="utf-8")
CONFIG.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "published.json").write_text(json.dumps({
    "profiles": published, "items": [ITEM], "runtime_tested": False, "new_animations": 0,
}, indent=2) + "\n", encoding="utf-8")
print("HUNT_GLOVES_PUBLISHED", len(published), flush=True)
