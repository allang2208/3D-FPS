"""Rebuild the large drum with parametric hard-surface modelling. v2

Neutral frame: drum centred at origin, disc axis along +X (left/right on the
gun), tower rising along +Z toward the well, +Y toward the muzzle.

Per gun: place the accepted old drum in gun-world (same composition as the
runtime), take the new drum centre from the old disc centroid, stretch the
tower so its top lands on the measured well seat, then bake back into that
gun's asset frame (identity mounts and per-rifle materials keep working).
Exports three FBXs + a neutral preview, and renders gun composites.
"""
import bpy
import bmesh
import json
import math
import os
from mathutils import Matrix, Vector
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
REF = os.path.join(ROOT, "Reference")
OUT = os.path.join(ROOT, "FBX", "drum")
SA = r"D:\FPS3D\FPSGAME\SourceAssets"

OLD_DRUMS = {
    "M4": (os.path.join(SA, r"WeaponAttachmentFinish20260913\FBX\M4\drum.fbx"), "asset"),
    "AKM": (os.path.join(SA, r"WeaponAttachmentFinish20260913\FBX\AKM\drum.fbx"), "socket"),
    "QBZ": (os.path.join(SA, r"QBZ191Attachments20260913\SM_QBZ191_drum.fbx"), "socket_mag0"),
}
GUNS = {
    "M4": os.path.join(SA, r"M4HK416Replica20260910\SK_M4_FoldingSights_HK416.fbx"),
    "AKM": os.path.join(SA, r"AKMSoviet20260911\SK_AKM_MannyNative.fbx"),
    "QBZ": os.path.join(SA, r"QBZ191MagazineSeat20260913\SK_QBZ191_Manny.fbx"),
}
SEATS = {
    "M4": Vector((0.058, 0.257, -0.070)),
    "AKM": Vector((0.062, 0.243, -0.105)),
    "QBZ": Vector((0.054, 0.260, -0.056)),
}
TOWER_CROSS = {"M4": (0.022, 0.032), "AKM": (0.026, 0.034), "QBZ": (0.024, 0.033)}
NEUTRAL_TOWER = (0.024, 0.034)
MAG0_T = Vector((2.8564492822624743e-05, -0.08145000040531158, -0.07817225158214569))

R = 0.0615
T = 0.077
SEG = 40
HUB_R = 0.023
HUB_P = 0.0022
BOLT_R = 0.0034
BOLT_P = 0.003
BOLT_N = 6
BOLT_CIRCLE = 0.043
AXLE_R = 0.006
WIN_R = 0.017
WIN_DEPTH = 0.0045
EMBED = 0.013


class MeshData:
    def __init__(self):
        self.verts = []
        self.faces = []  # (tuple(indices), material)

    def add(self, co, mat=0):
        self.verts.append(Vector(co))
        return len(self.verts) - 1

    def face(self, idx, mat=0):
        self.faces.append((tuple(idx), mat))


def cyl(md, center, x_sign, radius, half, segs, mat):
    """Small cylinder whose axis is X, centred at (center[0] ± half layout)."""
    cx, cy, cz = center
    a_ring, b_ring = [], []
    for i in range(segs):
        a = 2 * math.pi * i / segs
        y, z = radius * math.cos(a), radius * math.sin(a)
        a_ring.append(md.add((cx - half, cy + y, cz + z), mat))
        b_ring.append(md.add((cx + half, cy + y, cz + z), mat))
    for i in range(segs):
        j = (i + 1) % segs
        md.face((a_ring[i], a_ring[j], b_ring[j], b_ring[i]), mat)
    md.face(a_ring[::-1], mat)
    md.face(b_ring, mat)


