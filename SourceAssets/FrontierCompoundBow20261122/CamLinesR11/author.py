"""Rebuild the six Frontier game meshes with backed side tracks on the two existing cams."""
from pathlib import Path
import json
import math
import os

import bmesh
import bpy
from mathutils import Vector

here = Path(__file__).resolve().parent
family = here.parent
output = here / "Export"
output.mkdir(exist_ok=True)
report = {}
hardware = ("UpperLimb", "LowerLimb", "UpperCam", "LowerCam", "ControlCable1", "ControlCable2")


def replace_side_tracks(cam, rig, side):
    bm = bmesh.new()
    bm.from_mesh(cam.data)
    cam_group = cam.vertex_groups[side + "_cam"].index
    cord_slot = cam.data.materials.find("M_Frontier_Cord")
    if cord_slot < 0:
        raise ValueError(cam.name + ": cord slot missing")
    by_vertex = set(bm.verts)
    discard = []
    while by_vertex:
        first = by_vertex.pop()
        todo, island = [first], [first]
        while todo:
            vertex = todo.pop()
            for edge in vertex.link_edges:
                other = edge.other_vert(vertex)
                if other in by_vertex:
                    by_vertex.remove(other)
                    island.append(other)
                    todo.append(other)
        # R2 modeled the outboard side tracks as two wire hoops with three wire spokes each.
        faces = {f for v in island for f in v.link_faces}
        if max(v.co.y for v in island) < -2.0 and all(f.material_index == cord_slot for f in faces):
            discard.append(island)
    if sorted(map(len, discard)) != [20] * 6 + [960] * 2:
        raise ValueError(f"{cam.name}: unexpected wheel topology {list(map(len, discard))}")
    bmesh.ops.delete(bm, geom=[v for group in discard for v in group], context="VERTS")

    # Derive both visible groove levels from this mesh's existing control-cable bones.
    hub = rig.data.bones[side + "_cam"].head_local
    first, second = (rig.data.bones[side + "_cable" + str(i)].head_local - hub for i in (0, 1))
    a, b = math.hypot(first.x, first.z), math.hypot(second.x, second.z)
    y0, y1 = first.y, second.y
    profile = [
        (.53, -.85), (a * .90, -1.35), (a + .13, y0 + .27),
        (a + .15, y0 + .16), (a - .085, y0 + .07), (a - .085, y0 - .07),
        (a + .12, y0 - .15), (a + .10, y0 - .21), (b + .15, y1 + .19),
        (b + .15, y1 + .14), (b - .085, y1 + .07), (b - .085, y1 - .07),
        (b + .12, y1 - .14), (b + .12, y1 - .20), (b - .08, y1 - .27),
        (b * .76, y1 - .28), (b * .71, y1 - .23), (.57, y1 - .23),
        (.49, y1 - .17), (.49, -.85),
    ]
    count = 64
    rings = []
    weights = bm.verts.layers.deform.verify()
    for radius, y in profile:
        ring = []
        for j in range(count):
            t = math.tau * j / count
            v = bm.verts.new(hub + Vector((radius * math.cos(t), y, radius * math.sin(t))))
            v[weights][cam_group] = 1.0
            ring.append(v)
        rings.append(ring)
    new_faces = []
    for i, row in enumerate(rings):
        adjacent = rings[(i + 1) % len(rings)]
        for j in range(count):
            k = (j + 1) % count
            f = bm.faces.new((row[j], row[k], adjacent[k], adjacent[j]))
            f.material_index = cord_slot
            f.smooth = True
            new_faces.append(f)
    bmesh.ops.recalc_face_normals(bm, faces=new_faces)
    bm.to_mesh(cam.data)
    bm.free()
    cam.data.update()


def export(name, objects, rig):
    scene = bpy.context.scene
    bpy.ops.object.select_all(action="DESELECT")
    copies = []
    for obj in objects:
        copy = obj.copy()
        copy.data = obj.data.copy()
        scene.collection.objects.link(copy)
        copy.hide_viewport = False
        copy.hide_set(False)
        copy.select_set(True)
        copies.append(copy)
    mesh = copies[0]
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.join()
    mesh.name = name
    rig.hide_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.fbx(filepath=str(output / (name + ".fbx")), use_selection=True,
        object_types={"MESH", "ARMATURE"}, axis_forward="-Y", axis_up="Z", apply_unit_scale=True,
        add_leaf_bones=False, bake_anim=False, mesh_smooth_type="FACE")
    report[name] = {
        "parts": [o.name for o in objects], "vertices": len(mesh.data.vertices),
        "material_slots": [slot.name for slot in mesh.material_slots],
        "removed_wire_islands_per_cam": 8,
    }
    bpy.data.objects.remove(mesh, do_unlink=True)


for source in ("RigContactR2/FrontierCompoundBow_R2.blend", "FrameVariantsR1/Frontier_Frames.blend",
               "EclipseFrameR1/Frontier_Eclipse.blend"):
    bpy.ops.wm.open_mainfile(filepath=str(family / source))
    scene = bpy.context.scene
    scene.frame_set(1)
    rig = scene.objects["Armature"]
    rig.data.pose_position = "REST"
    for side in ("upper", "lower"):
        replace_side_tracks(scene.objects[side.title() + "Cam"], rig, side)
    mechanism = [scene.objects[n] for n in hardware]
    if source.startswith("FrameVariants"):
        for kind in ("Swift", "Heavy", "Strong", "Steady"):
            export("SK_Frontier_" + kind + "Frame",
                   [scene.objects[kind + "_Riser"], *mechanism, scene.objects[kind + "_Panels"]], rig)
    elif source.startswith("Eclipse"):
        details = [o for o in scene.objects if o.type == "MESH" and o.name.startswith("Eclipse_")]
        export("SK_Frontier_Eclipse", [scene.objects["Riser"], *mechanism, *details], rig)
    else:
        export("SK_Frontier_Assembly", [scene.objects["Riser"], *mechanism], rig)
        review = os.environ.get("FRONTIER_WHEEL_REVIEW")
        if review:
            bpy.ops.wm.save_as_mainfile(filepath=str(Path(review) / "FactoryRevised.blend"), copy=True, compress=True)

Path(os.environ["FRONTIER_BATCH"], "meshes.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
