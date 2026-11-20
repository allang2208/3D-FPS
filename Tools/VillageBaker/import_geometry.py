"""Read the delivery FBX in its authoring axes for the native R4 bind pose."""
import gzip
import json
import os
from pathlib import Path

import bpy
import numpy as np

HOST = Path(os.environ["BAKER_UE_HOST"])
PROJECT = Path(__file__).resolve().parents[2]
ASSEMBLY = PROJECT / "SourceAssets/VillageBaker/AssemblyR1"
record = json.loads((ASSEMBLY / "geometry_ready.json").read_text(encoding="utf-8"))
names = record["material_slots"]
rig_data = PROJECT / "SourceAssets/JasonStrong20261117/R3_ArmsRefined/AnatomyReview/derived_saved_mesh.json"
bones = {b["name"]: b["index"] for b in json.loads(rig_data.read_text(encoding="utf-8"))["bones"]}
fbx = HOST / record["skeletal_fbx"]
# The FBX importer can expand embedded images next to its input.
if not fbx.exists():
    os.link(ASSEMBLY / fbx.name, fbx)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(fbx), use_image_search=False)
result = {key: [] for key in ("p", "n", "uv", "tri", "m", "w")}
result["correctives"] = {}
result["slots"] = names
for obj in (o for o in bpy.context.scene.objects if o.type == "MESH"):
    mesh = obj.data
    mesh.calc_loop_triangles()
    world = np.asarray(obj.matrix_world)
    basis = world[:3, :3]
    verts = np.zeros(len(mesh.vertices) * 3, np.float32)
    mesh.vertices.foreach_get("co", verts)
    verts = verts.reshape(-1, 3)
    positions = (verts @ basis.T + world[:3, 3]) * 100
    loops = np.empty(len(mesh.loops), dtype=np.int32)
    mesh.loops.foreach_get("vertex_index", loops)
    uv = np.empty(len(loops) * 2, dtype=np.float32)
    mesh.uv_layers.active.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    uv[:, 1] = 1 - uv[:, 1]
    normals = np.empty(len(loops) * 3, dtype=np.float32)
    mesh.corner_normals.foreach_get("vector", normals)
    normals = normals.reshape(-1, 3) @ np.linalg.inv(basis)
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    corners, indices = np.unique(np.column_stack((loops, uv, normals.round(6))), axis=0, return_inverse=True)
    indices = indices.ravel()
    ids = corners[:, 0].astype(int)
    offset = len(result["p"])
    result["p"].extend(positions[ids].tolist())
    result["uv"].extend(corners[:, 1:3].tolist())
    result["n"].extend(corners[:, 3:].tolist())
    weights = []
    lookup = {g.index: bones[g.name] for g in obj.vertex_groups if g.name in bones}
    for vert in mesh.vertices:
        weighted = sorted(((lookup[g.group], g.weight) for g in vert.groups if g.group in lookup and g.weight > 0),
                          key=lambda row: -row[1])[:8]
        if not weighted:
            raise RuntimeError(f"Unweighted vertex in {obj.name}: {vert.index}")
        total = sum(w for _, w in weighted)
        weights.append([[b, w / total] for b, w in weighted])
    result["w"].extend(weights[i] for i in ids)
    tris = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int32)
    mesh.loop_triangles.foreach_get("loops", tris)
    # GeometryScript expects native clockwise winding for these unchanged XYZ coordinates.
    result["tri"].extend((indices[tris].reshape(-1, 3)[:, ::-1] + offset).tolist())
    slots = [slot.material.name.split(".")[0] for slot in obj.material_slots]
    result["m"].extend(names.index(slots[t.material_index]) for t in mesh.loop_triangles)
    if mesh.shape_keys:
        for key in mesh.shape_keys.key_blocks:
            if not key.name.startswith("R4_"):
                continue
            coords = np.empty(verts.size, dtype=np.float32)
            key.data.foreach_get("co", coords)
            delta = ((coords.reshape(-1, 3) - verts) @ basis.T * 100)[ids]
            moved = np.flatnonzero((delta**2).sum(axis=1) > 1.e-9)
            result["correctives"][key.name] = [[int(i + offset), *delta[i].tolist()] for i in moved]
    print("BAKER_GEOMETRY", obj.name, len(mesh.loop_triangles), flush=True)
with gzip.open(HOST / "geometry.json.gz", "wt", compresslevel=2, encoding="utf-8") as stream:
    json.dump(result, stream, separators=(",", ":"))
