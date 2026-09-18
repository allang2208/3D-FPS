"""Round 5: definitive well seat per gun.

For each gun the factory magazine becomes a red translucent surface shell
(M4/QBZ: object copy; AKM: the welded loose part rebuilt as a mesh). Side and
front renders are made, then the PNG pixels are scanned: the mag's topmost
visible row inside its column band is the well-mouth line (everything above
is hidden inside the receiver).

Numeric: mag z-bin centroids within [mouth, mouth+3cm] give the well axis by
least squares; cross-sections just inside the mouth (well throat) and just
below it (visible seam) come from the same bins.

Output: Reference/seat_final.json + render_final_*.png
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
AKM_MAG_BOX = ((0.02, 0.12), (0.14, 0.34), (-0.34, -0.07))
RES = 1000
ORTHO = 0.45


def import_file(path):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    return [o for o in bpy.context.scene.objects if o not in before]


def loose_parts(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    seen = set()
    out = []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack = [v]; group = []; seen.add(v.index)
        while stack:
            cur = stack.pop(); group.append(cur.index)
            for e in cur.link_edges:
                o = e.other_vert(cur)
                if o.index not in seen:
                    seen.add(o.index); stack.append(o)
        out.append(group)
    bm.free()
    return out


def flat(ob, color, alpha=1.0):
    m = bpy.data.materials.new(ob.name + "_f"); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = 0.65
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        m.blend_method = 'BLEND'
    ob.data.materials.clear()
    ob.data.materials.append(m)


def setup_cam(center, look, scale):
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
    scene.render.resolution_x = scene.render.resolution_y = RES
    return scene


def render_to(path, scene):
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def red_mask(png):
    img = bpy.data.images.load(png)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    bpy.data.images.remove(img)
    # Blender rows bottom-up; red material: R high, G low.
    red = (px[:, :, 0] > 0.45) & (px[:, :, 1] < 0.55) & (px[:, :, 0] - px[:, :, 1] > 0.12)
    return red[::-1]  # top-down rows


report = {}
for gun, path in GUNS.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = import_file(path)
    meshes = [o for o in objs if o.type == "MESH"]
    if gun == "M4":
        mag = next(o for o in meshes if o.name.startswith("M4_Magazine"))
        recv = [o for o in meshes if o is not mag and not o.name.startswith("SK_Manny")]
        shell = mag.copy(); shell.data = mag.data
        bpy.context.scene.collection.objects.link(shell)
        mw = mag.matrix_world
        mpts = [mw @ v.co for v in mag.data.vertices]
    elif gun == "QBZ":
        mag = next(o for o in meshes if o.name.startswith("QBZ191_Magazine"))
        recv = [o for o in meshes if o is not mag and not o.name.startswith("SK_Manny")]
        shell = mag.copy(); shell.data = mag.data
        bpy.context.scene.collection.objects.link(shell)
        mw = mag.matrix_world
        mpts = [mw @ v.co for v in mag.data.vertices]
    else:
        body = next(o for o in meshes if o.name.startswith("AKM_"))
        recv = [body]
        (x0, x1), (y0, y1), (z0, z1) = AKM_MAG_BOX
        mw_body = body.matrix_world
        best = None
        for grp in loose_parts(body):
            if len(grp) < 100:
                continue
            pts = [mw_body @ body.data.vertices[i].co for i in grp]
            xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
            ov = (min(max(xs), x1) - max(min(xs), x0)) * (min(max(ys), y1) - max(min(ys), y0)) * (min(max(zs), z1) - max(min(zs), z0))
            if ov > 0 and (best is None or ov > best[0]):
                best = (ov, grp, pts)
        _, grp, mpts = best
        me = bpy.data.meshes.new("AKM_MAG_SHELL")
        bm = bmesh.new()
        bverts = [bm.verts.new(mw_body @ body.data.vertices[i].co) for i in grp]
        remap = {vi: k for k, vi in enumerate(grp)}
        for p in body.data.polygons:
            try:
                bm.faces.new([bverts[remap[vi]] for vi in p.vertices])
            except (ValueError, KeyError):
                pass
        bm.to_mesh(me); bm.free()
        shell = bpy.data.objects.new("AKM_MAG_SHELL", me)
        shell.matrix_world = Matrix.Identity(4)
        bpy.context.scene.collection.objects.link(shell)

    flat(shell, (0.85, 0.12, 0.12), alpha=0.55)
    for o in recv:
        if o.type == "MESH":
            flat(o, (0.55, 0.56, 0.58))

    arr = np.array([[p.x, p.y, p.z] for p in mpts])
    zmin, zmax = arr[:, 2].min(), arr[:, 2].max()
    cx, cy = arr[:, 0].mean(), arr[:, 1].mean()
    scene = setup_cam((cx, cy, (zmin + zmax) / 2), Vector((1, 0, 0)), ORTHO)
    side_png = os.path.join(REF, f"render_final_{gun}_side.png")
    render_to(side_png, scene)
    front_png = os.path.join(REF, f"render_final_{gun}_front.png")
    render_to(front_png, scene)  # camera reused? rebuild camera for front
    # rebuild camera for front view
    cd = bpy.data.cameras.new("c2"); cd.type = 'ORTHO'; cd.ortho_scale = ORTHO
    cam2 = bpy.data.objects.new("c2", cd); scene.collection.objects.link(cam2)
    d = Vector((0, -1, 0))
    z = -d; x = Vector((0, 0, 1)).cross(z).normalized(); y = z.cross(x)
    cam2.matrix_world = Matrix.Translation(Vector((cx, cy, (zmin + zmax) / 2)) - d * 2) @ Matrix((x, y, z)).transposed().to_4x4()
    scene.camera = cam2
    render_to(front_png, scene)

    mask = red_mask(side_png)
    # column band of the mag: columns where red exists
    cols = np.where(mask.any(axis=0))[0]
    band = cols[(cols > cols.min() + 5) & (cols < cols.max() - 5)]
    top_rows = []
    for c in band:
        r = np.where(mask[:, c])[0]
        top_rows.append(r.min())
    top_rows = np.array(top_rows)
    mouth_row = np.percentile(top_rows, 20)  # near-topmost robust
    # pixel -> world: rows top-down; center row RES/2 at z_center; scale ORTHO/RES per px
    z_center = (zmin + zmax) / 2
    mouth_z = z_center + (RES / 2 - mouth_row) * (ORTHO / RES)
    # axis: centroids of mag bins in [mouth_z, mouth_z+0.03]
    bins = []
    zz = mouth_z
    while zz < mouth_z + 0.031:
        sel = arr[(arr[:, 2] >= zz) & (arr[:, 2] < zz + 0.005)]
        if len(sel) > 3:
            bins.append(sel.mean(axis=0))
        zz += 0.005
    bins = np.array(bins)
    A = np.stack([bins[:, 2], np.ones(len(bins))], axis=1)
    sol_x, *_ = np.linalg.lstsq(A, bins[:, 0], rcond=None)
    sol_y, *_ = np.linalg.lstsq(A, bins[:, 1], rcond=None)
    axis = Vector((sol_x[0], sol_y[0], 1.0)).normalized()
    if axis.z < 0:
        axis = -axis
    tilt = math.degrees(math.acos(axis.z))

    def cross_at(z0, z1):
        sel = arr[(arr[:, 2] >= z0) & (arr[:, 2] < z1)]
        if len(sel) < 4:
            return None
        return {
            "x": [round(sel[:, 0].min(), 4), round(sel[:, 0].max(), 4)],
            "y": [round(sel[:, 1].min(), 4), round(sel[:, 1].max(), 4)],
            "w_x": round(sel[:, 0].max() - sel[:, 0].min(), 4),
            "d_y": round(sel[:, 1].max() - sel[:, 1].min(), 4),
            "n": len(sel),
        }

    report[gun] = {
        "mouth_z": round(mouth_z, 4),
        "mouth_row_px": round(float(mouth_row), 1),
        "axis": [round(q, 4) for q in axis],
        "tilt_deg": round(tilt, 2),
        "lean_forward": round(-axis.y, 4),
        "throat_inside": cross_at(mouth_z + 0.004, mouth_z + 0.014),
        "seam_below": cross_at(mouth_z - 0.022, mouth_z - 0.008),
        "mag_z": [round(zmin, 4), round(zmax, 4)],
        "mag_center_xy": [round(float(cx), 4), round(float(cy), 4)],
        "n_mag": len(mpts),
    }

out = os.path.join(REF, "seat_final.json")
with open(out, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=1)
print("SEAT_FINAL_DONE", out)
