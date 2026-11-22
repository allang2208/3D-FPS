"""Retain the approved skinned hardware and replace the braid between the fittings."""
import json
import math
from pathlib import Path

import bmesh
import bpy

OUT = Path(__file__).resolve().parent
SOURCE = OUT.parent / "MountainEchoV13"
NAME = "SK_Highland_BeamString"
LIGHT = "M_Highland_BeamString_Light"

bpy.ops.wm.open_mainfile(filepath=str(SOURCE / "MountainEcho_String.blend"))
bpy.context.preferences.filepaths.save_version = 0
recipe = json.loads((SOURCE / "authoring.json").read_text(encoding="utf-8"))
body = bpy.data.objects[recipe["mesh"]]
armature = body.parent
mesh = bmesh.new()
mesh.from_mesh(body.data)
mesh.verts.ensure_lookup_table()

# The original recipe recorded the ordered contiguous vertex ranges of its islands.
remove_vertices = []
cursor = 0
for part in recipe["parts"]:
    count = part["vertices"]
    if part["name"] in {"Counterwoven silver/graphite", "Buried antique gold filament"}:
        remove_vertices.extend(mesh.verts[i] for i in range(cursor, cursor + count))
    cursor += count
if cursor != len(mesh.verts) or not remove_vertices:
    raise ValueError("Original part ranges and mesh no longer match")
bmesh.ops.delete(mesh, geom=remove_vertices, context="VERTS")

light = bpy.data.materials.new(LIGHT)
light.diffuse_color = (1.0, .78, .43, 1.0)
light.use_nodes = True
principled = next(node for node in light.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
principled.inputs["Base Color"].default_value = (1.0, .78, .43, 1)
principled.inputs["Emission Color"].default_value = (1.0, .76, .39, 1)
principled.inputs["Emission Strength"].default_value = 3
light_slot = len(body.data.materials)
body.data.materials.append(light)

x, y, nock = recipe["anchors_cm"]["nock"]
lower = recipe["anchors_cm"]["lower"][2]
upper = recipe["anchors_cm"]["upper"][2]
deform = mesh.verts.layers.deform.verify()

def beam(start, end, start_bone, end_bone):
    groups = (body.vertex_groups[start_bone].index, body.vertex_groups[end_bone].index)
    previous = None
    for ring in range(25):
        fraction = ring / 24
        z = start + (end - start) * fraction
        vertices = []
        for step in range(12):
            angle = math.tau * step / 12
            vertex = mesh.verts.new((x + .076 * math.cos(angle), y + .076 * math.sin(angle), z))
            if fraction < 1:
                vertex[deform][groups[0]] = 1 - fraction
            if fraction > 0:
                vertex[deform][groups[1]] = fraction
            vertices.append(vertex)
        if previous:
            for step in range(12):
                adjacent = (step + 1) % 12
                face = mesh.faces.new((previous[step], previous[adjacent], vertices[adjacent], vertices[step]))
                face.material_index = light_slot
                face.smooth = True
        previous = vertices

# Bury each end in its own fixture and keep it on that fixture's bone under draw.
beam(lower + 1.15, nock - 3.93, "string_lower", "string_nock")
beam(nock + 1.93, upper - 1.15, "string_nock", "string_upper")
mesh.normal_update()
mesh.to_mesh(body.data)
mesh.free()
body.data.update()
body.name = NAME
body.data.name = NAME

bpy.ops.object.select_all(action="DESELECT")
armature.select_set(True)
body.select_set(True)
bpy.context.view_layer.objects.active = armature
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Highland_BeamString.blend"))
bpy.ops.export_scene.fbx(filepath=str(OUT / (NAME + ".fbx")), use_selection=True,
    object_types={"ARMATURE", "MESH"}, global_scale=1, apply_unit_scale=True,
    apply_scale_options="FBX_SCALE_ALL", axis_forward="-Y", axis_up="Z",
    add_leaf_bones=False, use_armature_deform_only=True, bake_anim=False,
    mesh_smooth_type="FACE", use_tspace=True, colors_type="LINEAR")
