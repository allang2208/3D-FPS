"""Author a neutral left-digit mesh bind while preserving M16 animation poses.

The former position-only DQ repair is intentionally not an input surface.
Production inputs are the pre-repair native mesh snapshots and accepted V7
canonical surface.  Only the nineteen left-digit reference rotations change;
native translations, scales, hierarchy and all other reference bones remain.
UE saves are handled separately by the scoped installer.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
PROJECT = REPAIR.parents[1]
V7 = PROJECT / "SourceAssets/ModularOutfit20260925/BarePalmV7"
OUT = HERE / "Authored"
DIGIT_PREFIXES = ("thumb_", "index_", "middle_", "ring_", "pinky_")
PRIMARY = ("CurrentM16", "AcceptedM16V7", "EquipmentM16Skin")


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")),
                    encoding="utf-8")


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def matrix(bone):
    result = np.eye(4)
    result[:3, :3] = np.asarray(bone["axes"], dtype=float).T
    result[:3, 3] = bone["position"]
    return result


def is_digit(name):
    return name.endswith("_l") and name.startswith(DIGIT_PREFIXES)


def decompose(transform):
    """Keep native scale, including the native root's approximately 100 scale."""
    scale = np.linalg.norm(transform[:3, :3], axis=0)
    rotation = transform[:3, :3] / scale
    # Exported reference axes have normal floating point round-off.  Use the
    # nearest rotation only to author a quaternion; never discard native scale.
    left, _, right = np.linalg.svd(rotation)
    rotation = left @ right
    if np.linalg.det(rotation) < 0:
        scale[-1] *= -1
        left[:, -1] *= -1
        rotation = left @ right
    return transform[:3, 3].copy(), Rotation.from_matrix(rotation), scale


def neutral_reference(native, canonical):
    native_by_index = {b["index"]: name for name, b in native.items()}
    common_by_index = {b["index"]: name for name, b in canonical.items()}
    old_world = {name: matrix(b) for name, b in native.items()}
    common_world = {name: matrix(b) for name, b in canonical.items()}
    new_world = {}
    local_records = []
    for name, bone in sorted(native.items(), key=lambda item: item[1]["index"]):
        parent = native_by_index.get(bone["parent"])
        old_local = np.linalg.inv(old_world[parent]) @ old_world[name] if parent else old_world[name].copy()
        new_local = old_local.copy()
        if is_digit(name):
            common_parent = common_by_index.get(canonical[name]["parent"])
            common_local = (np.linalg.inv(common_world[common_parent]) @ common_world[name]
                            if common_parent else common_world[name])
            translation, old_rotation, scale = decompose(old_local)
            _, new_rotation, _ = decompose(common_local)
            new_local[:3, :3] = new_rotation.as_matrix() @ np.diag(scale)
            new_local[:3, 3] = translation
            local_records.append({
                "name": name, "index": bone["index"], "parent": parent,
                "translation": translation.tolist(),
                "rotation_xyzw": new_rotation.as_quat().tolist(),
                "scale": scale.tolist(),
                "old_rotation_xyzw": old_rotation.as_quat().tolist(),
            })
        new_world[name] = new_world[parent] @ new_local if parent else new_local
    if len(local_records) != 19:
        raise RuntimeError("Expected exactly nineteen left-digit reference bones")
    new_bones = {
        name: {"index": bone["index"], "parent": bone["parent"],
               "position": new_world[name][:3, 3].tolist(),
               "axes": new_world[name][:3, :3].T.tolist()}
        for name, bone in native.items()
    }
    return old_world, new_world, new_bones, local_records


def transfer(world, canonical):
    return {name: world[name] @ np.linalg.inv(matrix(bone))
            for name, bone in canonical.items() if name in world}


def blended(weights, transforms):
    total = sum(weights.values())
    if total <= 0:
        raise RuntimeError("A changed vertex has no skin influences")
    return sum(transforms[name] * (weight / total) for name, weight in weights.items())


def digit_indices(weights):
    return [i for i, influences in enumerate(weights)
            if any(is_digit(name) and weight > 0 for name, weight in influences.items())]


