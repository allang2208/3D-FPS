"""Locate the oden pistol grip, trigger guard and top rail in source space.

Run: blender --background --factory-startup --python-exit-code 1 --python measure_grip.py
"""
import json
import os

import bpy

ROOT = r"D:\FPS3D\资产\oden先辈"
SOURCE = os.path.join(ROOT, "fbx", "weapon.FBX")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "Reference"))

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SOURCE, use_custom_normals=True)

obj = next(o for o in bpy.context.scene.objects if o.type == "MESH")
me = obj.data
slot_of = {i: (m.name if m else "-") for i, m in enumerate(me.materials)}
poly_slot = {p.index: p.material_index for p in me.polygons}
vert_slots = {}
for p in me.polygons:
    for v in p.vertices:
        vert_slots.setdefault(v, set()).add(p.material_index)

# Lower receiver only ("09"), which carries the grip, trigger guard and buttstock.
lower = [v.index for v in me.vertices if 0 in vert_slots.get(v.index, ())]
print("ASH12_LOWER_VERTS", len(lower))

BIN = 0.5
bins = {}
for i in lower:
    co = me.vertices[i].co
    if co.z > -1.0:
        continue
    key = round(co.x / BIN)
    b = bins.setdefault(key, [1e9, -1e9, 1e9, -1e9, 0])
    b[0] = min(b[0], co.z)
    b[1] = max(b[1], co.z)
    b[2] = min(b[2], co.y)
    b[3] = max(b[3], co.y)
    b[4] += 1

print("ASH12_LOWER_BINS_BEGIN")
for key in sorted(bins):
    b = bins[key]
    print("  x=%-8.1f n=%-5d z=[%7.3f,%7.3f] y=[%7.3f,%7.3f]" % (key * BIN, b[4], b[0], b[1], b[2], b[3]))
print("ASH12_LOWER_BINS_END")

# Top rail crown: highest Z of the "sights" (11) and "frontend" (08) parts over X.
for want, label in ((1, "sights_11"), (2, "frontend_08"), (0, "lower_09")):
    row = {}
    for i in range(len(me.vertices)):
        if want not in vert_slots.get(i, ()):
            continue
        co = me.vertices[i].co
        key = round(co.x)
        if key not in row or co.z > row[key]:
            row[key] = co.z
    top = sorted(row.items())
    print("ASH12_TOPCROWN_%s" % label, [(x, round(z, 3)) for x, z in top if -8 <= x <= 12])

# Trigger: geometry between the grip and the magazine, in the trigger-guard slot.
print("ASH12_GRIP_HINT done")
