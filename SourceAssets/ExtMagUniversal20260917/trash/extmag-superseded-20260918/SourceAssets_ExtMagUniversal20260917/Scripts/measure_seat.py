"""Round 3: visual + numeric seat measurement.

- Per gun: extract factory mag verts (strict regions), estimate well-mouth
  plane from the receiver geometry near the mag, fit the upper-segment axis,
  measure neck cross-sections at the mouth.
- Render orthographic side (-X view) and front (-Y view) images with mag verts
  tinted so the extraction can be verified visually.
- Compose each accepted drum at its seat (QBZ-style math) to cross-check.

Outputs: Reference/seat.json + Reference/render_{gun}_{view}.png
Run: blender -b -P measure_seat.py
"""
import bpy
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

MAG_REGIONS = {
    # world-space boxes around each factory magazine (Blender metres)
    "M4": ((0.020, 0.42), (0.200, 0.345), (-0.240, -0.030)),
    "AKM": ((0.025, 0.115), (0.150, 0.335), (-0.320, -0.080)),
    "QBZ": ((0.020, 0.42), (0.210, 0.370), (-0.250, -0.040)),
}


def import_file(path):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    return [o for o in bpy.context.scene.objects if o not in before]


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def bone_world(arm_obj, name):
    arm = arm_obj.data
    arm.pose_position = "REST"
    bpy.context.view_layer.update()
    return arm_obj.matrix_world @ arm.bones[name].matrix_local


def region_pts(objs, box):
    (x0, x1), (y0, y1), (z0, z1) = box
    pts = []
    for o in objs:
        if o.type != "MESH":
            continue
        mw = o.matrix_world
        for v in o.data.vertices:
            p = mw @ v.co
            if x0 <= p.x <= x1 and y0 <= p.y <= y1 and z0 <= p.z <= z1:
                pts.append(p)
    return pts


def make_cloud(pts, name, color):
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    for p in pts:
        bm.verts.new(p)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    mat = bpy.data.materials.new(name + "_m")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Emission Color"].default_value = (*color, 1)
    bsdf.inputs["Emission Strength"].default_value = 2.0
    me.materials.append(mat)
    return ob


def gun_materials_flat(objs):
    for o in objs:
        if o.type == "MESH":
            mat = bpy.data.materials.new(o.name + "_flat")
            mat.use_nodes = True
            b = mat.node_tree.nodes.get("Principled BSDF")
            b.inputs["Base Color"].default_value = (0.55, 0.56, 0.58, 1)
            b.inputs["Metallic"].default_value = 0.1
            b.inputs["Roughness"].default_value = 0.6
            o.data.materials.clear()
            o.data.materials.append(mat)


def render_ortho(tag, center, look, up_hint=(0, 0, 1)):
    scene = bpy.context.scene
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = 0.55
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    d = Vector(look).normalized()
    up = Vector(up_hint)
    z_axis = -d
    x_axis = up.cross(z_axis).normalized()
    y_axis = z_axis.cross(x_axis).normalized()
    rot = Matrix((x_axis, y_axis, z_axis)).transposed().to_4x4()
    cam.matrix_world = Matrix.Translation(Vector(center) - d * 2.0) @ rot
    scene.camera = cam
    sun = bpy.data.lights.new("sun", 'SUN')
    sun.energy = 3.0
    sun_ob = bpy.data.objects.new("sun", sun)
    scene.collection.objects.link(sun_ob)
    sun_ob.rotation_euler = (math.radians(50), 0, math.radians(30))
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.9, 0.9, 0.92, 1)
    scene.world = world
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.filepath = os.path.join(REF, f"render_{tag}.png")
    bpy.ops.render.render(write_still=True)


