"""Review the duplicate-band extended magazines against their own factory part.

Both meshes live in the rifle's mesh frame, so putting them in one scene with the
factory part shifted sideways is exactly the comparison the user judges: same
camera, same lighting, "factory magazine" next to "extended magazine". Four
orthographic views (side / front / top / bottom) plus a per-slice vertex profile
along the length axis, so a truncated or missing section is visible by eye and in
the numbers at the same time.

Run: blender -b -P render_dupb_review.py
"""
import bmesh
import bpy
import json
import math
import os
import numpy as np

SA = r"D:\FPS3D\FPSGAME\SourceAssets"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
OUT = os.path.join(ROOT, "Reference")
BINS = 44

JOBS = {
    "M4": dict(source=os.path.join(SA, "M4HK416Replica20260910",
                                   "SK_M4_FoldingSights_HK416.fbx"),
               built=os.path.join(ROOT, "FBX", "SM_ExtMag_M440_arc.fbx"),
               match="magazine"),
    "QBZ": dict(source=os.path.join(SA, "PhantomRearGripIntegration20260913",
                                    "QBZ191", "SK_QBZ191_Manny.fbx"),
                built=os.path.join(ROOT, "FBX", "SM_ExtMag_QBZ40_arc.fbx"),
                match="magazine"),
}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_fbx(path):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    return [o for o in bpy.context.scene.objects if o not in before]


def pick_magazine(match):
    for ob in bpy.context.scene.objects:
        if ob.type == "MESH":
            for material in ob.data.materials:
                if material and match in material.name.lower():
                    return ob
    raise RuntimeError("no magazine object found (%s)" % match)