def build_neutral():
    md = MeshData()
    bands = [
        (-T/2,          R - 0.0012),
        (-T/2 + 0.004,  R),
        (-0.008,        R),
        (0.0,           R + 0.0013),
        (0.008,         R),
        (T/2 - 0.004,   R),
        (T/2,           R - 0.0012),
    ]
    prot = [(math.cos(2*math.pi*i/SEG), math.sin(2*math.pi*i/SEG)) for i in range(SEG)]
    ring_first = ring_last = None
    prev = None
    for x, rad in bands:
        ring = [md.add((x, cv*rad, cu*rad), 0) for (cu, cv) in prot]
        if ring_first is None:
            ring_first = ring
        if prev:
            for i in range(SEG):
                j = (i + 1) % SEG
                md.face((prev[i], prev[j], ring[j], ring[i]), 0)
        ring_last = ring
        prev = ring
    md.face(ring_first[::-1], 0)
    md.face(ring_last, 0)

    for sign in (-1, 1):
        cyl(md, (sign*(T/2 + HUB_P/2), 0, 0), sign, HUB_R, HUB_P/2 + 0.0006, 32, 1)
        cyl(md, (sign*(T/2 + HUB_P + 0.0014), 0, 0), sign, AXLE_R, 0.0015, 16, 1)
        for k in range(BOLT_N):
            a = 2*math.pi*k/BOLT_N
            by, bz = BOLT_CIRCLE*math.cos(a), BOLT_CIRCLE*math.sin(a)
            cyl(md, (sign*(T/2 + BOLT_P/2 + 0.0004), by, bz), sign, BOLT_R, BOLT_P/2, 6, 1)

    # index window: rim + wall + recessed floor + indicator dot, left face (-X)
    n_win = 28
    win_x = -T/2 - 0.0006
    outer, rim, flo = [], [], []
    for i in range(n_win):
        a = 2*math.pi*i/n_win
        cy, cz = WIN_R*math.cos(a), WIN_R*math.sin(a)
        outer.append(md.add((win_x, cy, cz), 2))
        rim.append(md.add((win_x - 0.0012, cy, cz), 2))
        flo.append(md.add((win_x - WIN_DEPTH, cy*0.88, cz*0.88), 2))
    for i in range(n_win):
        j = (i + 1) % n_win
        md.face((outer[j], outer[i], rim[i], rim[j]), 2)
        md.face((rim[i], rim[j], flo[j], flo[i]), 2)
    md.face(flo[::-1], 2)
    cyl(md, (win_x - WIN_DEPTH - 0.0013, 0.008, 0.004), -1, 0.0035, 0.0012, 12, 2)

    # tower with fairing skirt
    W0, D0 = NEUTRAL_TOWER
    z_j = R - EMBED
    z_s = R - 0.002
    z_f = R + 0.010
    z_t = R + 0.068
    # rounded rect profile
    rr = []
    corners = [(0.2, 0.2, 0.0), (-0.2, 0.2, math.pi/2), (-0.2, -0.2, math.pi), (0.2, -0.2, math.pi*1.5)]
    rrr = 0.3
    for cx, cy, a0 in corners:
        for i in range(4):
            a = a0 + (math.pi/2)*i/3
            rr.append((cx + rrr*math.cos(a), cy + rrr*math.sin(a)))
    ded = [rr[0]]
    for p in rr[1:]:
        if (p[0]-ded[-1][0])**2 + (p[1]-ded[-1][1])**2 > 1e-12:
            ded.append(p)
    def ring(z, sw, sd):
        return [md.add((lx*W0*0.5*sw, ly*D0*0.5*sd, z), 0) for (lx, ly) in ded]
    rings = [ring(z_j, 1.5, 1.45), ring(z_s, 1.42, 1.38), ring(z_f, 1.06, 1.05),
             ring(z_f + 0.012, 1.0, 1.0), ring(z_t - 0.006, 1.0, 1.0), ring(z_t, 0.94, 0.95)]
    for (a, b) in zip(rings[:-1], rings[1:]):
        n = len(a)
        for i in range(n):
            j = (i + 1) % n
            md.face((a[i], a[j], b[j], b[i]), 0)
    md.face(rings[-1][::-1], 0)
    return md