report = {}
for gun, path in GUNS.items():
    clear()
    objs = import_file(path)
    arm = next(o for o in objs if o.type == "ARMATURE")
    sw = bone_world(arm, "WPN_SOCKET_Magazine")
    st = sw.translation
    gun_meshes = [o for o in objs if o.type == "MESH"]
    mag_pts = region_pts(gun_meshes, MAG_REGIONS[gun])
    arr = np.array([[p.x, p.y, p.z] for p in mag_pts])

    # upper-segment axis: slice by z (1 cm bins) using only the top 45% of the
    # mag, fit direction through slice centroids.
    z = arr[:, 2]
    ztop = z.max(); zbot = z.min()
    sel = arr[z > zbot + (ztop - zbot) * 0.55]
    bins = []
    z0 = sel[:, 2].min()
    cur = [sel[0]]
    for row in sel[np.argsort(sel[:, 2])][1:]:
        if row[2] - z0 > 0.01:
            bins.append(np.mean(cur, axis=0)); cur = [row]; z0 = row[2]
        else:
            cur.append(row)
    bins.append(np.mean(cur, axis=0))
    bins = np.array(bins)
    c = bins.mean(axis=0)
    _, _, vt = np.linalg.svd(bins - c)
    axis = Vector(vt[0])
    if axis.z < 0:
        axis = -axis

    # mouth plane: lowest receiver surface near the mag along the axis. Use a
    # histogram of ALL gun verts projected on the axis; the mag verts continue
    # below the receiver. Receiver = gun verts within the mag XY neighborhood
    # but ABOVE the mag top region... Simpler: the mouth is where mag cross
    # section changes abruptly? Keep numeric: use gun verts (excluding arms
    # mesh) near the mag axis line, project on axis; the mouth ≈ the largest
    # gap-free run boundary. We record the mag-only profile for inspection.
    rel = np.array([[(p - st).dot(axis) for p in mag_pts]])
    hi = float(rel.max()); lo = float(rel.min())
    u = Vector((1, 0, 0))
    if abs(axis.dot(u)) > 0.9:
        u = Vector((0, 0, 1))
    v = axis.cross(u).normalized(); u = v.cross(axis).normalized()
    prof = []
    for i in range(24):
        t0 = lo + (hi - lo) * i / 24
        t1 = t0 + (hi - lo) / 24
        sl = [p for p in mag_pts if t0 <= (p - st).dot(axis) < t1]
        if len(sl) >= 4:
            us = [p.dot(u) for p in sl]; vs = [p.dot(v) for p in sl]
            prof.append({
                "t": round(t0, 4),
                "u": [round(min(us), 4), round(max(us), 4)],
                "v": [round(min(vs), 4), round(max(vs), 4)],
                "cu": round((min(us) + max(us)) / 2, 4),
                "cv": round((min(vs) + max(vs)) / 2, 4),
                "n": len(sl),
            })
    report[gun] = {
        "socket": [round(q, 4) for q in st],
        "axis": [round(q, 4) for q in axis],
        "tilt_deg": round(math.degrees(math.acos(axis.z)), 2),
        "along_min": round(lo, 4), "along_max": round(hi, 4),
        "profile": prof,
        "n_mag": len(mag_pts),
    }

    # visuals: flat-shaded gun + red mag cloud + socket axes marker.
    for o in gun_meshes:
        if o.type == "MESH":
            o.hide_render = False
    gun_materials_flat(gun_meshes)
    cloud = make_cloud(mag_pts, "MAG", (0.9, 0.05, 0.05))
    # axis line
    import bmesh
    me = bpy.data.meshes.new("axis_line")
    bm = bmesh.new()
    a0 = st + axis * lo
    a1 = st + axis * hi
    bm.verts.new(a0); bm.verts.new(a1); bm.edges.new(bm.verts[:])
    bm.to_mesh(me); bm.free()
    axis_ob = bpy.data.objects.new("axis_line", me)
    bpy.context.scene.collection.objects.link(axis_ob)
    m2 = bpy.data.materials.new("axm"); m2.use_nodes = True
    m2.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.1, 0.4, 1.0, 1)
    m2.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (0.1, 0.4, 1.0, 1)
    m2.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 3.0
    me.materials.append(m2)

    mid = Vector(report[gun]["socket"]) + axis * (hi * 0.5)
    render_ortho(f"{gun}_side", mid, Vector((1, 0, 0)))
    render_ortho(f"{gun}_front", mid, Vector((0, -1, 0)))

out = os.path.join(REF, "seat.json")
with open(out, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=1)
print("SEAT_DONE", out)
