"""Locate the frost sword pommel on its texture and dump the UVs it uses.

Usage:
    blender --background --factory-startup --python-exit-code 1 \
        --python read_pommel_uvs.py -- <case_dir>

The frost sword (寒晶·双手剑) is a single skinned mesh using
M_FrostCrystalSword, so the pommel has no material of its own: it is a UV
region of the same four textures. authoring.json puts the pommel at z =
-28.235 cm and the blade tip at +81.17 cm, so the pommel is the bulky end of
the long axis. This script finds that end, collects the UVs of the vertices in
it and writes them out for texture sampling.
"""

import json
import os
import sys

import bpy

SWORD_FBX = ("D:/FPS3D/FPSGAME/SourceAssets/MeshyMelee20260915/Export/"
             "SM_FrostCrystalSword.fbx")
P0MMEL_HINT_CM = -28.235143423080444
BLADE_TIP_CM = 81.17273449897766


def log(message):
    print("[pommel] " + message)


def main():
    argv = sys.argv
    case_dir = argv[argv.index("--") + 1] if "--" in argv else os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(case_dir, "pommel_uvs.json")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=SWORD_FBX)
    meshes = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    if not meshes:
        raise SystemExit("no mesh imported from " + SWORD_FBX)
    obj = max(meshes, key=lambda item: len(item.data.vertices))
    mesh = obj.data
    log("mesh=%s verts=%d uv_layers=%d slots=%d" % (
        obj.name, len(mesh.vertices), len(mesh.uv_layers),
        len(obj.material_slots)))

    matrix = obj.matrix_world
    coords = [matrix @ vert.co for vert in mesh.vertices]
    mins = [min(c[i] for c in coords) for i in range(3)]
    maxs = [max(c[i] for c in coords) for i in range(3)]
    extents = [maxs[i] - mins[i] for i in range(3)]
    axis = extents.index(max(extents))
    length = extents[axis]
    others = [i for i in range(3) if i != axis]
    log("long axis=%d length=%.4f m extents=%s" % (
        axis, length, [round(value, 4) for value in extents]))

    def spread(band):
        return max(max(c[i] for c in band) - min(c[i] for c in band) for i in others)

    band_size = 0.06 * length
    low_band = [c for c in coords if c[axis] <= mins[axis] + band_size]
    high_band = [c for c in coords if c[axis] >= maxs[axis] - band_size]
    low_spread, high_spread = spread(low_band), spread(high_band)
    log("low end spread=%.4f (n=%d)  high end spread=%.4f (n=%d)" % (
        low_spread, len(low_band), high_spread, len(high_band)))
    # The blade tip tapers to a point; the pommel is the blunt, wider end.
    pommel_is_low = low_spread > high_spread
    log("pommel at %s end" % ("low" if pommel_is_low else "high"))

    # Take the outer 4 cm of the pommel end.
    reach = 0.04
    if pommel_is_low:
        limit = mins[axis] + reach
        selected = [i for i, c in enumerate(coords) if c[axis] <= limit]
    else:
        limit = maxs[axis] - reach
        selected = [i for i, c in enumerate(coords) if c[axis] >= limit]
    selected_set = set(selected)
    log("pommel vertices selected=%d" % len(selected))

    uv_layer = mesh.uv_layers.active.data
    uv_samples = []
    for loop in mesh.loops:
        if loop.vertex_index in selected_set:
            uv = uv_layer[loop.index].uv
            uv_samples.append((float(uv[0]), float(uv[1])))
    if not uv_samples:
        raise SystemExit("no UVs found for the pommel band")

    us = [uv[0] for uv in uv_samples]
    vs = [uv[1] for uv in uv_samples]
    us_wrapped = [u % 1.0 for u in us]
    vs_wrapped = [v % 1.0 for v in vs]
    report = {
        "sword_fbx": SWORD_FBX,
        "mesh": obj.name,
        "vertices": len(mesh.vertices),
        "material_slots": [slot.material.name for slot in obj.material_slots if slot.material],
        "axis_index": axis,
        "length_m": round(length, 5),
        "ends": {"low_spread": round(low_spread, 5), "high_spread": round(high_spread, 5),
                 "pommel_at_low_end": pommel_is_low},
        "pommel_band_m": reach,
        "pommel_vertices": len(selected),
        "uv_raw": {"u_min": min(us), "u_max": max(us), "v_min": min(vs), "v_max": max(vs)},
        "uv_wrapped": {"u_min": min(us_wrapped), "u_max": max(us_wrapped),
                       "v_min": min(vs_wrapped), "v_max": max(vs_wrapped),
                       "u_mean": sum(us_wrapped) / len(us_wrapped),
                       "v_mean": sum(vs_wrapped) / len(vs_wrapped)},
        "uv_samples": [[round(u % 1.0, 5), round(v % 1.0, 5)] for u, v in uv_samples],
        "authoring_reference_cm": {"pommel": P0MMEL_HINT_CM, "blade_tip": BLADE_TIP_CM},
    }
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    log("wrote %s (uv samples=%d)" % (os.path.basename(out_path), len(uv_samples)))


if __name__ == "__main__":
    main()