def md_to_object(md, name):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bv = [bm.verts.new(v) for v in md.verts]
    for idx, mat in md.faces:
        try:
            f = bm.faces.new([bv[i] for i in idx])
            f.material_index = mat
        except ValueError:
            pass
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    for f in me.polygons:
        f.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    es = ob.modifiers.new("EdgeSplit", 'EDGE_SPLIT')
    es.split_angle = math.radians(28)
    for nm, base, rough, met in (("DrumPolymer", (0.05, 0.052, 0.056), 0.55, 0.0),
                                 ("DrumFasteners", (0.10, 0.10, 0.11), 0.42, 0.85),
                                 ("DrumIndex", (0.07, 0.072, 0.078), 0.5, 0.0)):
        m = bpy.data.materials.new(nm)
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*base, 1)
        b.inputs["Roughness"].default_value = rough
        b.inputs["Metallic"].default_value = met
        me.materials.append(m)
    return ob


def old_placed(gun):
    path, mode = OLD_DRUMS[gun]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
    mo = next(o for o in bpy.context.scene.objects if o.type == "MESH")
    mw = mo.matrix_world
    raw = [mw @ v.co for v in mo.data.vertices]
    if mode == "asset":
        return raw, None
    bpy.ops.import_scene.fbx(filepath=GUNS[gun])
    arm = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
    arm.data.pose_position = "REST"
    bpy.context.view_layer.update()
    sw = arm.matrix_world @ arm.data.bones["WPN_SOCKET_Magazine"].matrix_local
    if mode == "socket":
        return [sw @ v for v in raw], sw
    return [sw @ (v + MAG0_T) for v in raw], sw


def drum_centre(pts):
    arr = np.array([[p.x, p.y, p.z] for p in pts])
    c0 = arr.mean(axis=0)
    d = np.linalg.norm(arr - c0, axis=1)
    fat = arr[d > 0.5 * d.max()]
    return Vector(fat.mean(axis=0))


def export_md(md, name):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ob = md_to_object(md, name)
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    path = os.path.join(OUT, name + ".fbx")
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'MESH'},
                             axis_forward='-Y', axis_up='Z', bake_anim=False,
                             mesh_smooth_type='FACE', use_tspace=True)
    return ob


def composite(gun, gun_path, md, placed_pts):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=gun_path)
    for o in [x for x in bpy.context.scene.objects if x not in before and x.type == "MESH"]:
        m = bpy.data.materials.new(o.name + "_f"); m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (0.52, 0.53, 0.55, 1)
        b.inputs["Roughness"].default_value = 0.6
        o.data.materials.clear()
        o.data.materials.append(m)
        o.hide_render = o.name.startswith("SK_Manny")
    placed_ob = md_to_object(md, "drum_placed")
    scene = bpy.context.scene
    cd = bpy.data.cameras.new("c"); cd.type = 'ORTHO'; cd.ortho_scale = 0.5
    cam = bpy.data.objects.new("c", cd); scene.collection.objects.link(cam)
    ctr = Vector((sum(p.x for p in placed_pts)/len(placed_pts),
                  sum(p.y for p in placed_pts)/len(placed_pts),
                  sum(p.z for p in placed_pts)/len(placed_pts)))
    d = Vector((1, -0.55, 0.3)).normalized()
    z = -d; x = Vector((0, 0, 1)).cross(z).normalized(); y = z.cross(x)
    cam.matrix_world = Matrix.Translation(ctr - d*2) @ Matrix((x, y, z)).transposed().to_4x4()
    scene.camera = cam
    sun = bpy.data.lights.new("s", 'SUN'); sun.energy = 3.5
    so = bpy.data.objects.new("s", sun); scene.collection.objects.link(so)
    so.rotation_euler = (math.radians(55), 0, math.radians(35))
    w = bpy.data.worlds.new("w"); w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.9, 0.9, 0.92, 1)
    scene.world = w
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = scene.render.resolution_y = 1000
    scene.render.filepath = os.path.join(REF, f"drum_new_{gun}.png")
    bpy.ops.render.render(write_still=True)