def common_vertex_map(data, raw):
    """Resolve UV-split imported vertices back to the exact accepted surface."""
    tree = cKDTree(np.asarray(raw["positions"]))
    positions = np.asarray(data["positions"])
    distances, nearest = tree.query(positions)
    if float(distances.max(initial=0)) > 0.001:
        raise RuntimeError("Accepted V7 native vertex registration changed")
    mapping = nearest.astype(np.int64)
    for index in digit_indices(data["weights"]):
        candidates = tree.query_ball_point(positions[index], 0.0001)
        weights = data["weights"][index]
        def error(candidate):
            donor = raw["weights"][candidate]
            return sum(abs(weights.get(name, 0) - donor.get(name, 0))
                       for name in weights.keys() | donor.keys())
        selected = min(candidates, key=error)
        if error(selected) > 0.001:
            raise RuntimeError("Accepted V7 native skin registration changed")
        mapping[index] = selected
    return mapping


def current_positions(input_path, data):
    positions = np.asarray(data["positions"], dtype=float).copy()
    # These positions are the source that the installer currently reads.  They
    # are used only for the precondition; neutral geometry starts from baseline.
    old_patch = REPAIR / "Authored" / f"{input_path.stem}.position_patch.json"
    for edit in read(old_patch)["vertex_edits"]:
        positions[edit["index"]] = edit["position"]
    return positions


def author_patch(input_path, raw, old_transfers, new_transfers, receipt):
    data = read(input_path)
    before = np.asarray(data["positions"], dtype=float)
    current = current_positions(input_path, data)
    authored = before.copy()
    indices = digit_indices(data["weights"])
    primary = input_path.stem in PRIMARY
    common_map = common_vertex_map(data, raw) if primary else None
    for index in indices:
        weights = data["weights"][index]
        new_blend = blended(weights, new_transfers)
        if primary:
            canonical = np.asarray(raw["canonical_positions"][common_map[index]])
        else:
            canonical = np.linalg.solve(blended(weights, old_transfers),
                                        np.r_[before[index], 1.])[:3]
        authored[index] = (new_blend @ np.r_[canonical, 1.])[:3]
    movement = np.linalg.norm(authored - current, axis=1)
    output = OUT / f"{input_path.stem}.position_patch.json"
    expected = receipt[data["path"]]["after_sha256"]
    patch = {
        "schema": "m16_neutral_left_digit_bind_positions_v1",
        "input": str(input_path.resolve()), "input_sha256": sha(input_path),
        "source": data["path"], "source_sha256": expected,
        "baseline_source_sha256": data["source_sha256"],
        "skeleton": data["skeleton"], "arm_ids": data.get("arm_ids"),
        "vertex_index_space": ("sorted_used_vertices_of_exported_arm_materials"
                               if data.get("arm_ids") is not None else "full_mesh_vertex_ids"),
        "vertex_count": len(before), "triangle_count": len(data.get("triangles", [])),
        "edited_vertex_count": len(indices),
        "max_movement_cm": float(movement.max(initial=0)),
        "vertex_edits": [{"index": int(index), "original": current[index].tolist(),
                          "baseline_before_dq": before[index].tolist(),
                          "position": authored[index].tolist()} for index in indices],
        "method": ("exact_common_v7_surface_new_native_left_digit_bind" if primary else
                   "inverse_pre_dq_native_lbs_then_new_native_left_digit_bind"),
        "preserved": ["skin_weights", "triangles", "uvs", "materials", "right_arm",
                      "wrist", "forearm", "native_local_translation", "native_local_scale"],
    }
    write(output, patch)
    return {"source": data["path"], "source_sha256": expected,
            "patch": str(output.resolve()), "patch_sha256": sha(output),
            "edited_vertex_count": len(indices), "vertex_count": len(before),
            "max_movement_cm": patch["max_movement_cm"]}


