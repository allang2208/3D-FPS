"""Read the skinned Meshy bind pose in its original glTF axes, without applying its animation."""
from pathlib import Path
import json

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[2] / "SourceAssets/VillageGunsmith/Rig"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT / "rigged.glb"))
objects = [o for o in bpy.context.scene.objects if o.type == "MESH" and o.vertex_groups]
bones = sorted({g.name for obj in objects for g in obj.vertex_groups})
points, indices, amounts = [], [], []
for obj in objects:
    vertices = obj.data.vertices
    coords = np.empty(len(vertices) * 3, np.float32)
    vertices.foreach_get("co", coords)
    m = np.asarray(obj.matrix_world)
    xyz = coords.reshape(-1, 3) @ m[:3, :3].T + m[:3, 3]
    # Blender (x,-z,y) -> glTF (x,y,z) -> the original R4 authoring frame.
    points.append(xyz * [-1., -1., 1.])
    slots = [bones.index(g.name) for g in obj.vertex_groups]
    joints = np.zeros((len(vertices), 8), np.int16)
    weights = np.zeros((len(vertices), 8), np.float32)
    for i, vertex in enumerate(vertices):
        for j, g in enumerate(sorted(vertex.groups, key=lambda g: -g.weight)[:8]):
            joints[i, j] = slots[g.group]
            weights[i, j] = g.weight
    indices.append(joints)
    amounts.append(weights)
if not points:
    raise ValueError("Meshy delivered no skinned geometry")
np.savez_compressed(ROOT / "skin.npz", points=np.vstack(points), joints=np.vstack(indices),
                    weights=np.vstack(amounts), bones=bones)
print("Rigged objects:", [(o.name, len(o.data.vertices)) for o in objects])
print("Skin bounds:", np.vstack(points).min(axis=0), np.vstack(points).max(axis=0))
print("Bones:", json.dumps(bones))
