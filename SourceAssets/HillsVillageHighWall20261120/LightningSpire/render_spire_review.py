"""Render multi-angle Day/Night Cycles reviews & Workshop card plate for SM_LightningSpirePreview."""
import json
import math
import os
import random
import struct
import zipfile
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
MESHZIP = HERE / "SM_LightningSpirePreview.meshzip"
TEXDIR = HERE / "PropTextures"
OUT = Path(os.environ.get("SPIRE_REVIEW_OUT", r"F:\FPSGAMEData\ArtReviews\HighVillageDefense\LightningSpireModel-20261127"))
OUT.mkdir(parents=True, exist_ok=True)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def load_tex(name, non_color=False):
    path = str(TEXDIR / name)
    img = bpy.data.images.load(path, check_existing=True)
    if non_color:
        img.colorspace_settings.name = "Non-Color"
    return img


def make_pbr_material(slot, night_mode=False):
    mat = bpy.data.materials.new(slot)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    uv = nt.nodes.new("ShaderNodeTexCoord")

    def sample(suffix, non_color=False):
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = load_tex(f"{slot}_{suffix}.png", non_color=non_color)
        nt.links.new(uv.outputs["UV"], n.inputs["Vector"])
        return n

    tb = sample("base_color", False)
    tr = sample("roughness", True)
    tm = sample("metallic", True)
    tn = sample("normal", True)

    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nmap.inputs["Strength"].default_value = 0.85
    nt.links.new(tn.outputs["Color"], nmap.inputs["Color"])

    nt.links.new(tb.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tr.outputs["Color"], bsdf.inputs["Roughness"])
    nt.links.new(tm.outputs["Color"], bsdf.inputs["Metallic"])
    nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])

    em_path = TEXDIR / f"{slot}_emissive.png"
    if em_path.exists():
        te = sample("emissive", True)
        em_col = (0.18, 0.78, 1.0) if slot == "SpireRuneGlow" else (0.30, 0.72, 1.0)
        strength = (9.5 if night_mode else 4.2) if slot == "SpireRuneGlow" else (11.0 if night_mode else 4.8)
        mul = nt.nodes.new("ShaderNodeVectorMath")
        mul.operation = "SCALE"
        mul.inputs[0].default_value = em_col
        nt.links.new(te.outputs["Color"], mul.inputs["Scale"])
        # Principled BSDF in Blender 5.x exposes Emission Color + Emission Strength
        bsdf.inputs["Emission Color"].default_value = (*em_col, 1.0)
        pow_node = nt.nodes.new("ShaderNodeMath")
        pow_node.operation = "MULTIPLY"
        pow_node.inputs[1].default_value = strength
        nt.links.new(te.outputs["Color"], pow_node.inputs[0])
        nt.links.new(pow_node.outputs["Value"], bsdf.inputs["Emission Strength"])

    return mat


def load_meshzip(path, night_mode=False):
    scene = bpy.context.scene
    with zipfile.ZipFile(path) as z:
        meta = json.loads(z.read("mesh.json"))
        mesh_data = bpy.data.meshes.new("SM_LightningSpirePreview")
        verts, tris, mats, uvs = [], [], [], []
        for idx, slot in enumerate(meta["materials"]):
            mesh_data.materials.append(make_pbr_material(slot, night_mode=night_mode))
            vraw = z.read(f"{idx}/vertices")
            iraw = z.read(f"{idx}/indices")
            uvraw = z.read(f"{idx}/uv")
            vcount = len(vraw) // 12
            voff = len(verts)
            vf = struct.unpack(f"<{vcount * 3}f", vraw)
            uvf = struct.unpack(f"<{vcount * 2}f", uvraw)
            for k in range(vcount):
                x, y, zc = vf[k * 3], vf[k * 3 + 1], vf[k * 3 + 2]
                verts.append((x * 0.01, -y * 0.01, zc * 0.01))
            indices = struct.unpack(f"<{len(iraw) // 4}I", iraw)
            for k in range(0, len(indices), 3):
                i0, i1, i2 = indices[k], indices[k + 1], indices[k + 2]
                tris.append((voff + i0, voff + i2, voff + i1))
                mats.append(idx)
                for vi in (i0, i2, i1):
                    uvs.append((uvf[vi * 2], 1.0 - uvf[vi * 2 + 1]))
        mesh_data.from_pydata(verts, [], tris)
        uv_layer = mesh_data.uv_layers.new(name="UVMap")
        for li, uv_val in enumerate(uvs):
            uv_layer.data[li].uv = uv_val
        for p, m_idx in zip(mesh_data.polygons, mats):
            p.material_index = m_idx
            p.use_smooth = True
        mesh_data.update()
        obj = bpy.data.objects.new("SM_LightningSpirePreview", mesh_data)
        scene.collection.objects.link(obj)
        return obj


