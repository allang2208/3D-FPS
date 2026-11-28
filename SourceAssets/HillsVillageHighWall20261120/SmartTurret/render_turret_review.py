"""Render multi-angle Day/Night Cycles reviews, gun fit & Workshop card for SM_SmartTurretPreview."""
import json
import math
import os
import struct
import zipfile
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
MESHZIP = HERE / "SM_SmartTurretPreview.meshzip"
TEXDIR = HERE / "PropTextures"
OUT = Path(os.environ.get("TURRET_REVIEW_OUT", r"F:\FPSGAMEData\ArtReviews\HighVillageDefense\SmartTurretModel-20261127"))
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
        em_col = (0.015, 0.72, 0.96)
        strength = 3.6 if night_mode else 1.55
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
        mesh_data = bpy.data.meshes.new("SM_SmartTurretPreview")
        verts, tris, mats, uvs, loop_normals = [], [], [], [], []
        for idx, slot in enumerate(meta["materials"]):
            mesh_data.materials.append(make_pbr_material(slot, night_mode=night_mode))
            vraw = z.read(f"{idx}/vertices")
            nraw = z.read(f"{idx}/normals")
            iraw = z.read(f"{idx}/indices")
            uvraw = z.read(f"{idx}/uv")
            vcount = len(vraw) // 12
            voff = len(verts)
            vf = struct.unpack(f"<{vcount * 3}f", vraw)
            nf = struct.unpack(f"<{vcount * 3}f", nraw)
            uvf = struct.unpack(f"<{vcount * 2}f", uvraw)
            for k in range(vcount):
                x, y, zc = vf[k * 3], vf[k * 3 + 1], vf[k * 3 + 2]
                verts.append((x * 0.01, -y * 0.01, zc * 0.01))
            indices = struct.unpack(f"<{len(iraw) // 4}I", iraw)
            for k in range(0, len(indices), 3):
                i0, i1, i2 = indices[k], indices[k + 1], indices[k + 2]
                # Negating Y mirrors UE CW winding directly into Blender CCW outward winding.
                tris.append((voff + i0, voff + i1, voff + i2))
                mats.append(idx)
                for vi in (i0, i1, i2):
                    uvs.append((uvf[vi * 2], 1.0 - uvf[vi * 2 + 1]))
                    nx, ny, nz = nf[vi * 3], nf[vi * 3 + 1], nf[vi * 3 + 2]
                    n_len = math.sqrt(nx * nx + ny * ny + nz * nz)
                    if n_len > 1e-6:
                        loop_normals.append((nx / n_len, -ny / n_len, nz / n_len))
                    else:
                        loop_normals.append((0.0, 0.0, 1.0))
        mesh_data.from_pydata(verts, [], tris)
        uv_layer = mesh_data.uv_layers.new(name="UVMap")
        for li, uv_val in enumerate(uvs):
            uv_layer.data[li].uv = uv_val
        for p, m_idx in zip(mesh_data.polygons, mats):
            p.material_index = m_idx
            p.use_smooth = True
        mesh_data.normals_split_custom_set(loop_normals)
        mesh_data.update()
        obj = bpy.data.objects.new("SM_SmartTurretPreview", mesh_data)
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