def update_normals(data, positions, indices):
    triangles = np.asarray(data["triangles"], dtype=np.int64)
    normals = np.asarray(data["normals"], dtype=float)
    moved = np.zeros(len(positions), dtype=bool)
    moved[indices] = True
    changed = np.any(moved[triangles], axis=1)
    affected = set(int(i) for i in triangles[changed].ravel())
    face_normals = np.cross(positions[triangles[:, 1]] - positions[triangles[:, 0]],
                            positions[triangles[:, 2]] - positions[triangles[:, 0]])
    face_normals[np.einsum("ij,ij->i", face_normals, normals.mean(axis=1)) < 0] *= -1
    groups = {}
    for face, triangle in enumerate(triangles):
        for corner, vertex in enumerate(triangle):
            if int(vertex) in affected:
                key = (int(vertex), *np.round(normals[face, corner], 5))
                groups.setdefault(key, []).append((face, corner))
    for corners in groups.values():
        normal = sum((face_normals[face] for face, _ in corners), np.zeros(3))
        length = np.linalg.norm(normal)
        if length > 1e-12:
            normal /= length
            for face, corner in corners:
                normals[face, corner] = normal
    data["normals"] = normals.tolist()


def author_editable(raw, new_transfers, new_bones):
    data = dict(raw)
    positions = np.asarray(raw["positions"], dtype=float).copy()
    indices = digit_indices(raw["weights"])
    for index in indices:
        positions[index] = (blended(raw["weights"][index], new_transfers) @
                            np.r_[raw["canonical_positions"][index], 1.])[:3]
    data["positions"] = positions.tolist()
    update_normals(data, positions, indices)
    data["contract"] += "; M16 nineteen left-digit mesh bind rotations neutralized to common V7"
    data["neutral_left_digit_bind"] = {
        "method": "exact_common_v7_surface_new_native_left_digit_bind",
        "bone_rotation_count": 19, "native_translation_and_scale_preserved": True,
        "native_animation_local_keys_unchanged": True,
    }
    output = OUT / "M16_BareArmsV7_NeutralBind_Editable.json"
    write(output, data)
    native_source = HERE / "NativeSources" / "M16.json"
    write(native_source, {"bones": new_bones})
    write(HERE / "manifest.json", [{"profile": "M16", "authored": str(output.resolve())}])
    return {"output": str(output.resolve()), "output_sha256": sha(output),
            "native_reference": str(native_source.resolve()),
            "native_reference_sha256": sha(native_source), "vertex_count": len(positions)}


def main():
    canonical_path = V7 / "M4_original.json"
    raw_path = V7 / "Authored/M16.json"
    canonical = read(canonical_path)["bones"]
    native = read(REPAIR / "Input/AcceptedM16V7.json")["bones"]
    raw = read(raw_path)
    old_world, new_world, new_bones, local_records = neutral_reference(native, canonical)
    old_transfers = transfer(old_world, canonical)
    new_transfers = transfer(new_world, canonical)
    reference_path = OUT / "left_digit_reference.json"
    write(reference_path, {"schema": "m16_neutral_left_digit_reference_v1",
                          "native_mesh_reference_source": "AcceptedM16V7 pre-DQ snapshot",
                          "canonical": str(canonical_path.resolve()),
                          "local_transforms": local_records,
                          "bones": new_bones,
                          "skeleton_asset_reference_unchanged": True})
    inputs = [REPAIR / f"Input/{name}.json" for name in PRIMARY]
    inputs.extend(sorted((REPAIR / "Input/Outfits").glob("*M16*.json")))
    receipt = read(REPAIR / "installed.json")
    manifest = {
        "schema": "m16_neutral_left_digit_bind_authoring_v1",
        "canonical_source": str(canonical_path.resolve()), "canonical_sha256": sha(canonical_path),
        "raw_surface_source": str(raw_path.resolve()), "raw_surface_sha256": sha(raw_path),
        "reference": str(reference_path.resolve()), "reference_sha256": sha(reference_path),
        "patches": [author_patch(path, raw, old_transfers, new_transfers, receipt) for path in inputs],
        "editable": author_editable(raw, new_transfers, new_bones),
        "animation_assets_changed": False, "runtime_tested": False,
    }
    write(OUT / "authoring.json", manifest)
    for patch in manifest["patches"]:
        print("M16_NEUTRAL_AUTHORED", patch["source"], patch["edited_vertex_count"],
              "vertices", f"max={patch['max_movement_cm']:.6f}cm", flush=True)
    print("M16_NEUTRAL_AUTHOR_COMPLETE", str((OUT / "authoring.json").resolve()), flush=True)


if __name__ == "__main__":
    main()