def add_ground(night_mode=False):
    bpy.ops.mesh.primitive_plane_add(size=90.0, location=(0, 0, -0.002))
    floor = bpy.data.materials.new("StoneDeck")
    floor.use_nodes = True
    bsdf = floor.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.025, 0.030, 0.036, 1.0) if night_mode else (0.14, 0.135, 0.125, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.84
    bpy.context.object.data.materials.append(floor)


def add_scale_mannequin():
    """Subtle translucent 1.75 m operator silhouette at rear -X lectern for scale verification."""
    scene = bpy.context.scene
    mat = bpy.data.materials.new("OperatorScaleRef")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.55, 0.62, 0.70, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.8
    bsdf.inputs["Alpha"].default_value = 0.28
    # Simple capsule+head stand-in standing at x = -1.25 m facing +X
    bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=0.19, depth=1.42, location=(-1.28, 0.0, 0.71))
    body = bpy.context.object
    body.data.materials.append(mat)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=0.115, location=(-1.28, 0.0, 1.62))
    head = bpy.context.object
    head.data.materials.append(mat)


def add_arc_ribbon(pts, mat, r=0.011):
    curve = bpy.data.curves.new("Arc", "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = r
    curve.bevel_resolution = 2
    sp = curve.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        sp.points[i].co = (p[0], p[1], p[2], 1.0)
    obj = bpy.data.objects.new("Arc", curve)
    obj.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(obj)


def setup_arcs():
    rng = random.Random(202611)
    arc_core = bpy.data.materials.new("ArcCore")
    arc_core.use_nodes = True
    bsdf = arc_core.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.55, 0.90, 1.0, 1.0)
    bsdf.inputs["Emission Color"].default_value = (0.20, 0.78, 1.0, 1.0)
    bsdf.inputs["Emission Strength"].default_value = 11.0

    arc_halo = bpy.data.materials.new("ArcHalo")
    arc_halo.use_nodes = True
    hb = arc_halo.node_tree.nodes.get("Principled BSDF")
    hb.inputs["Base Color"].default_value = (0.08, 0.52, 1.0, 1.0)
    hb.inputs["Emission Color"].default_value = (0.08, 0.55, 1.0, 1.0)
    hb.inputs["Emission Strength"].default_value = 4.2
    hb.inputs["Alpha"].default_value = 0.34

    def jagged(a, b, jitter=0.075, n=8):
        va, vb = Vector(a), Vector(b)
        pts = [va]
        for k in range(1, n):
            t = k / n
            p = va.lerp(vb, t)
            off = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * jitter * math.sin(t * math.pi)
            pts.append(p + off)
        pts.append(vb)
        return [(p.x, p.y, p.z) for p in pts]

    # Arcs surging from crystal core (0,0,2.86) to apex corona orb (0,0,3.58) and discharging down-range (+X)
    for sy in (-1, 1):
        p_up = jagged((0.0, sy * 0.09, 2.86), (0.0, sy * 0.03, 3.58), 0.065, 7)
        add_arc_ribbon(p_up, arc_core, 0.011)
        add_arc_ribbon(p_up, arc_halo, 0.032)
    main_bolt = jagged((0.0, 0.0, 3.58), (2.55, 0.06, 1.72), 0.16, 11)
    fork_bolt = jagged((0.95, 0.04, 2.88), (2.40, -0.42, 1.55), 0.14, 8)
    add_arc_ribbon(main_bolt, arc_core, 0.018)
    add_arc_ribbon(main_bolt, arc_halo, 0.052)
    add_arc_ribbon(fork_bolt, arc_core, 0.011)
    add_arc_ribbon(fork_bolt, arc_halo, 0.034)


def setup_world_and_lights(mode="day"):
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new("Studio")
    if mode == "night":
        scene.world.color = (0.002, 0.004, 0.011)
        lights = [
            ("MoonRim", "AREA", (2.8, 3.2, 5.2), 14.0, 2.2, (0.40, 0.56, 0.95)),
            ("CoolFill", "AREA", (-3.5, -2.5, 2.4), 5.5, 2.5, (0.30, 0.45, 0.85)),
        ]
    elif mode == "plate":
        scene.world.color = (0.12, 0.13, 0.14)
        lights = [
            ("SoftKey", "AREA", (-1.8, -3.6, 5.0), 420.0, 3.5, (1.0, 0.86, 0.68)),
            ("SoftRim", "AREA", (1.8, 3.6, 3.2), 510.0, 3.5, (0.75, 0.84, 1.0)),
        ]
    else:
        scene.world.color = (0.14, 0.16, 0.19)
        lights = [
            ("DayKey", "AREA", (-2.8, -3.5, 5.4), 560.0, 3.8, (1.0, 0.90, 0.76)),
            ("DayRim", "AREA", (3.2, 3.0, 3.6), 440.0, 3.6, (0.72, 0.85, 1.0)),
            ("FrontFill", "AREA", (2.0, -3.0, 2.0), 180.0, 3.0, (0.95, 0.96, 1.0)),
        ]
    for name, kind, loc, energy, sz, col in lights:
        ld = bpy.data.lights.new(name, kind)
        ld.energy = energy
        ld.color = col
        ld.shape = "DISK"
        ld.size = sz
        ob = bpy.data.objects.new(name, ld)
        scene.collection.objects.link(ob)
        ob.location = loc
        target = Vector((0, 0, 1.85))
        ob.rotation_euler = (target - Vector(loc)).to_track_quat("-Z", "Y").to_euler()

    if mode in ("night", "plate"):
        pt = bpy.data.lights.new("CrystalGlow", "POINT")
        pt.energy = 85.0 if mode == "night" else 35.0
        pt.color = (0.28, 0.78, 1.0)
        pt.shadow_soft_size = 0.25
        ob = bpy.data.objects.new("CrystalGlow", pt)
        scene.collection.objects.link(ob)
        ob.location = (0.0, 0.0, 2.84)

    if mode == "night":
        pt2 = bpy.data.lights.new("DrumGlow", "POINT")
        pt2.energy = 14.0
        pt2.color = (0.25, 0.76, 1.0)
        pt2.shadow_soft_size = 0.35
        ob2 = bpy.data.objects.new("DrumGlow", pt2)
        scene.collection.objects.link(ob2)
        ob2.location = (-0.75, 0.0, 0.85)


