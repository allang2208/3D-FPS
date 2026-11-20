"""Fit the village baker's linen cap to the assembled Jason R4 head in Blender."""

import math
from pathlib import Path

import numpy as np


TEXTURES = Path(__file__).resolve().parents[2] / "SourceAssets" / "VillageBaker" / "CapR1"
STEM = "T_VillageBaker_Cap_"
TAU = math.tau


def write_linen_maps():
    """Author an exportable UV atlas. Run with ordinary Python and Pillow."""
    from PIL import Image

    width, height = 2048, 1024
    rng = np.random.default_rng(71327)
    y, x = np.mgrid[:height, :width].astype(np.float32)
    u, v = (x + .5) / width, 1.0 - (y + .5) / height
    noise = rng.normal(size=x.shape).astype(np.float32)

    def mottling(columns, rows):
        pixels = rng.integers(0, 256, (rows, columns), dtype=np.uint8)
        field = Image.fromarray(pixels).resize((width, height), Image.Resampling.BICUBIC)
        return np.asarray(field, dtype=np.float32) / 127.5 - 1.

    uneven = mottling(15, 11)
    drift = mottling(42, 23)
    warp = (x + 1.15 * uneven + .72 * np.sin(y * .011 + x * .007)) / 3.9
    weft = (y + .95 * drift + .88 * np.sin(x * .014 - y * .006)) / 4.5
    warp_thread = .5 + .5 * np.cos(TAU * warp)
    weft_thread = .5 + .5 * np.cos(TAU * weft)
    crossings = np.cos(math.pi * warp) * np.cos(math.pi * weft)
    over = .5 + .48 * np.tanh(3.5 * crossings)
    warp_tone = rng.normal(0, .82, width)[np.floor(warp).astype(int) % width]
    weft_tone = rng.normal(0, .82, height)[np.floor(weft).astype(int) % height]
    surface = over * warp_thread + (1. - over) * weft_thread
    relief = surface * .78 + .15 * (warp_thread + weft_thread) + noise * .028
    linen = ((surface - .58) * 14. + 3.4 * (over * warp_tone + (1. - over) * weft_tone)
             + 2.6 * uneven + 1.3 * drift + 1.25 * noise)

    # Back opening of the circular unwrap and the matched crown panel seam.
    edge_dist = np.minimum(u, 1. - u) * width
    seam_dist = np.where(v < .475, edge_dist, abs(u - .5) * width)
    crown_seam = ((v >= .121) & (v < .475)) | (v > .724)
    stitches = .5 + .5 * np.cos(TAU * (y + .7 * np.sin(y * .051)) / 9.)
    seam_line = np.exp(-np.square(seam_dist / 1.05)) * crown_seam
    felled_edges = np.exp(-np.square((seam_dist - 2.8) / 1.15)) * crown_seam
    back_stitch = felled_edges * np.maximum(0., (stitches - .22) / .78)
    relief += .55 * back_stitch - .24 * seam_line
    linen += 5.1 * back_stitch - 8.0 * seam_line - 2.1 * felled_edges

    # Two narrow running stitches on the fitted band, with a soft turned hem.
    for row in (.037, .091):
        distance = (v - row) * height - .32 * np.sin(u * TAU * 19.)
        thread = np.exp(-np.square(distance / 1.1))
        step = .5 + .5 * np.cos(TAU * (x / 12. - .12 * np.sin(u * TAU * 13.)))
        stitch = thread * np.maximum(0., (step - .15) / .85)
        relief += stitch * .6 - thread * .14
        linen += stitch * 8. - thread * 3.5
    band = v < .116
    crease = np.exp(-np.square((v - .022) * 134.)) + np.exp(-np.square((v - .106) * 141.))
    linen -= band * (7.7 + crease * 7.5)

    base = np.stack([185. + linen, 169. + linen * .94, 148. + linen * .88], axis=-1)
    dy, dx = np.gradient(relief)
    normal = np.stack((-dx * .70, dy * .70, np.ones_like(dx)), axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    roughness = 211. + 4. * uneven - 7. * (surface - .5) + 1.5 * noise
    ao = 248. - (1. - surface) * 6. - seam_line * 7.
    orm = np.stack((ao, roughness, np.zeros_like(roughness)), axis=-1)
    TEXTURES.mkdir(parents=True, exist_ok=True)
    for suffix, values in (("BC", base), ("N_GL", (normal + 1.) * 127.5), ("ORM", orm)):
        pixels = np.clip(np.rint(values), 0, 255).astype(np.uint8)
        Image.fromarray(pixels).save(TEXTURES / (STEM + suffix + ".png"), compress_level=7)


def _linen_material():
    import bpy

    material = bpy.data.materials.new("M_VillageBaker_CapLinen")
    material.diffuse_color = (.485, .397, .296, 1.)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    link = material.node_tree.links.new
    shader = nodes.get("Principled BSDF")
    shader.inputs["Roughness"].default_value = .83
    shader.inputs["Specular IOR Level"].default_value = .23
    shader.inputs["Sheen Weight"].default_value = .17
    for i, suffix in enumerate(("BC", "N_GL", "ORM")):
        tex = nodes.new("ShaderNodeTexImage")
        tex.location = (-650, 320 - i * 285)
        tex.image = bpy.data.images.load(str(TEXTURES / (STEM + suffix + ".png")), check_existing=True)
        tex.image.colorspace_settings.name = "sRGB" if suffix == "BC" else "Non-Color"
        if not tex.image.packed_file:
            tex.image.pack()
        if suffix == "BC":
            link(tex.outputs["Color"], shader.inputs["Base Color"])
        elif suffix == "N_GL":
            normal = nodes.new("ShaderNodeNormalMap")
            normal.location = (-290, -10)
            normal.inputs["Strength"].default_value = .78
            link(tex.outputs["Color"], normal.inputs["Color"])
            link(normal.outputs["Normal"], shader.inputs["Normal"])
        else:
            split = nodes.new("ShaderNodeSeparateColor")
            split.location = (-290, -270)
            link(tex.outputs["Color"], split.inputs["Color"])
            link(split.outputs["Green"], shader.inputs["Roughness"])
            link(split.outputs["Blue"], shader.inputs["Metallic"])
    return material


def _head_surface(objects, rig):
    import bpy
    from mathutils import Matrix
    from mathutils.bvhtree import BVHTree

    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    rig_eval = rig.evaluated_get(deps)
    bones = rig_eval.pose.bones
    head = bones["head"]

    def joint(name):
        return np.array(rig_eval.matrix_world @ bones[name].head, dtype=float)

    # Jason's physical left and vertical define forward even in a rotated assembly.
    pivot = joint("head")
    body_z = pivot - (joint("foot_l") + joint("foot_r")) * .5
    body_z /= np.linalg.norm(body_z)
    left = joint("clavicle_l") - joint("clavicle_r")
    left -= body_z * left.dot(body_z)
    left /= np.linalg.norm(left)
    axes = np.column_stack((left, np.cross(body_z, left), body_z))
    pieces, faces, count = [], [], 0
    for obj in objects:
        if obj.type != "MESH":
            continue
        evaluated = obj.evaluated_get(deps)
        mesh = evaluated.to_mesh()
        try:
            xyz = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
            mesh.vertices.foreach_get("co", xyz)
            transform = np.asarray(evaluated.matrix_world)
            xyz = xyz.reshape(-1, 3) @ transform[:3, :3].T + transform[:3, 3]
            pieces.append((xyz - pivot) @ axes)
            mesh.calc_loop_triangles()
            indices = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int32)
            mesh.loop_triangles.foreach_get("vertices", indices)
            faces.append(indices.reshape(-1, 3) + count)
            count += len(xyz)
        finally:
            evaluated.to_mesh_clear()
    points = np.concatenate(pieces)
    height = points[:, 2].max()
    crown = points[(points[:, 2] >= .57 * height) & (points[:, 2] <= .79 * height)]
    center = np.zeros(3)
    center[:2] = np.mean(np.percentile(crown[:, :2], [1, 99], axis=0), axis=0)
    points = (points - center) / height
    indices = np.concatenate(faces)
    indices = indices[np.max(points[indices, 2], axis=1) > .22]
    surface = BVHTree.FromPolygons(points.tolist(), indices.tolist(), all_triangles=True)
    # Put fitted world coordinates into head rest space before adding the armature.
    frame = np.eye(4)
    frame[:3, :3] = axes * height
    frame[:3, 3] = pivot + axes @ center
    to_rest = (head.bone.matrix_local @ head.matrix.inverted()
               @ rig_eval.matrix_world.inverted() @ Matrix(frame.tolist()))
    return surface, to_rest, head.name


