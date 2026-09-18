"""Round 4: clean per-gun well seat measurement.

M4 / QBZ: the factory magazine is its own object. AKM: the magazine is a
welded shell inside the receiver object -> bmesh loose-part whose bbox sits in
the magazine region.

Per gun outputs: well axis (top-segment PCA of the mag), mouth plane
(receiver surface closest point along the axis near the mag), neck cross
section at the mouth, and a render with the mag object highlighted via a
translucent red shell copy (so it stays visible inside/around the receiver).
"""
import bpy
import bmesh
import json
import math
import os
from mathutils import Matrix, Vector
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.normpath(os.path.join(HERE, "..", "Reference"))
SA = r"D:\FPS3D\FPSGAME\SourceAssets"

GUNS = {
    "M4": os.path.join(SA, r"M4HK416Replica20260910\SK_M4_FoldingSights_HK416.fbx"),
    "AKM": os.path.join(SA, r"AKMSoviet20260911\SK_AKM_MannyNative.fbx"),
    "QBZ": os.path.join(SA, r"QBZ191MagazineSeat20260913\SK_QBZ191_Manny.fbx"),
}
# search box for the AKM magazine loose part
AKM_MAG_BOX = ((0.02, 0.12), (0.14, 0.34), (-0.34, -0.07))


def import_file(path):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    return [o for o in bpy.context.scene.objects if o not in before]


def bone_world(arm_obj, name):
    arm = arm_obj.data
    arm.pose_position = "REST"
    bpy.context.view_layer.update()
    return arm_obj.matrix_world @ arm.bones[name].matrix_local


def loose_parts_world(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    seen = set()
    out = []
    mw = obj.matrix_world
    for v in bm.verts:
        if v.index in seen:
            continue
        stack = [v]; group = []; seen.add(v.index)
        while stack:
            cur = stack.pop(); group.append(cur)
            for e in cur.link_edges:
                o = e.other_vert(cur)
                if o.index not in seen:
                    seen.add(o.index); stack.append(o)
        pts = [mw @ x.co for x in group]
        out.append(pts)
    bm.free()
    return out


def pca_axis(pts):
    arr = np.array([[p.x, p.y, p.z] for p in pts])
    c = arr.mean(axis=0)
    _, _, vt = np.linalg.svd(arr - c)
    a = Vector(vt[0])
    if a.z < 0:
        a = -a
    return a, Vector(c)


def flat_mat(ob, color, alpha=1.0, emit=0.0):
    mat = bpy.data.materials.new(ob.name + "_f")
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = 0.6
    if alpha < 1.0:
        b.inputs["Alpha"].default_value = alpha
        mat.blend_method = 'BLEND'
    if emit:
        b.inputs["Emission Color"].default_value = (*color, 1)
        b.inputs["Emission Strength"].default_value = emit
    ob.data.materials.clear()
    ob.data.materials.append(mat)


def setup_render(tag, center, look, scale=0.5):
    scene = bpy.context.scene
    cd = bpy.data.cameras.new("c"); cd.type = 'ORTHO'; cd.ortho_scale = scale
    cam = bpy.data.objects.new("c", cd); scene.collection.objects.link(cam)
    d = Vector(look).normalized()
    z = -d; x = Vector((0, 0, 1)).cross(z).normalized(); y = z.cross(x)
    cam.matrix_world = Matrix.Translation(Vector(center) - d * 2) @ Matrix((x, y, z)).transposed().to_4x4()
    scene.camera = cam
    sun = bpy.data.lights.new("s", 'SUN'); sun.energy = 3.5
    so = bpy.data.objects.new("s", sun); scene.collection.objects.link(so)
    so.rotation_euler = (math.radians(55), 0, math.radians(35))
    w = bpy.data.worlds.new("w"); w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.92, 0.92, 0.94, 1)
    scene.world = w
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = scene.render.resolution_y = 1000
    scene.render.filepath = os.path.join(REF, f"render_{tag}.png")
    bpy.ops.render.render(write_still=True)