def render_cam(filename, loc, aim, res_x, res_y, ortho_scale=None, lens=38.0, fmt="PNG"):
    scene = bpy.context.scene
    cam_d = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", cam_d)
    scene.collection.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    if ortho_scale is not None:
        cam_d.type = "ORTHO"
        cam_d.ortho_scale = ortho_scale
    else:
        cam_d.lens = lens
    scene.camera = cam
    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.resolution_percentage = 100
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    if fmt == "JPEG":
        scene.render.image_settings.file_format = "JPEG"
        scene.render.image_settings.quality = 92
    else:
        scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(OUT / filename)
    bpy.ops.render.render(write_still=True)


def main():
    # 1. Day Hero 3/4 (+X aiming forward-right toward camera)
    clear_scene()
    load_meshzip(MESHZIP, night_mode=False)
    add_ground(night_mode=False)
    setup_world_and_lights("day")
    render_cam("01-day-hero-34.png", (3.65, -3.55, 2.75), (0.0, 0.0, 1.85), 960, 1080, lens=40.0)

    # 2. Day Side Elevation (-X operator rear on left, +X horns on right, 1.75m human scale ref)
    clear_scene()
    load_meshzip(MESHZIP, night_mode=False)
    add_ground(night_mode=False)
    add_scale_mannequin()
    setup_world_and_lights("day")
    render_cam("02-day-side-profile.png", (-0.15, -5.6, 1.95), (-0.15, 0.0, 1.85), 960, 1080, ortho_scale=4.3)

    # 3. Crown Detail Close-Up (coils, insulators, crystal, gyro rings, forward discharge horns)
    clear_scene()
    load_meshzip(MESHZIP, night_mode=False)
    setup_world_and_lights("day")
    render_cam("03-closeup-crown.png", (1.65, -1.75, 2.85), (0.08, 0.0, 2.52), 960, 960, lens=45.0)

    # 4. Night Raid Silhouette & Arc Glow
    clear_scene()
    load_meshzip(MESHZIP, night_mode=True)
    add_ground(night_mode=True)
    setup_arcs()
    setup_world_and_lights("night")
    render_cam("04-night-raid-glow.png", (3.85, -3.25, 2.70), (0.30, 0.0, 1.95), 960, 1080, lens=38.0)

    # 5. Workshop Upgrade Card Plate (matching workshop_plates.py camera angle & 672x322 aspect)
    clear_scene()
    obj = load_meshzip(MESHZIP, night_mode=False)
    add_ground(night_mode=True)
    setup_world_and_lights("plate")
    scene = bpy.context.scene
    bpy.context.view_layer.update()
    direction = Vector((0.48, -1.0, 0.45)).normalized()
    center = Vector((0.0, 0.0, 1.85))
    size = 3.70
    cam_d = bpy.data.cameras.new("Plate")
    cam = bpy.data.objects.new("Plate", cam_d)
    scene.collection.objects.link(cam)
    cam.location = center + direction * size * 3.0
    cam.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
    cam_d.type = "ORTHO"
    cam_d.clip_end = size * 25.0
    bpy.context.view_layer.update()
    proj = cam.matrix_world.inverted()
    xy = [proj @ (obj.matrix_world @ v.co) for v in obj.data.vertices]
    xs = [q.x for q in xy]
    ys = [q.y for q in xy]
    cam_d.ortho_scale = max(max(xs) - min(xs), (max(ys) - min(ys)) * 672.0 / 322.0) * 1.16
    cam.location += cam.rotation_euler.to_quaternion() @ Vector(((max(xs) + min(xs)) * 0.5, (max(ys) + min(ys)) * 0.5, 0.0))
    scene.camera = cam
    scene.render.resolution_x = 672
    scene.render.resolution_y = 322
    scene.render.resolution_percentage = 100
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 91
    scene.render.filepath = str(OUT / "LightningSpire.jpg")
    bpy.ops.render.render(write_still=True)
    print(f"RENDERED SPIRE REVIEW -> {OUT}")


if __name__ == "__main__":
    main()
