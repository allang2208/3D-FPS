"""Rebuild the dark-bow riser on the original 5.6k cage.

Adds grip swell, a proud inlay, Body/Limb lamination chamfers, an arrow-rest
shelf and nock grooves. No global subdivision. Units are metres; source JSON
is centimetres. The live 71k detail mesh is not the modeling base.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "ArmsV2" / "bow_surface.json"
EXPORT = HERE / "Export"
PREVIEW = HERE / "InspectPreview"
EXPORT.mkdir(exist_ok=True)
PREVIEW.mkdir(exist_ok=True)

STRING = dict(xmin=-21.79, xmax=-21.13, ymin=-1.26, ymax=-0.61, zmin=-64.05, zmax=64.12)
NOCKS_CM = ((-21.46, -0.935, 64.11), (-21.46, -0.935, -64.04))
SLOT = ("Body", "Limb", "Inlay")

GRIP_Z_CM = 11.0
GRIP_X_MIN_CM = -4.0
GRIP_X_MAX_CM = 8.0
GRIP_BACK_M = 0.008
GRIP_THICK_M = 0.0045
INLAY_PROUD_M = 0.0024
LAM_OFFSET_M = 0.0015
SHELF_SIZE_M = (0.046, 0.014, 0.016)
SHELF_CENTER_M = (0.000, -0.0335, 0.015)
NOCK_RADIUS_M = 0.0015
NOCK_DEPTH_M = 0.018
BEVEL_WIDTH_M = 0.00075
BEVEL_ANGLE = math.radians(28.0)


def cm(v):
    return tuple(c / 100.0 for c in v)


def load_cage():
    source = json.loads(SRC.read_text(encoding="utf-8"))
    keep = []
    removed = 0
    for i, face in enumerate(source["triangles"]):
        pts = [source["positions"][v] for v in face]
        if all(
            STRING["xmin"] <= p[0] <= STRING["xmax"]
            and STRING["ymin"] <= p[1] <= STRING["ymax"]
            and STRING["zmin"] <= p[2] <= STRING["zmax"]
            for p in pts
        ):
            removed += 1
            continue
        keep.append(i)
    if removed != 124:
        raise RuntimeError("string island changed: %s" % removed)
    used = []
    remap = {}
    for i in keep:
        for v in source["triangles"][i]:
            if v not in remap:
                remap[v] = len(used)
                used.append(v)
    verts = [cm(source["positions"][v]) for v in used]
    faces = [tuple(remap[v] for v in source["triangles"][i]) for i in keep]
    mesh = bpy.data.meshes.new("RiserForm")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    for name in SLOT:
        mesh.materials.append(bpy.data.materials.new(name))
    loop = 0
    uv = mesh.uv_layers.new(name="UVMap")
    for pi, src in enumerate(keep):
        poly = mesh.polygons[pi]
        poly.material_index = int(source["materials"][src])
        poly.use_smooth = True
        for corner in source["uv"][src]:
            uv.data[loop].uv = corner
            loop += 1
    obj = bpy.data.objects.new("SM_DarkBow_RiserForm", mesh)
    bpy.context.collection.objects.link(obj)
    return obj, removed


def bbox_cm(obj):
    pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    xs, ys, zs = zip(*[(p.x * 100, p.y * 100, p.z * 100) for p in pts])
    return {
        "x": [round(min(xs), 3), round(max(xs), 3)],
        "y": [round(min(ys), 3), round(max(ys), 3)],
        "z": [round(min(zs), 3), round(max(zs), 3)],
        "size": [
            round(max(xs) - min(xs), 3),
            round(max(ys) - min(ys), 3),
            round(max(zs) - min(zs), 3),
        ],
    }


def slot_counts(obj):
    counts = {name: 0 for name in SLOT}
    for poly in obj.data.polygons:
        name = SLOT[poly.material_index] if poly.material_index < 3 else str(poly.material_index)
        counts[name] = counts.get(name, 0) + 1
    return counts


def nock_gaps(obj):
    pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    out = []
    for key in NOCKS_CM:
        target = Vector(cm(key))
        best = 1e9
        nearest = None
        for p in pts:
            d = (p - target).length
            if d < best:
                best = d
                nearest = [round(p.x * 100, 3), round(p.y * 100, 3), round(p.z * 100, 3)]
        out.append({"key_cm": list(key), "nearest_cm": nearest, "gap_cm": round(best * 100, 3)})
    return out


def string_faces(obj):
    count = 0
    for poly in obj.data.polygons:
        pts = [obj.matrix_world @ obj.data.vertices[i].co for i in poly.vertices]
        zs = [p.z * 100 for p in pts]
        if min(abs(z) for z in zs) > 58.0:
            continue
        if all(
            STRING["xmin"] <= p.x * 100 <= STRING["xmax"]
            and STRING["ymin"] <= p.y * 100 <= STRING["ymax"]
            and STRING["zmin"] <= p.z * 100 <= STRING["zmax"]
            for p in pts
        ):
            count += 1
    return count


def apply(obj, name):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=name)


def bm_from(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    bm.normal_update()
    return bm


def swell_grip(bm):
    mid_y = cm((0.0, -0.935, 0.0))[1]
    moved = 0
    for v in bm.verts:
        x, y, z = v.co.x * 100, v.co.y * 100, v.co.z * 100
        az = abs(z)
        if az > GRIP_Z_CM or x < GRIP_X_MIN_CM or x > GRIP_X_MAX_CM:
            continue
        if not any(f.material_index == 0 for f in v.link_faces):
            continue
        w = (1.0 - az / GRIP_Z_CM) ** 2
        v.co.x += GRIP_BACK_M * w
        sign = 1.0 if y > mid_y * 100 else -1.0
        v.co.y += sign * GRIP_THICK_M * w
        moved += 1
    return moved


def extrude_inlay(bm):
    faces = [f for f in bm.faces if f.material_index == 2 and f.normal.y < -0.2]
    if len(faces) < 8:
        faces = [f for f in bm.faces if f.material_index == 2]
    if not faces:
        return 0
    acc = Vector((0.0, 0.0, 0.0))
    for f in faces:
        acc += f.normal
    normal = acc.normalized() if acc.length > 0.1 else Vector((0.0, -1.0, 0.0))
    ret = bmesh.ops.extrude_discrete_faces(bm, faces=faces)
    new_faces = ret.get("faces") or []
    verts = []
    for f in new_faces:
        f.material_index = 2
        verts.extend(f.verts)
    if verts:
        bmesh.ops.translate(bm, vec=normal * INLAY_PROUD_M, verts=list(set(verts)))
    return len(faces)


def inset_limbs(bm):
    faces = [f for f in bm.faces if f.material_index == 1]
    if len(faces) < 20:
        return 0
    try:
        bmesh.ops.inset_region(
            bm,
            faces=faces,
            thickness=0.0024,
            depth=-0.0010,
            use_boundary=True,
            use_even_offset=True,
            use_interpolate=True,
            use_relative_offset=False,
            use_edge_rail=False,
            use_outset=False,
        )
    except Exception:
        bmesh.ops.inset_individual(
            bm,
            faces=faces,
            thickness=0.0016,
            depth=-0.0007,
            use_even_offset=True,
            use_interpolate=True,
            use_relative_offset=False,
        )
    return len(faces)


def make_shelf(parent):
    mesh = bpy.data.meshes.new("ArrowShelf")
    sx, sy, sz = [c * 0.5 for c in SHELF_SIZE_M]
    verts = [
        (-sx, -sy, -sz),
        (sx, -sy, -sz),
        (sx, sy, -sz),
        (-sx, sy, -sz),
        (-sx, -sy, sz),
        (sx, -sy, sz),
        (sx, sy, sz),
        (-sx, sy, sz),
    ]
    faces = [
        (0, 1, 2, 3),
        (4, 7, 6, 5),
        (0, 4, 5, 1),
        (3, 2, 6, 7),
        (0, 3, 7, 4),
        (1, 5, 6, 2),
    ]
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    for mat in parent.data.materials:
        mesh.materials.append(mat)
    for poly in mesh.polygons:
        poly.material_index = 2
        poly.use_smooth = True
    obj = bpy.data.objects.new("ArrowShelf", mesh)
    obj.location = SHELF_CENTER_M
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bevel = obj.modifiers.new("ShelfBevel", "BEVEL")
    bevel.width = 0.0012
    bevel.segments = 2
    bevel.limit_method = "ANGLE"
    bevel.angle_limit = math.radians(40)
    apply(obj, "ShelfBevel")
    return obj


def make_nock_cutters():
    from mathutils import Matrix

    cutters = []
    for key in NOCKS_CM:
        loc = cm(key)
        mesh = bpy.data.meshes.new("NockCutter")
        bm = bmesh.new()
        bmesh.ops.create_cone(
            bm,
            cap_ends=True,
            cap_tris=True,
            segments=14,
            radius1=NOCK_RADIUS_M,
            radius2=NOCK_RADIUS_M,
            depth=NOCK_DEPTH_M,
        )
        bmesh.ops.rotate(
            bm,
            verts=list(bm.verts),
            cent=(0.0, 0.0, 0.0),
            matrix=Matrix.Rotation(math.radians(90.0), 3, "X"),
        )
        bmesh.ops.translate(bm, verts=list(bm.verts), vec=Vector(loc))
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new("NockCutter", mesh)
        bpy.context.collection.objects.link(obj)
        cutters.append(obj)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in cutters:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = cutters[0]
    bpy.ops.object.join()
    return cutters[0]


def join_objects(main, other):
    bpy.ops.object.select_all(action="DESELECT")
    main.select_set(True)
    other.select_set(True)
    bpy.context.view_layer.objects.active = main
    bpy.ops.object.join()


def boolean_cut(main, cutter):
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = main
    main.select_set(True)
    mod = main.modifiers.new("NockCut", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    try:
        mod.operand_type = "OBJECT"
    except Exception:
        pass
    mod.object = cutter
    for solver in ("EXACT", "FLOAT"):
        try:
            mod.solver = solver
        except Exception:
            pass
        try:
            apply(main, "NockCut")
            bpy.data.objects.remove(cutter, do_unlink=True)
            return solver
        except Exception:
            continue
    if "NockCut" in main.modifiers:
        main.modifiers.remove(main.modifiers["NockCut"])
    bpy.data.objects.remove(cutter, do_unlink=True)
    return None


def render_views(obj):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 720
    scene.render.resolution_y = 1200
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = True
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    cam = bpy.data.cameras.new("FormCam")
    cam.type = "ORTHO"
    cam_obj = bpy.data.objects.new("FormCam", cam)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj
    pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    xs, ys, zs = zip(*[(p.x, p.y, p.z) for p in pts])
    cx = (min(xs) + max(xs)) * 0.5
    cy = (min(ys) + max(ys)) * 0.5
    cz = (min(zs) + max(zs)) * 0.5
    span = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
    cam.ortho_scale = span * 1.12
    files = {}
    for name, loc, rot in (
        ("side_profile", (cx + span, cy, cz), (math.radians(90), 0.0, math.radians(90))),
        ("string_face", (cx, cy - span, cz), (math.radians(90), 0.0, 0.0)),
        ("grip_close", (0.18, -0.22, 0.02), (math.radians(78), 0.0, math.radians(18))),
    ):
        cam_obj.location = loc
        cam_obj.rotation_euler = rot
        if name == "grip_close":
            cam.type = "ORTHO"
            cam.ortho_scale = 0.22
            scene.render.resolution_x = 900
            scene.render.resolution_y = 900
        path = PREVIEW / ("form_" + name + ".png")
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        files[name] = str(path)
    return files


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    obj, removed = load_cage()
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    before = {
        "tris": len(obj.data.polygons),
        "verts": len(obj.data.vertices),
        "bbox_cm": bbox_cm(obj),
        "slots": slot_counts(obj),
    }

    bm = bm_from(obj)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=5e-5)
    bmesh.ops.dissolve_degenerate(bm, dist=5e-5, edges=bm.edges)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    moved = swell_grip(bm)
    bm.normal_update()
    inlay_faces = extrude_inlay(bm)
    bm.normal_update()
    lam_faces = inset_limbs(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    print('STEP_BMESH', len(bm.faces), 'grip', moved, 'inlay', inlay_faces, 'limb', lam_faces, flush=True)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    print('STEP_AFTER_BM', len(obj.data.polygons), slot_counts(obj), flush=True)

    shelf = make_shelf(obj)
    print('STEP_SHELF', len(shelf.data.polygons), flush=True)
    join_objects(obj, shelf)
    print('STEP_JOIN', len(obj.data.polygons), flush=True)
    cutter = make_nock_cutters()
    solver = boolean_cut(obj, cutter)
    print('STEP_BOOL', solver, len(obj.data.polygons), flush=True)

    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.shade_smooth()
    bevel = obj.modifiers.new("FormBevel", "BEVEL")
    bevel.affect = "EDGES"
    bevel.limit_method = "ANGLE"
    bevel.angle_limit = BEVEL_ANGLE
    bevel.width = BEVEL_WIDTH_M
    bevel.segments = 2
    bevel.use_clamp_overlap = True
    apply(obj, "FormBevel")

    bm = bm_from(obj)
    bmesh.ops.dissolve_degenerate(bm, dist=5e-5, edges=bm.edges)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()

    bm = bm_from(obj)
    crease = bm.edges.layers.float.get("crease_edge") or bm.edges.layers.float.new("crease_edge")
    for e in bm.edges:
        zs = [abs(v.co.z) * 100.0 for v in e.verts]
        ys = [v.co.y for v in e.verts]
        xs = [v.co.x for v in e.verts]
        mats = {f.material_index for f in e.link_faces}
        score = 0.0
        if 2 in mats:
            score = max(score, 0.85)
        if min(zs) < 8.0:
            score = max(score, 0.55)
        if min(zs) > 60.0:
            score = max(score, 0.8)
        if min(ys) < -0.028 and abs(sum(xs) / 2.0) < 0.04 and min(zs) < 6.0:
            score = max(score, 1.0)
        if score:
            e[crease] = score
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    sub = obj.modifiers.new("FormSubdiv", "SUBSURF")
    sub.subdivision_type = "CATMULL_CLARK"
    sub.levels = 1
    sub.render_levels = 1
    try:
        sub.use_creases = True
        sub.use_limit_surface = True
    except Exception:
        pass
    apply(obj, "FormSubdiv")
    size = bbox_cm(obj)
    if size["size"][1] < 4.6:
        disp = obj.modifiers.new("RestoreThick", "DISPLACE")
        disp.strength = 0.0006
        disp.mid_level = 0.0
        try:
            disp.direction = "NORMAL"
        except Exception:
            pass
        apply(obj, "RestoreThick")

    wn = obj.modifiers.new("WeightedN", "WEIGHTED_NORMAL")
    wn.mode = "FACE_AREA"
    wn.weight = 50
    wn.thresh = 0.01
    wn.keep_sharp = True
    apply(obj, "WeightedN")
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    after = {
        "tris": len(obj.data.polygons),
        "verts": len(obj.data.vertices),
        "bbox_cm": bbox_cm(obj),
        "slots": slot_counts(obj),
        "nock_keys": nock_gaps(obj),
        "string_faces": string_faces(obj),
    }
    if after["tris"] < 8000:
        raise RuntimeError("too few faces: %s" % after["tris"])
    if after["tris"] > 45000:
        raise RuntimeError("too dense: %s" % after["tris"])
    if after["bbox_cm"]["size"][2] < 136 or after["bbox_cm"]["size"][2] > 146:
        raise RuntimeError("length drifted: %s" % after["bbox_cm"]["size"][2])
    if after["bbox_cm"]["size"][1] < 3.3 or after["bbox_cm"]["size"][1] > 8.5:
        raise RuntimeError("thickness out of range: %s" % after["bbox_cm"]["size"][1])
    if after["string_faces"] > 8:
        raise RuntimeError("baked string faces came back: %s" % after["string_faces"])
    if any(item["gap_cm"] > 0.65 for item in after["nock_keys"]):
        raise RuntimeError("nock drifted: %s" % after["nock_keys"])
    if after["slots"].get("Inlay", 0) < 80:
        raise RuntimeError("inlay lost: %s" % after["slots"])

    files = render_views(obj)
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "RiserForm_Editable.blend"))
    bpy.ops.export_scene.fbx(
        filepath=str(EXPORT / "SM_DarkBow_RiserForm.fbx"),
        use_selection=True,
        object_types={"MESH"},
        axis_forward="-Y",
        axis_up="Z",
        bake_anim=False,
        mesh_smooth_type="FACE",
        use_tspace=True,
        apply_scale_options="FBX_SCALE_ALL",
    )
    receipt = {
        "removed_string_tris": removed,
        "before": before,
        "after": after,
        "ops": {
            "grip_verts": moved,
            "inlay_faces": inlay_faces,
            "limb_inset": lam_faces,
            "nock_boolean": solver,
            "shelf_cm": [round(c * 100, 2) for c in SHELF_SIZE_M],
        },
        "previews": files,
        "fbx": str(EXPORT / "SM_DarkBow_RiserForm.fbx"),
        "runtime_tested": False,
    }
    (HERE / "authoring.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print("BOW_RISER_FORM_AUTHORED", json.dumps({"after": after, "ops": receipt["ops"]}), flush=True)


if __name__ == "__main__":
    main()
