"""Save Body hunt gloves and point only the brown glove item at them."""
import json
import time
from pathlib import Path

import unreal as u

PROJECT = Path("D:/FPS3D/FPSGAME")
ROOT = PROJECT / "SourceAssets/ModularOutfit20260925/HuntFieldGlovesV1"
DEST = "/Game/Characters/ModularOutfit20260924/HuntFieldGlovesV1/Body"
CONFIG = PROJECT / "Content/ColdSteelData/modular_outfits.json"
ITEM = "ue_field_gloves"
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
G = u.GeometryScript_AssetUtils
B = u.GeometryScript_BoneWeights
S = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
SAVE = u.EditorLoadingAndSavingUtils


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
        raise RuntimeError("Finish play before saving Body hunt gloves")

data = json.loads((ROOT / "Authored/Body.json").read_text(encoding="utf-8-sig"))
material = u.load_asset("/Game/Characters/ModularOutfit20260924/Materials/M_FieldGloves_Brown")
source = u.load_asset(data["binding_source"])
if not material or not source:
    raise RuntimeError("Missing Body glove material or skeleton source")
native, status = G.copy_mesh_from_skeletal_mesh(
    source, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
if status != u.GeometryScriptOutcomePins.SUCCESS:
    raise RuntimeError("Cannot read Body skeleton")
_, bones = B.get_all_bones_info(native)
bone_ids = {str(b.name): b.index for b in bones}
vertices, normals, uv0, weights, triangles = [], [], [], [], []
lookup = {}
for fi, face in enumerate(data["triangles"]):
    row = []
    for corner, vi in enumerate(face):
        uv = data["uv"][fi][corner]
        normal = data["normals"][fi][corner]
        key = (vi, *uv, *normal)
        if key not in lookup:
            lookup[key] = len(vertices)
            vertices.append(u.Vector(*data["positions"][vi]))
            normals.append(u.Vector(*normal))
            uv0.append(u.Vector2D(*uv))
            weights.append(data["weights"][vi])
        row.append(lookup[key])
    triangles.append(u.IntVector(*row))
dm = u.DynamicMesh()
u.GeometryScript_MeshEdits.append_buffers_to_mesh(
    dm, u.GeometryScriptSimpleMeshBuffers(vertices=vertices, normals=normals, uv0=uv0, triangles=triangles), 0, True)
B.copy_bones_from_mesh(native, dm)
B.mesh_create_bone_weights(dm)
for vi, bindings in enumerate(weights):
    B.set_vertex_bone_weights(dm, vi, [
        u.GeometryScriptBoneWeight(bone_index=bone_ids[n], weight=w) for n, w in bindings.items() if n in bone_ids and w > 0])
E.make_directory(DEST)
name = "SK_Body_HuntFieldGlovesV1"
mesh = u.load_asset(DEST + "/" + name)
if not mesh:
    mesh = A.duplicate_asset(name, DEST, source)
options = u.GeometryScriptCopyMeshToAssetOptions(
    replace_materials=True, new_materials=[material], new_material_slot_names=["HuntFieldLeather"],
    enable_recompute_normals=False, enable_recompute_tangents=True,
    bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
_, status = G.copy_mesh_to_skeletal_mesh(dm, mesh, options, u.GeometryScriptMeshWriteLOD())
if status != u.GeometryScriptOutcomePins.SUCCESS:
    raise RuntimeError("Cannot build Body hunt gloves")
mesh.set_editor_property("physics_asset", None)
if not (SAVE.save_packages([mesh.get_outer()], False) or E.save_loaded_asset(mesh, False)):
    raise RuntimeError("Cannot save Body hunt gloves")
lod_ok = False
try:
    lod_ok = u.FPSModularOutfitComponent.configure_outfit_lods(mesh) and S.regenerate_lod(mesh, 3, True, False)
except Exception:
    lod_ok = False
if lod_ok:
    SAVE.save_packages([mesh.get_outer()], False)
else:
    print("BODY_HUNT_GLOVES_LOD0_ONLY", flush=True)
path = mesh.get_path_name()
config = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
config["items"][ITEM]["rig_meshes"]["Body"] = path
CONFIG.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "Saved/Body.json").write_text(json.dumps({
    "profile": "Body", "mesh": path, "runtime_tested": False,
}, indent=2) + "\n", encoding="utf-8")
print("BODY_HUNT_GLOVES_SAVED", path, flush=True)