report = {}
for gun, path in GUNS.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = import_file(path)
    arm = next(o for o in objs if o.type == "ARMATURE")
    sw = bone_world(arm, "WPN_SOCKET_Magazine")
    st = sw.translation
    meshes = [o for o in objs if o.type == "MESH"]

    if gun == "M4":
        mag = next(o for o in meshes if o.name.startswith("M4_Magazine"))
        recv = [o for o in meshes if o is not mag and not o.name.startswith("SK_Manny")]
    elif gun == "QBZ":
        mag = next(o for o in meshes if o.name.startswith("QBZ191_Magazine"))
        recv = [o for o in meshes if o is not mag and not o.name.startswith("SK_Manny")]
    else:
        body = next(o for o in meshes if o.name.startswith("AKM_"))
        recv = [body]
        best = None
        (x0, x1), (y0, y1), (z0, z1) = AKM_MAG_BOX
        for pts in loose_parts_world(body):
            n = len(pts)
            if n < 100:
                continue
            xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
            ov = (min(max(xs), x1) - max(min(xs), x0)) * (min(max(ys), y1) - max(min(ys), y0)) * (min(max(zs), z1) - max(min(zs), z0))
            if ov > 0 and (best is None or ov > best[0]):
                best = (ov, pts)
        mag_pts = best[1]
        mag = None

    mw = mag.matrix_world if mag else None
    if mag:
        mag_pts = [mw @ v.co for v in mag.data.vertices]
    arr = np.array([[p.x, p.y, p.z] for p in mag_pts])
    zmax, zmin = arr[:, 2].max(), arr[:, 2].min()
    top = arr[arr[:, 2] > zmin + (zmax - zmin) * 0.72]
    axis, ctop = pca_axis([Vector(row) for row in top])
    _, cmag = pca_axis([Vector(row) for row in arr])

    # mouth: receiver surface lowest along world Z within a tight XY window
    # around the mag neck center, excluding the rear slab (trigger guard).
    cx, cy = cmag.x, cmag.y
    cands = []
    for o in recv:
        mwo = o.matrix_world
        for v in o.data.vertices:
            p = mwo @ v.co
            if abs(p.x - cx) < 0.020 and cy - 0.005 < p.y < cy + 0.075 and p.z < cmag.z + 0.09:
                cands.append(p)
    mouth_z = min(p.z for p in cands)
    # neck cross-section at the mouth plane (mag slice +-6mm around mouth_z)
    neck = [p for p in mag_pts if abs(p.z - mouth_z) < 0.006]
    nu = [p.x for p in neck]; nv = [p.y for p in neck]
    # axis param at mouth
    t_mouth = (Vector((cmag.x, cmag.y, mouth_z)) - st).dot(axis)
    t_top = (Vector((cmag.x, cmag.y, zmax)) - st).dot(axis)
    t_bot = (Vector((cmag.x, cmag.y, zmin)) - st).dot(axis)
    report[gun] = {
        "socket": [round(q, 4) for q in st],
        "axis": [round(q, 4) for q in axis],
        "tilt_deg": round(math.degrees(math.acos(axis.z)), 2),
        "mag_center": [round(q, 4) for q in cmag],
        "top_center": [round(q, 4) for q in ctop],
        "mouth_z": round(mouth_z, 4),
        "mouth_point": [round(cx, 4), round(cy, 4), round(mouth_z, 4)],
        "mouth_along_axis_from_socket": round(t_mouth, 4),
        "top_along_axis": round(t_top, 4),
        "bottom_along_axis": round(t_bot, 4),
        "neck_x": [round(min(nu), 4), round(max(nu), 4)] if neck else None,
        "neck_y": [round(min(nv), 4), round(max(nv), 4)] if neck else None,
        "insert_depth_available": round(t_top - t_mouth, 4),
        "n_mag": len(mag_pts),
        "mag_z_range": [round(zmin, 4), round(zmax, 4)],
    }

    # render: flat receiver, translucent red shell copy of the mag
    for o in recv:
        if o.type == "MESH":
            flat_mat(o, (0.55, 0.56, 0.58))
    if mag:
        shell = mag.copy()
        shell.data = mag.data
        bpy.context.scene.collection.objects.link(shell)
        flat_mat(shell, (0.85, 0.1, 0.1), alpha=0.45)
    else:
        cloud = make_nothing = None
        import bmesh as _bm
        me = bpy.data.meshes.new("AKM_MAG")
        bm = _bm.new()
        for p in mag_pts:
            bm.verts.new(p)
        bm.to_mesh(me); bm.free()
        cob = bpy.data.objects.new("AKM_MAG", me)
        bpy.context.scene.collection.objects.link(cob)
        flat_mat(cob, (0.85, 0.1, 0.1), alpha=0.45, emit=0.5)
    mid = Vector((cmag.x, cmag.y, (zmax + zmin) / 2))
    setup_render(f"{gun}_seat_side", mid, Vector((1, 0, 0)), 0.45)
    setup_render(f"{gun}_seat_front", mid, Vector((0, -1, 0)), 0.35)

out = os.path.join(REF, "well.json")
with open(out, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=1)
print("WELL_DONE", out)