def add_reference_lmg():
    """Render-only 1:1 scale LMG/rifle silhouette seated in the open-top U-cradle (Z=1.45 m) for fit proof."""
    scene = bpy.context.scene
    gun_dark = bpy.data.materials.new("RefGunSteel")
    gun_dark.use_nodes = True
    bs = gun_dark.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (0.032, 0.036, 0.042, 1.0)
    bs.inputs["Metallic"].default_value = 0.86
    bs.inputs["Roughness"].default_value = 0.42

    gun_poly = bpy.data.materials.new("RefGunPolymer")
    gun_poly.use_nodes = True
    bp = gun_poly.node_tree.nodes.get("Principled BSDF")
    bp.inputs["Base Color"].default_value = (0.022, 0.024, 0.028, 1.0)
    bp.inputs["Metallic"].default_value = 0.15
    bp.inputs["Roughness"].default_value = 0.58

    lens_mat = bpy.data.materials.new("RefOpticCyan")
    lens_mat.use_nodes = True
    bl = lens_mat.node_tree.nodes.get("Principled BSDF")
    bl.inputs["Base Color"].default_value = (0.12, 0.65, 0.88, 1.0)
    bl.inputs["Roughness"].default_value = 0.08
    bl.inputs["Emission Color"].default_value = (0.14, 0.82, 1.0, 1.0)
    bl.inputs["Emission Strength"].default_value = 2.4

    z_bore = 1.47

    def box_part(name, loc, scale, mat):
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
        ob = bpy.context.object
        ob.name = name
        ob.scale = scale
        ob.data.materials.append(mat)
        return ob

    def cyl_part_x(name, loc, radius, length, mat):
        bpy.ops.mesh.primitive_cylinder_add(vertices=18, radius=radius, depth=length, location=loc, rotation=(0, math.pi * 0.5, 0))
        ob = bpy.context.object
        ob.name = name
        ob.data.materials.append(mat)
        return ob

    # Receiver & feed cover (seated between front & rear vise jaws at Y=+/-0.038 m)
    box_part("RefReceiver", (-0.01, 0.0, z_bore + 0.01), (0.34, 0.068, 0.095), gun_dark)
    # Top rail & LPVO / ACOG Optic clearing open-top U-clamp
    box_part("RefTopRail", (0.02, 0.0, z_bore + 0.068), (0.28, 0.028, 0.022), gun_dark)
    cyl_part_x("RefScopeTube", (0.01, 0.0, z_bore + 0.108), 0.022, 0.19, gun_dark)
    cyl_part_x("RefScopeBell", (0.09, 0.0, z_bore + 0.108), 0.030, 0.055, gun_dark)
    cyl_part_x("RefScopeGlass", (0.118, 0.0, z_bore + 0.108), 0.024, 0.008, lens_mat)
    # Handguard & heavy fluted barrel + gas tube + flash hider extending +X
    box_part("RefHandguard", (0.23, 0.0, z_bore + 0.002), (0.21, 0.062, 0.072), gun_poly)
    cyl_part_x("RefBarrel", (0.44, 0.0, z_bore + 0.012), 0.013, 0.56, gun_dark)
    cyl_part_x("RefGasTube", (0.39, 0.0, z_bore - 0.018), 0.009, 0.34, gun_dark)
    cyl_part_x("RefFlashHider", (0.73, 0.0, z_bore + 0.012), 0.017, 0.06, gun_dark)
    # Front sight post
    box_part("RefFrontSight", (0.52, 0.0, z_bore + 0.045), (0.022, 0.014, 0.055), gun_dark)
    # Underside 200-round LMG box magazine dropping cleanly into open magwell bay!
    box_part("RefBoxMag", (0.04, 0.0, z_bore - 0.115), (0.12, 0.095, 0.145), gun_poly)
    # Pistol grip & buttstock extending -X clear above rear console
    grip = box_part("RefGrip", (-0.11, 0.0, z_bore - 0.085), (0.045, 0.036, 0.11), gun_poly)
    grip.rotation_euler = (0.0, 0.25, 0.0)
    box_part("RefStock", (-0.31, 0.0, z_bore - 0.015), (0.27, 0.044, 0.115), gun_poly)


def add_scale_and_parapet():
    """Subtle translucent 1.75 m operator silhouette at -X and 1.10 m stone parapet wall in front (+X)."""
    scene = bpy.context.scene
    mat = bpy.data.materials.new("OperatorScaleRef")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.55, 0.62, 0.70, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.8
    bsdf.inputs["Alpha"].default_value = 0.28
    bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=0.19, depth=1.42, location=(-1.12, 0.0, 0.71))
    bpy.context.object.data.materials.append(mat)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=0.115, location=(-1.12, 0.0, 1.62))
    bpy.context.object.data.materials.append(mat)

    # 1.10 m parapet merlon silhouette at X = +0.95 m to prove Z=1.45 m pivot clears battlement cleanly
    pmat = bpy.data.materials.new("ParapetScaleRef")
    pmat.use_nodes = True
    pbs = pmat.node_tree.nodes.get("Principled BSDF")
    pbs.inputs["Base Color"].default_value = (0.30, 0.32, 0.35, 1.0)
    pbs.inputs["Roughness"].default_value = 0.88
    pbs.inputs["Alpha"].default_value = 0.32
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(1.05, 0.0, 0.55))
    par = bpy.context.object
    par.scale = (0.42, 0.80, 1.10)
    par.data.materials.append(pmat)


