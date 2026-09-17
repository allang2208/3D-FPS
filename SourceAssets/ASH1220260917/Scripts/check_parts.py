"""Compare each material's fitted bounds against the source bounds moved by the
fit transform, so a misplaced part is visible instead of guessed at.

Run: blender --background --factory-startup --python-exit-code 1 --python check_parts.py
"""
import json
import os

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
O = os.path.normpath(os.path.join(HERE, ".."))

with open(os.path.join(O, "build.json"), encoding="utf-8") as fh:
    build = json.load(fh)
SCALE = build["fit"]["scale"]
TARGET = Vector(build["fit"]["translation"])
fit = Matrix.Translation(TARGET) @ Matrix.Rotation(1.5707963267948966, 4, "Z") @ Matrix.Scale(SCALE, 4)

bpy.ops.wm.open_mainfile(filepath=os.path.join(O, "ASH12_Editable.blend"))
scene = bpy.context.scene
rig = bpy.data.objects["SK_M4_Infima"]
gun = bpy.data.objects["ASH12_Export"]
action = bpy.data.actions["ASH12_idle"]
rig.animation_data.action = action
if action.slots:
    rig.animation_data.action_slot = action.slots[0]
scene.frame_set(0)
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
ev = gun.evaluated_get(dg)
me = ev.to_mesh()
world = [ev.matrix_world @ v.co for v in me.vertices]

groups = {}
for poly in me.polygons:
    slot = me.materials[poly.material_index].name
    for v in poly.vertices:
        groups.setdefault(slot, set()).add(v)

# Where the source put these same materials, moved by the fit alone.
with open(os.path.join(O, "Reference", "parts.json"), encoding="utf-8") as fh:
    parts = json.load(fh)["parts"]
source_bounds = {}
for part in parts:
    source_bounds[part["material"]] = (part["bbox_min"], part["bbox_max"])

with open(os.path.join(O, "build.json"), encoding="utf-8") as fh:
    material_map = json.load(fh)["materials"]

print("ASH12_PARTCHECK_BEGIN")
for slot, verts in sorted(groups.items()):
    pts = [world[v] for v in verts]
    lo = [round(min(p[i] for p in pts), 4) for i in range(3)]
    hi = [round(max(p[i] for p in pts), 4) for i in range(3)]
    src = None
    for source_name, fitted_name in material_map.items():
        if fitted_name == slot:
            src = source_name
    expect = ""
    if src and src in source_bounds:
        slo, shi = source_bounds[src]
        elo = [round((fit @ Vector(slo))[i], 4) for i in range(3)]
        ehi = [round((fit @ Vector(shi))[i], 4) for i in range(3)]
        expect = "expected_min=%s expected_max=%s" % (elo, ehi)
    print("ASH12_PART %-24s n=%-6d min=%s max=%s %s" % (slot, len(verts), lo, hi, expect))
ev.to_mesh_clear()

# Which bone owns which vertex, and where those bones actually are.
bones = {}
for group in gun.vertex_groups:
    bones[group.name] = 0
for v in gun.data.vertices:
    for g in v.groups:
        bones[gun.vertex_groups[g.group].name] += 1
print("ASH12_GROUPS", bones)
for name in bones:
    bone = rig.pose.bones[name]
    print("ASH12_GROUP_BONE %-22s head=%s" % (name, [round(float(c), 4) for c in (rig.matrix_world @ bone.head)]))
print("ASH12_PARTCHECK_END")
