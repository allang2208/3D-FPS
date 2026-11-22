"""Trim the factory blade remnant while preserving the shield and the swept wings."""
from collections import defaultdict
import json
from pathlib import Path

import bpy
from mathutils import Vector, geometry


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1] / "CommonMods/ForgedSteelGreatsword_CommonVariants_Editable.blend"
ROOT = "/Game/Weapons/ForgedSteelGreatsword20261120"
DESTINATION = ROOT + "/ExecutionerBlade/GuardSeats"
MATERIAL = "M_ForgedSteelGreatsword_Surface_V1"
Z_CUT = 0.0162
CENTRAL_HALF_WIDTH = 0.052
OPTIONS = ("factory", "bastion_guard", "riposte_guard", "light_guard")


def build_seat(source, name):
    mesh = source.data
    normals = [corner.vector.copy() for corner in mesh.corner_normals]
    uvs = mesh.uv_layers.active.data
    points, faces, samples = [], [], []
    indices = {}
    neighbours = defaultdict(set)

    def corner(loop):
        index = mesh.loops[loop].vertex_index
        return (index, mesh.vertices[index].co.copy(), uvs[loop].uv.copy(), normals[loop])

    def intersection(a, b):
        key = tuple(sorted((a[0], b[0])))
        weight = (Z_CUT - a[1].z) / (b[1].z - a[1].z)
        position = a[1].lerp(b[1], weight)
        position.z = Z_CUT
        return (key, position, a[2].lerp(b[2], weight),
                a[3].lerp(b[3], weight).normalized())

    def emit(ring, smooth):
        face = []
        for key, point, uv, normal in ring:
            if key not in indices:
                indices[key] = len(points)
                points.append(point.copy())
            face.append(indices[key])
            samples.append((tuple(uv), tuple(normal)))
        faces.append((face, smooth))

    removed, sections = 0, 0
    mesh.calc_loop_triangles()
    for triangle in mesh.loop_triangles:
        corners = [corner(loop) for loop in triangle.loops]
        high = [c for c in corners if c[1].z > Z_CUT]
        if not high or all(abs(c[1].x) >= CENTRAL_HALF_WIDTH for c in high):
            emit(corners, mesh.polygons[triangle.polygon_index].use_smooth)
            continue
        assert all(abs(c[1].x) < CENTRAL_HALF_WIDTH for c in corners), "Cut reaches wing"
        removed += 1
        if len(high) == len(corners):
            continue
        ring, cuts = [], []
        for a, b in zip(corners, corners[1:] + corners[:1]):
            keep_a, keep_b = a[1].z <= Z_CUT, b[1].z <= Z_CUT
            if keep_a:
                ring.append(a)
            if keep_a != keep_b:
                cut = intersection(a, b)
                ring.append(cut)
                cuts.append(cut[0])
        a, b = cuts
        neighbours[a].add(b)
        neighbours[b].add(a)
        sections += 1
        for i in range(1, len(ring) - 1):
            emit([ring[0], ring[i], ring[i + 1]], mesh.polygons[triangle.polygon_index].use_smooth)

    assert removed and sections and all(len(v) == 2 for v in neighbours.values()), "Open section"
    remaining = set(neighbours)
    cap_faces = 0
    while remaining:
        first = min(remaining)
        ring, node, previous = [], first, None
        while node in remaining:
            remaining.remove(node)
            ring.append(node)
            next_node = min(neighbours[node] - {previous})
            previous, node = node, next_node
        assert node == first
        coords = [points[indices[key]] for key in ring]
        triangles = geometry.tessellate_polygon([coords])
        assert len(triangles) == len(ring) - 2, "Incomplete cap"
        for i, j, k in triangles:
            if (coords[j] - coords[i]).cross(coords[k] - coords[i]).z < 0:
                j, k = k, j
            cap = []
            for index in (i, j, k):
                co = coords[index]
                cap.append((ring[index], co, Vector((.44 + co.x, .38 + co.y)), Vector((0, 0, 1))))
            emit(cap, False)
        cap_faces += len(triangles)

    new_mesh = bpy.data.meshes.new(name)
    new_mesh.from_pydata(points, [], [face for face, smooth in faces])
    new_mesh.materials.append(mesh.materials[0])
    new_mesh.update()
    layer = new_mesh.uv_layers.new(name=mesh.uv_layers.active.name)
    for polygon, (_, smooth) in zip(new_mesh.polygons, faces):
        polygon.use_smooth = smooth
    for loop, (uv, normal) in enumerate(samples):
        layer.data[loop].uv = uv
    new_mesh.normals_split_custom_set([normal for uv, normal in samples])
    obj = bpy.data.objects.new(name, new_mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.matrix_world = source.matrix_world.copy()
    return obj, {"trimmed_source_triangles": removed, "closed_section_edges": sections,
                 "cap_triangles": cap_faces}


bpy.ops.wm.read_factory_settings(use_empty=True)
source_names = {key: "SM_ForgedSteelGreatsword_Guard_" + ("V1" if key == "factory" else key + "_V2")
                for key in OPTIONS}
with bpy.data.libraries.load(str(SOURCE), link=False) as (available, loaded):
    loaded.objects = list(source_names.values())

rows = {}
for key, source_name in source_names.items():
    source = bpy.data.objects[source_name]
    name = "SM_ForgedSteelGreatsword_Guard_" + key + "_ExecutionerSeat"
    obj, stats = build_seat(source, name)
    assert obj.location.length < 1e-7
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(filepath=str(HERE / (name + ".fbx")), use_selection=True,
                             object_types={"MESH"}, axis_forward="-Y", axis_up="Z",
                             add_leaf_bones=False, bake_anim=False, mesh_smooth_type="FACE",
                             use_tspace=True, use_triangles=True)
    rows[key] = {"source_mesh": source_name, "fbx": name + ".fbx", "mesh": name,
                 "object_path": f"{DESTINATION}/{name}.{name}", **stats}

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "ExecutionerGuardSeats.blend"), compress=True)
exports = {"blade_option": "executioner_blade", "factory_option": "factory",
           "destination": DESTINATION, "cut_z_cm": Z_CUT * 100, "material_slot": MATERIAL,
           "material": f"{ROOT}/V1/Materials/{MATERIAL}.{MATERIAL}",
           "mesh_by_guard": {key: row["object_path"] for key, row in rows.items()}, "guards": rows}
(HERE / "exports.json").write_text(json.dumps(exports, indent=2) + "\n", encoding="utf8")
print("EXECUTIONER_GUARD_SEATS_AUTHORED")