def setup_world_and_lights(mode="day"):
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new("Studio")
    if mode == "night":
        scene.world.color = (0.004, 0.006, 0.014)
        lights = [
            ("MoonRim", "AREA", (-2.6, -2.8, 4.4), 24.0, 2.2, (0.45, 0.62, 1.0)),
            ("CoolFill", "AREA", (2.8, 3.0, 2.2), 10.5, 2.4, (0.35, 0.52, 0.90)),
        ]
    elif mode == "plate":
        scene.world.color = (0.12, 0.13, 0.14)
        lights = [
            ("SoftKey", "AREA", (-1.5, 3.4, 4.2), 360.0, 3.2, (1.0, 0.88, 0.72)),
            ("SoftRim", "AREA", (2.2, -2.8, 2.8), 400.0, 3.2, (0.76, 0.85, 1.0)),
            ("PlateFront", "AREA", (2.2, 2.4, 1.9), 180.0, 2.6, (0.94, 0.96, 1.0)),
        ]
    else:
        scene.world.color = (0.14, 0.16, 0.19)
        lights = [
            ("DayKey", "AREA", (1.2, 3.4, 4.6), 460.0, 3.4, (1.0, 0.91, 0.78)),
            ("DayRim", "AREA", (-2.6, -2.8, 3.4), 380.0, 3.2, (0.74, 0.86, 1.0)),
            ("FrontFill", "AREA", (2.8, 1.8, 1.8), 210.0, 2.8, (0.95, 0.96, 1.0)),
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
        target = Vector((0.0, 0.0, 1.05))
        ob.rotation_euler = (target - Vector(loc)).to_track_quat("-Z", "Y").to_euler()

    # Subtle sapphire pod glow cast onto brass hood & yoke steel (placed in Blender Y = +0.452 -> flipped from UE -Y)
    if mode in ("night", "plate"):
        pt = bpy.data.lights.new("OpticGlowLight", "POINT")
        pt.energy = 26.0 if mode == "night" else 8.0
        pt.color = (0.18, 0.84, 1.0)
        pt.shadow_soft_size = 0.08
        ob = bpy.data.objects.new("OpticGlowLight", pt)
        scene.collection.objects.link(ob)
        ob.location = (0.24, 0.46, 1.46)


def render_cam(filename, loc, aim, res_x, res_y, ortho_scale=None, lens=42.0, fmt="PNG"):
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
        scene.render.image_settings.quality = 91
    else:
        scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(OUT / filename)
    bpy.ops.render.render(write_still=True)


def main():
    # NOTE on coordinate mapping: load_meshzip negates UE Y -> Blender Y, so UE -Y (the sapphire optic pod)
    # sits at Blender +Y! Place hero/closeup cameras on +Y side of Blender to frame the sapphire pod!

    # 1. Day Hero 3/4 (+X barrel pointing forward-left/right cleanly toward viewer, +Y sapphire pod facing viewer)
    clear_scene()
    load_meshzip(MESHZIP, night_mode=False)
    add_reference_lmg()
    add_ground(night_mode=False)
    setup_world_and_lights("day")
    render_cam("01-day-hero-mounted.png", (2.05, 2.55, 1.98), (0.08, 0.0, 1.00), 1080, 1080, lens=44.0)

    # 2. Day Rear 3/4 Empty (-X console, empty open-top U-clamp, open magwell bay, brass slewing gear)
    clear_scene()
    load_meshzip(MESHZIP, night_mode=False)
    add_ground(night_mode=False)
    setup_world_and_lights("day")
    render_cam("02-day-rear-empty.png", (-2.20, 2.15, 2.15), (-0.05, 0.0, 0.98), 1080, 1080, lens=42.0)

    # 3. Ortho Side Profile (-X operator on left, +X parapet on right, proving Z=1.45m pivot clearance)
    clear_scene()
    load_meshzip(MESHZIP, night_mode=False)
    add_ground(night_mode=False)
    add_scale_and_parapet()
    setup_world_and_lights("day")
    render_cam("03-side-profile-scale.png", (0.02, 4.40, 1.05), (0.02, 0.0, 0.96), 1080, 1080, ortho_scale=2.75)

    # 4. Close-Up of Brass Gear Teeth, Helical Springs, Hydraulic Struts, U-Clamp & Sapphire Optic Pod
    clear_scene()
    load_meshzip(MESHZIP, night_mode=False)
    setup_world_and_lights("day")
    render_cam("04-closeup-cradle-optic.png", (1.28, 1.48, 1.62), (0.02, 0.16, 1.24), 960, 960, lens=46.0)

    # 5. Night Raid Silhouette & Sapphire Optic Glow
    clear_scene()
    load_meshzip(MESHZIP, night_mode=True)
    add_ground(night_mode=True)
    setup_world_and_lights("night")
    render_cam("05-night-tracking-glow.png", (2.25, 2.35, 2.00), (0.05, 0.05, 1.04), 1080, 1080, lens=42.0)

    # 6. Workshop Upgrade Card Plate (672x322 JPEG matching LightningSpire.jpg crop & studio brightness)
    clear_scene()
    obj = load_meshzip(MESHZIP, night_mode=False)
    add_ground(night_mode=True)
    setup_world_and_lights("plate")
    scene = bpy.context.scene
    bpy.context.view_layer.update()
    direction = Vector((0.62, 1.0, 0.48)).normalized()
    center = Vector((0.0, 0.0, 0.96))
    size = 2.0
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
    cam_d.ortho_scale = max(max(xs) - min(xs), (max(ys) - min(ys)) * 672.0 / 322.0) * 1.18
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
    scene.render.filepath = str(OUT / "SmartTurret.jpg")
    bpy.ops.render.render(write_still=True)
    print(f"RENDERED SMART TURRET REVIEW -> {OUT}")


if __name__ == "__main__":
    main()