def add_baker_cap(head_objects, rig):
    """Create and return the separate, rigidly head-weighted cap mesh in the active scene."""
    import bpy
    from mathutils import Vector

    objects = list(head_objects)
    surface, to_rest, head_name = _head_surface(objects, rig)
    count = 176
    angles = np.arange(count) * TAU / count
    cs, sn = np.cos(angles), np.sin(angles)
    # Angle zero is the nape. The front sweeps up at the temples to the hairline.
    base = .555 - .147 * cs + .012 * np.cos(2. * angles - .28)
    band_height = .102 + .009 * np.cos(angles + .25)
    rays = np.column_stack((sn, -cs, np.zeros(count)))

    def sample(z, pitch):
        flat, rise = math.cos(pitch), math.sin(pitch)
        radii = []
        for i, ray in enumerate(rays):
            direction = Vector((ray[0] * flat, ray[1] * flat, rise))
            origin = Vector((0., 0., float(z[i])))
            loc, _, _, _ = surface.ray_cast(origin + direction * 2.5, -direction, 2.5)
            radii.append((loc - origin).length if loc is not None else np.nan)
        raw = np.asarray(radii)
        valid = np.isfinite(raw)
        if not np.any(valid):
            raise ValueError("No scalp surface intersects this ring of the baker's cap.")
        if not np.all(valid):
            raw[~valid] = np.interp(angles[~valid], angles[valid], raw[valid], period=TAU)
        # Keep close hair relief inside the fabric while bridging shallow strand valleys.
        smoothed = (raw * 4. + 2. * (np.roll(raw, 1) + np.roll(raw, -1))
                    + np.roll(raw, 2) + np.roll(raw, -2)) * .1
        return np.maximum(raw, smoothed)

    rows, band_v, crown_t = [], [], []
    for lift, allowance, v in ((0., -.032, .010), (-.008, -.003, .018),
                               (-.007, .009, .026), (.05, .019, .032),
                               (.22, .017, .042), (.55, .020, .061),
                               (.83, .021, .083), (.96, .023, .097),
                               (1.03, .017, .104), (1.05, .006, .110)):
        z = base + band_height * lift
        radius = sample(z, 0.) + allowance
        rows.append(np.column_stack((sn * radius, -cs * radius, z)))
        band_v.append(v)

    rng = np.random.default_rng(91535)
    gathers = []
    for j in range(14):
        gathers.append((TAU * (j + rng.uniform(-.21, .21)) / 14.,
                        rng.uniform(.046, .092), rng.uniform(.037, .072),
                        rng.uniform(-.31, .33), rng.uniform(.15, .29)))
    crown_z = base + 1.045 * band_height
    for t in np.linspace(.0, .98, 40):
        pitch = t * math.pi / 2.
        radii = sample(crown_z, pitch)
        # Fullness rolls over the band and vanishes toward the gently flattened top.
        hem_roll = math.sin(min(1., t / .14) * math.pi * .5)
        ease = .021 + hem_roll * (.050 + .049 * math.exp(-((t - .22) / .25) ** 2))
        tuck = np.zeros(count)
        for phase, width, amplitude, lean, reach in gathers:
            delta = (angles - phase - lean * t + math.pi) % TAU - math.pi
            groove = np.exp(-np.square(delta / width))
            ridge = np.exp(-np.square((delta - width * 1.45) / (width * 1.38)))
            tuck += amplitude * (.63 * ridge - groove) * math.exp(-((t - .19) / reach) ** 2)
        soft_wave = .011 * np.sin(angles * 3. + .68) + .007 * np.cos(angles * 5. - .4)
        tail_seam = np.minimum(angles, TAU - angles) * np.maximum(.015, radii * math.cos(pitch))
        fell = .005 * np.exp(-np.square((tail_seam - .008) / .007))
        gather = hem_roll * tuck + soft_wave * math.sin(math.pi * t) + fell * (1. - t)
        horizontal = math.cos(pitch) * (radii + ease + gather)
        back_slouch = .035 * math.sin(t * math.pi * .5) ** 2
        z = crown_z + (radii + .052 + gather) * math.sin(pitch)
        rows.append(np.column_stack((sn * horizontal, -cs * horizontal - back_slouch, z)))
        crown_t.append(t)

    position = [to_rest @ Vector(point) for ring in rows for point in ring]
    last = len(rows) - 1
    pole = np.array((0., -.035, float(sample(crown_z, math.pi * .5)[0] + crown_z[0] + .052)))
    position.append(to_rest @ Vector(pole))
    tip = len(position) - 1
    polygons, loop_uvs = [], []
    top_start = next(i for i, t in enumerate(crown_t) if t >= .60)
    top_row = len(band_v) + top_start

    def panel_uv(row, j):
        x, y, _ = rows[row][j % count]
        return (.5 + .238 * x, .724 - .476 * (y + .035))

    def side_v(row):
        if row < len(band_v):
            return band_v[row]
        return .126 + .328 * crown_t[row - len(band_v)] / crown_t[top_start]

    for row in range(last):
        for j in range(count):
            k = (j + 1) % count
            polygons.append((row * count + j, row * count + k,
                             (row + 1) * count + k, (row + 1) * count + j))
            corners = ((row, j), (row, j + 1), (row + 1, j + 1), (row + 1, j))
            if row >= top_row:
                loop_uvs.extend(panel_uv(r, c) for r, c in corners)
            else:
                loop_uvs.extend((c / count, side_v(r)) for r, c in corners)
    for j in range(count):
        polygons.append((last * count + j, last * count + (j + 1) % count, tip))
        loop_uvs.extend((panel_uv(last, j), panel_uv(last, j + 1), (.5, .724)))

    mesh = bpy.data.meshes.new("SK_VillageBaker_Cap")
    mesh.from_pydata(position, [], polygons)
    mesh.update()
    mesh.polygons.foreach_set("use_smooth", [True] * len(polygons))
    uv = mesh.uv_layers.new(name="UVMap")
    uv.data.foreach_set("uv", np.asarray(loop_uvs, dtype=np.float32).ravel())
    mesh.materials.append(_linen_material())
    cap = bpy.data.objects.new("SK_VillageBaker_Cap", mesh)
    collection = rig.users_collection[0] if rig.users_collection else bpy.context.collection
    collection.objects.link(cap)
    cap.parent = rig
    cap.vertex_groups.new(name=head_name).add(list(range(len(position))), 1., "REPLACE")
    armature = cap.modifiers.new("Jason R4 head", "ARMATURE")
    armature.object = rig
    return [cap]


if __name__ == "__main__":
    import sys
    if "--write-textures" in sys.argv:
        write_linen_maps()