def keep_magazine_slot(ob, match):
    index = next((i for i, m in enumerate(ob.data.materials)
                  if m and match in m.name.lower()), None)
    if index is None:
        raise RuntimeError("no magazine slot on " + ob.name)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    drop = [face for face in bm.faces if face.material_index != index]
    if drop:
        bmesh.ops.delete(bm, geom=drop, context='FACES')
    loose = [vert for vert in bm.verts if not vert.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def world_points(ob):
    return np.array([tuple(ob.matrix_world @ v.co) for v in ob.data.vertices])


def open_edges(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    border = sum(1 for edge in bm.edges if len(edge.link_faces) == 1)
    non_manifold = sum(1 for edge in bm.edges if len(edge.link_faces) > 2)
    bm.free()
    return border, non_manifold


def profile(points, lo, hi, bins=BINS):
    """Vertices per slice along the length axis, plus the slice's own spread."""
    span = hi - lo
    counts = []
    for index in range(bins):
        a = lo + span * index / bins
        b = lo + span * (index + 1) / bins
        slab = points[(points[:, 2] >= a) & (points[:, 2] < b)]
        counts.append(int(len(slab)))
    return counts


def frame_camera(points, name):
    lo, hi = points.min(axis=0), points.max(axis=0)
    mid = (lo + hi) / 2.0
    dim = float(max(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]))
    data = bpy.data.cameras.new(name)
    data.type = 'ORTHO'
    data.ortho_scale = dim * 1.25
    cam = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam.location = (float(mid[0]) + dim * 2.0, float(mid[1]), float(mid[2]))
    cam.rotation_mode = 'XYZ'
    return cam, (float(mid[0]), float(mid[1]), float(mid[2]))


# view -> (camera offset direction, euler); the camera has to move to the matching
# side of the part, otherwise the front/top/bottom shots come out empty.
VIEWS = {
    "side": ((1.0, 0.0, 0.0), (math.radians(90), 0.0, math.radians(90))),
    "front": ((0.0, -1.0, 0.0), (math.radians(90), 0.0, 0.0)),
    "top": ((0.0, 0.0, 1.0), (0.0, 0.0, 0.0)),
    "bottom": ((0.0, 0.0, -1.0), (math.radians(180), 0.0, 0.0)),
}

report = {}

for gun, cfg in JOBS.items():
    reset()
    scene = bpy.context.scene          # read_factory_settings replaces the scene
    import_fbx(cfg["source"])
    factory = pick_magazine(cfg["match"])
    keep_magazine_slot(factory, cfg["match"])
    bpy.context.view_layer.objects.active = factory
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    factory.name = "factory_" + gun
    factory_pts = world_points(factory)

    # The built mesh is authored in the same rifle frame, so it can live in this
    # scene untouched; the factory part only moves sideways for the eye.
    for ob in import_fbx(cfg["built"]):
        if ob.type == "MESH":
            built = ob
    built.name = "ext_" + gun
    built_pts = world_points(built)

    # Separate the two parts diagonally: offsetting along a single axis would put
    # them on top of each other in one of the two horizontal views.
    dims = built_pts.max(axis=0) - built_pts.min(axis=0)
    factory.location.x += float(dims[0]) + 0.05
    factory.location.y += float(dims[1]) + 0.05
    bpy.context.view_layer.update()

    all_pts = np.vstack([world_points(factory), world_points(built)])
    cam, mid = frame_camera(all_pts, "ReviewCam_" + gun)
    distance = float(max(all_pts.max(axis=0) - all_pts.min(axis=0))) * 2.0
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = 'BOTH'
    scene.display.shading.color_type = 'SINGLE'
    scene.display.shading.single_color = (0.32, 0.33, 0.35)
    scene.display.shading.show_object_outline = True
    scene.render.resolution_x, scene.render.resolution_y = 1400, 1000

    # One pass per part: the rifle has to be out of frame, otherwise its own
    # factory magazine sits on top of the extended one and hides the seam.
    passes = {
        "pair": [factory, built],
        "factory": [factory],
        "ext": [built],
    }
    for tag, keep in passes.items():
        for ob in scene.objects:
            if ob.type == 'MESH':
                ob.hide_render = ob not in keep
            elif ob.type == 'CAMERA':
                continue
            else:
                ob.hide_render = True
        for view, (direction, eul) in VIEWS.items():
            cam.location = tuple(mid[i] + direction[i] * distance for i in range(3))
            cam.rotation_euler = eul
            scene.render.filepath = os.path.join(
                OUT, "dupb_review_%s_%s_%s.png" % (gun, tag, view))
            bpy.ops.render.render(write_still=True)
    for ob in scene.objects:
        if ob.type == 'MESH':
            ob.hide_render = False

    # Profiles run on the factory magazine's own length axis so the two are
    # directly comparable: index 0 = floor-plate end, last = throat end.
    f_lo, f_hi = float(factory_pts[:, 2].min()), float(factory_pts[:, 2].max())
    b_lo, b_hi = float(built_pts[:, 2].min()), float(built_pts[:, 2].max())
    u_lo, u_hi = min(f_lo, b_lo), max(f_hi, b_hi)
    b_border, b_nonmanifold = open_edges(built)
    f_border, _ = open_edges(factory)
    report[gun] = {
        "factory_length_cm": round(f_hi - f_lo, 2),
        "built_length_cm": round(b_hi - b_lo, 2),
        "factory_floor_to_throat_m": [round(f_lo, 4), round(f_hi, 4)],
        "built_floor_to_throat_m": [round(b_lo, 4), round(b_hi, 4)],
        "built_dims_cm": [round(float(v), 2) for v in
                          (built_pts.max(axis=0) - built_pts.min(axis=0))],
        "factory_border_edges": f_border,
        "built_border_edges": b_border,
        "built_non_manifold_edges": b_nonmanifold,
        "factory_profile_own_range": profile(factory_pts, f_lo, f_hi),
        "built_profile_own_range": profile(built_pts, b_lo, b_hi),
        "union_profile_factory": profile(factory_pts, u_lo, u_hi, 56),
        "union_profile_built": profile(built_pts, u_lo, u_hi, 56),
        "views": sorted(VIEWS),
    }
    print("DUPB_REVIEW " + gun + " " + json.dumps(report[gun]), flush=True)

with open(os.path.join(OUT, "dupb_review.json"), "w", encoding="utf-8") as handle:
    json.dump(report, handle, indent=1, ensure_ascii=False)
print("DUPB_REVIEW_REPORT " + json.dumps({g: {"factory_cm": r["factory_length_cm"],
                                              "built_cm": r["built_length_cm"],
                                              "built_border": r["built_border_edges"]}
                                          for g, r in report.items()}))
