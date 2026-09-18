"""Rebuild the M4 and QBZ extended magazines from their factory magazine parts.

Same rule that passed on the AKM: the factory magazine is lengthened 6 cm with
the displacement ramped along the magazine's own centre line (quadratic-fitted
tangents), and the band sits just above the floor plate so the reload
animation's left-hand grip zone keeps untouched factory geometry.

Run: blender -b -P build_extmag_from_sections.py
"""
import bpy
import json
import math
import numpy as np
import os
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
FBXDIR = os.path.join(ROOT, "FBX")
SA = r"D:\FPS3D\FPSGAME\SourceAssets"
BLENDS = os.path.join(SA, "PhantomRearGripIntegration20260913")

EXTENSION = 0.06
BAND_FRACTION = 0.12

JOBS = {
    "M4": dict(source=os.path.join(BLENDS, "AKM", "AKM_RearGripSections_Editable.blend"),
               blend=True, object="M4_Magazine Light.003_Export", match="magazine",
               out="SM_ExtMag_M440_factory.fbx"),
    "QBZ": dict(source=os.path.join(BLENDS, "QBZ191", "QBZ191_RearGripSections_Editable.blend"),
                blend=True, object="QBZ_Magazine", match="magazine",
                out="SM_ExtMag_QBZ40_factory.fbx"),
}


def load_source(cfg):
    if cfg["blend"]:
        bpy.ops.wm.open_mainfile(filepath=cfg["source"])
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=cfg["source"])


def pick_object(cfg):
    if cfg["object"] in bpy.data.objects:
        return bpy.data.objects[cfg["object"]]
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        for material in ob.data.materials:
            if material and cfg["match"] in material.name.lower():
                return ob
    raise RuntimeError("magazine object not found in " + cfg["source"])


report = {}
for gun, cfg in JOBS.items():
    load_source(cfg)
    source = pick_object(cfg)
    mesh = source.data.copy()
    mesh.name = "SM_ExtMag_%s" % gun
    ob = bpy.data.objects.new("SM_ExtMag_%s" % gun, mesh)
    bpy.context.scene.collection.objects.link(ob)
    ob.matrix_world = source.matrix_world.copy()
    for modifier in list(ob.modifiers):
        ob.modifiers.remove(modifier)
    for other in [o for o in bpy.context.scene.objects if o is not ob]:
        bpy.data.objects.remove(other, do_unlink=True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    points = [ob.matrix_world @ v.co for v in mesh.vertices]
    lo = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    hi = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    centroid = (lo + hi) * 0.5
    print("SECTION", gun, "verts", len(mesh.vertices), "polys", len(mesh.polygons),
          "dims_cm", tuple(round((hi - lo)[i] * 100, 2) for i in range(3)),
          "mats", [m.name if m else None for m in mesh.materials], flush=True)

    # Magazine axis: slice centroids through the mesh, then a quadratic centre line.
    seed = (hi - lo)
    seed_axis = Vector((0.0, 0.0, 1.0))
    along = [(p - centroid).dot(seed_axis) for p in points]
    bins = 24
    low, high = min(along), max(along)
    slices = []
    for index in range(bins):
        a = low + (high - low) * index / bins
        b = low + (high - low) * (index + 1) / bins
        group = [p for p, value in zip(points, along) if a <= value < b]
        if len(group) >= 8:
            slices.append((a + b) * 0.5, )
            slices[-1] = ((a + b) * 0.5, sum(group, Vector()) / len(group))
    values = np.array([value for value, _ in slices])
    centres = np.array([[c.x, c.y, c.z] for _, c in slices])
    polys = [np.polyfit(values, centres[:, axis], 2) for axis in range(3)]

    def tangent(value):
        derivative = np.array([np.polyval(np.polyder(p), value) for p in polys])
        direction = Vector((float(derivative[0]), float(derivative[1]), float(derivative[2])))
        if direction.length < 1e-6:
            return seed_axis
        return direction.normalized()

    along = [(ob.matrix_world @ v.co - centroid).dot(seed_axis) for v in mesh.vertices]
    low, high = min(along), max(along)
    band_bottom = low + (high - low) * BAND_FRACTION
    band_top = band_bottom + EXTENSION
    inverse = ob.matrix_world.inverted()
    for vertex in mesh.vertices:
        point = ob.matrix_world @ vertex.co
        value = (point - centroid).dot(seed_axis)
        ramp = (band_top - value) / EXTENSION
        if ramp <= 0.0:
            continue
        ramp = min(1.0, ramp)
        ramp = ramp * ramp * (3.0 - 2.0 * ramp)
        vertex.co = inverse @ (point - tangent(value) * (EXTENSION * ramp))
    mesh.update()

    new_points = [ob.matrix_world @ v.co for v in mesh.vertices]
    nlo = Vector((min(p.x for p in new_points), min(p.y for p in new_points), min(p.z for p in new_points)))
    nhi = Vector((max(p.x for p in new_points), max(p.y for p in new_points), max(p.z for p in new_points)))
    print("SECTION_EXTENDED", gun,
          "dims_cm", tuple(round((nhi - nlo)[i] * 100, 2) for i in range(3)),
          "band_cm_from_bottom", round((band_bottom - low) * 100, 2), flush=True)

    out = os.path.join(FBXDIR, cfg["out"])
    bpy.ops.export_scene.fbx(filepath=out, use_selection=True, object_types={'MESH'},
                             axis_forward='-Y', axis_up='Z', bake_anim=False,
                             mesh_smooth_type='FACE', use_tspace=True)
    report[gun] = {"source": cfg["source"], "object": cfg["object"], "file": out,
                   "dims_cm": [round((nhi - nlo)[i] * 100, 2) for i in range(3)],
                   "band_fraction": BAND_FRACTION, "extension_cm": EXTENSION * 100,
                   "uv_layers": [layer.name for layer in mesh.uv_layers]}

with open(os.path.join(ROOT, "Reference", "sections_build.json"), "w", encoding="utf-8") as handle:
    json.dump(report, handle, indent=1, ensure_ascii=False)
print("SECTIONS_BUILD " + json.dumps(report, ensure_ascii=False), flush=True)