def main():
    md = build_neutral()
    print("DRUM tris:", sum(len(f[0]) - 2 for f in md.faces), "verts:", len(md.verts))
    os.makedirs(OUT, exist_ok=True)
    report = {}
    placed_all = {}
    for gun in ("M4", "AKM", "QBZ"):
        pts, sw = old_placed(gun)
        C = drum_centre(pts)
        zax = (SEATS[gun] - C).normalized()
        yref = Vector((0, 1, 0))
        yax = (yref - yref.dot(zax) * zax).normalized()
        xax = yax.cross(zax).normalized()
        M = Matrix((xax, yax, zax)).transposed().to_4x4()
        L = (SEATS[gun] - C).length
        w, d = TOWER_CROSS[gun]
        s_w, s_d = w / NEUTRAL_TOWER[0], d / NEUTRAL_TOWER[1]
        z_emb = R - EMBED
        z_f = R + 0.012
        placed = []
        for v in md.verts:
            p = Vector(v)
            if p.z > z_f:
                t = (p.z - z_f) / ((R + 0.068) - z_f)
                p.z = z_f + t * (L - z_f)
            if p.z > z_emb:
                fade = min(1.0, (p.z - z_emb) / 0.01)
                p.x *= 1 + (s_w - 1) * fade
                p.y *= 1 + (s_d - 1) * fade
            placed.append(C + M @ p)
        placed_all[gun] = placed
        if gun == "M4":
            baked = placed
        elif gun == "AKM":
            baked = [sw.inverted() @ p for p in placed]
        else:
            baked = [sw.inverted() @ (p - MAG0_T) for p in placed]
        md_bake = MeshData()
        md_bake.verts = baked
        md_bake.faces = md.faces
        name = {"M4": "SM_M4_LargeDrum_new", "AKM": "SM_AKM_drum_new", "QBZ": "SM_QBZ191_drum_new"}[gun]
        export_md(md_bake, name)
        zs = [p.z for p in placed]
        report[gun] = {"centre": [round(c, 4) for c in C], "seat_dist": round(L, 4),
                       "placed_z": [round(min(zs), 4), round(max(zs), 4)],
                       "top": [round(c, 4) for c in placed[int(np.argmax([p.z for p in placed]))]]}
        print("BAKED", gun, json.dumps(report[gun]))
    with open(os.path.join(REF, "drum_new_report.json"), "w") as f:
        json.dump(report, f, indent=1)
    # composites
    for gun in ("M4", "AKM", "QBZ"):
        # rebuild placed mesh data with per-gun transform for the render
        pts, sw = old_placed(gun)
        C = drum_centre(pts)
        zax = (SEATS[gun] - C).normalized()
        yref = Vector((0, 1, 0))
        yax = (yref - yref.dot(zax) * zax).normalized()
        xax = yax.cross(zax).normalized()
        M = Matrix((xax, yax, zax)).transposed().to_4x4()
        L = (SEATS[gun] - C).length
        w, d = TOWER_CROSS[gun]
        s_w, s_d = w / NEUTRAL_TOWER[0], d / NEUTRAL_TOWER[1]
        z_emb = R - EMBED
        z_f = R + 0.012
        placed = []
        for v in md.verts:
            p = Vector(v)
            if p.z > z_f:
                t = (p.z - z_f) / ((R + 0.068) - z_f)
                p.z = z_f + t * (L - z_f)
            if p.z > z_emb:
                fade = min(1.0, (p.z - z_emb) / 0.01)
                p.x *= 1 + (s_w - 1) * fade
                p.y *= 1 + (s_d - 1) * fade
            placed.append(C + M @ p)
        md_gun = MeshData()
        md_gun.verts = placed
        md_gun.faces = md.faces
        composite(gun, GUNS[gun], md_gun, placed)
    print("DRUM_BUILD_DONE")


main()
