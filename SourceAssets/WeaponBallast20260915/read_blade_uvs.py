"""Dump the UVs the frost sword's blade (剑身) occupies on its textures.

Usage:
    blender --background --factory-startup --python-exit-code 1 \
        --python read_blade_uvs.py -- <case_dir>

Same mesh and textures as the pommel measurement; the difference is the band
that gets selected. The band is not guessed: a cross-section profile along the
long axis finds the guard (the widest point of the hilt), and the blade is
everything from just above it to the tip.
"""

import json
import os
import sys

import bpy

SWORD_FBX = ("D:/FPS3D/FPSGAME/SourceAssets/MeshyMelee20260915/Export/"
             "SM_FrostCrystalSword.fbx")
PROFILE_BINS = 60
TIP_MARGIN_M = 0.03


def log(message):
    print("[blade] " + message)


def main():
    argv = sys.argv
    case_dir = argv[argv.index("--") + 1] if "--" in argv else os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(case_dir, "blade_uvs.json")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=SWORD_FBX)
    meshes = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    obj = max(meshes, key=lambda item: len(item.data.vertices))
    mesh = obj.data
    matrix = obj.matrix_world
    coords = [matrix @ vert.co for vert in mesh.vertices]
    mins = [min(c[i] for c in coords) for i in range(3)]
    maxs = [max(c[i] for c in coords) for i in range(3)]
    extents = [maxs[i] - mins[i] for i in range(3)]
    axis = extents.index(max(extents))
    log("long axis=%d length=%.4f" % (axis, extents[axis]))

    # Cross-section profile: max radial distance from the long axis per bin.
    others = [i for i in range(3) if i != axis]
    centre = [(mins[i] + maxs[i]) / 2.0 for i in range(3)]
    bin_size = extents[axis] / PROFILE_BINS
    profile = [0.0] * PROFILE_BINS
    for c in coords:
        index = min(PROFILE_BINS - 1, max(0, int((c[axis] - mins[axis]) / bin_size)))
        radius = max(abs(c[i] - centre[i]) for i in others)
        profile[index] = max(profile[index], radius)
    log("profile (low -> high end, mm): " + " ".join(
        "%.0f" % (value * 1000.0) for value in profile))

    # The guard is the widest bin in the lower half; the blade starts above it.
    lower = range(0, PROFILE_BINS // 2)
    guard_bin = max(lower, key=lambda i: profile[i])
    guard_z = mins[axis] + (guard_bin + 0.5) * bin_size
    low = guard_z + bin_size
    high = maxs[axis] - TIP_MARGIN_M
    log("guard at z=%.3f m (bin %d, width %.1f mm); blade band %.3f..%.3f m" % (
        guard_z, guard_bin, profile[guard_bin] * 1000.0, low, high))
    selected = [i for i, c in enumerate(coords) if low <= c[axis] <= high]
    selected_set = set(selected)
    log("blade band z=%.3f..%.3f m  vertices=%d" % (low, high, len(selected)))

    uv_layer = mesh.uv_layers.active.data
    uv_samples = []
    for loop in mesh.loops:
        if loop.vertex_index in selected_set:
            uv = uv_layer[loop.index].uv
            uv_samples.append((float(uv[0]) % 1.0, float(uv[1]) % 1.0))
    if not uv_samples:
        raise SystemExit("no UVs found for the blade band")

    us = [uv[0] for uv in uv_samples]
    vs = [uv[1] for uv in uv_samples]
    report = {
        "sword_fbx": SWORD_FBX,
        "mesh": obj.name,
        "axis_index": axis,
        "guard_z_m": guard_z,
        "band_m": [low, high],
        "profile_mm": [round(value * 1000.0, 1) for value in profile],
        "blade_vertices": len(selected),
        "uv_rect": {"u_min": min(us), "u_max": max(us), "v_min": min(vs), "v_max": max(vs),
                    "u_mean": sum(us) / len(us), "v_mean": sum(vs) / len(vs)},
        "uv_samples": [[round(u, 5), round(v, 5)] for u, v in uv_samples],
    }
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    log("wrote %s (uv samples=%d)" % (os.path.basename(out_path), len(uv_samples)))


if __name__ == "__main__":
    main()
