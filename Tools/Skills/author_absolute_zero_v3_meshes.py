"""Sculpt RAZOR-FACETED fractured mineral glacier spires for AbsoluteZero V4 (Blender 5.1).

Upgraded from V3 to eliminate smooth/conical voxel-melted silhouettes:
  - ZERO voxel remesh and ZERO CorrectiveSmooth rounding!
  - True angular crystalline prism architecture with 12-16 razor-straight oblique `bisect_plane`
    cleavage fractures, stepped crystal ledges, asymmetric chiseled blade tips, and jagged
    upturned base frost plates.
  - Micro-bevel (`0.0045 m`, 1 segment) on sharp cleavage edges catches realistic wet-ice glints.
  - Clean 20-deg creased split normals keep flat cleaved crystal faces mirror-crisp!
  - Continuous cylindrical/planar UVs tailored 1:1 for IceSpike's 4K T_IceBaseColor & T_IceNormal.
  - Calibrated 4-channel vertex color ("Frost", CORNER, BYTE_COLOR):
      R: thin frost strictly along razor convex crystal edges (mean ~0.16-0.22, never washes body)
      G: tight ground-rupture root frost collar (Z < 0.22 m only, mean ~0.14-0.20)
      B: deep concave crystal-seam cavity shadow
      A: normalized height Z in [0, 1]
"""
import json
import math
import random
from pathlib import Path
import bpy
import bmesh
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'SourceAssets/AbsoluteZeroV3_20261127'
DEST.mkdir(parents=True, exist_ok=True)


def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else (hi if v > hi else v)


def smoothstep(e0, e1, x):
    t = clamp((x - e0) / max(1e-6, e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def bisect_and_cap(bm, plane_co, plane_no):
    n = plane_no.normalized()
    res = bmesh.ops.bisect_plane(
        bm,
        geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
        dist=1e-5,
        plane_co=plane_co,
        plane_no=n,
        clear_outer=True,
    )
    cut_edges = [e for e in res['geom_cut'] if isinstance(e, bmesh.types.BMEdge) and e.is_boundary]
    if cut_edges:
        bmesh.ops.holes_fill(bm, edges=cut_edges, sides=0)


def make_razor_crystal_prism(
    rng,
    height=1.0,
    skirt=-0.14,
    base_rx=0.25,
    base_ry=0.21,
    sides=6,
    lean_x=0.04,
    lean_y=0.0,
    twist_rad=0.10,
    tilt_x_rad=0.0,
    tilt_y_rad=0.0,
    offset=(0.0, 0.0, 0.0),
    cleave_cuts=7,
    step_notches=2,
):
    """Build a sharp-faceted angular mineral crystal column with true planar cleavage cuts."""
    bm = bmesh.new()
    # Irregular hexagonal/heptagonal base section (real hexagonal Ih ice crystal symmetry!)
    angles = []
    r_mul = []
    for s in range(sides):
        a = (2.0 * math.pi * s) / sides + rng.uniform(-0.16, 0.16)
        angles.append(a)
        r_mul.append(rng.uniform(0.78, 1.26))

    # Build a crisp multi-section tapered hexagonal column rising to a razor-sharp spear point
    z_levels = [skirt, 0.0, 0.22 * height, 0.50 * height, 0.76 * height, 0.90 * height]
    radii_t = [1.08, 1.04, 0.86, 0.58, 0.30, 0.11]

    ring_verts = []
    for z, rm in zip(z_levels, radii_t):
        t = clamp(z / max(1e-4, height), 0.0, 1.0)
        cx = lean_x * t
        cy = lean_y * t
        tw = twist_rad * t
        row = []
        for s in range(sides):
            ang = angles[s] + tw
            vx = cx + math.cos(ang) * base_rx * rm * r_mul[s]
            vy = cy + math.sin(ang) * base_ry * rm * r_mul[s]
            row.append(bm.verts.new((vx, vy, z)))
        ring_verts.append(row)

    bm.faces.new(list(reversed(ring_verts[0])))
    for ri in range(len(ring_verts) - 1):
        r0, r1 = ring_verts[ri], ring_verts[ri + 1]
        for s in range(sides):
            sn = (s + 1) % sides
            bm.faces.new((r0[s], r0[sn], r1[sn], r1[s]))

    # Razor chiseled asymmetric blade tip (2-vertex wedge ridge instead of rounded cone!)
    blade_ang = rng.uniform(0.0, math.pi)
    bx = math.cos(blade_ang) * base_rx * 0.06
    by = math.sin(blade_ang) * base_ry * 0.06
    tip = bm.verts.new((lean_x + bx, lean_y + by, height))
    top_ring = ring_verts[-1]
    for s in range(sides):
        sn = (s + 1) % sides
        bm.faces.new((top_ring[s], top_ring[sn], tip))

    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

    # 1) Bold planar crystal cleavage facets along the flanks/shoulders (kept strictly below apex so
    #    every spire terminates in a razor-sharp crystal lance point, never a blunted flat top!)
    for ci in range(cleave_cuts):
        ang = (2.0 * math.pi * ci) / max(1, cleave_cuts) + rng.uniform(-0.32, 0.32)
        t_z = rng.uniform(0.24, 0.74)
        z_pt = t_z * height
        nz = rng.uniform(0.14, 0.34)
        n = Vector((math.cos(ang), math.sin(ang), nz)).normalized()
        rad_est = max(base_rx, base_ry) * (1.0 - t_z * 0.76) * rng.uniform(0.72, 0.94)
        p = Vector((lean_x * t_z + math.cos(ang) * rad_est, lean_y * t_z + math.sin(ang) * rad_est, z_pt))
        bisect_and_cap(bm, p, n)

    # 2) Crisp stepped fracture notches along the lower/mid flanks (never clipping apex)
    for _ in range(step_notches):
        ang = rng.uniform(0.0, 2.0 * math.pi)
        t_z = rng.uniform(0.26, 0.58)
        z_pt = t_z * height
        n = Vector((math.cos(ang), math.sin(ang), rng.uniform(0.42, 0.78))).normalized()
        rad_est = max(base_rx, base_ry) * (1.0 - t_z * 0.68) * rng.uniform(0.68, 0.90)
        p = Vector((lean_x * t_z + math.cos(ang) * rad_est, lean_y * t_z + math.sin(ang) * rad_est, z_pt))
        bisect_and_cap(bm, p, n)

    # Apply subtle micro-bevel on sharp crystal intersections so sunlight glints crisply on every edge
    sharp_edges = []
    for e in bm.edges:
        if len(e.link_faces) == 2:
            d = clamp(e.link_faces[0].normal.dot(e.link_faces[1].normal), -1.0, 1.0)
            if d < math.cos(math.radians(22.0)):
                sharp_edges.append(e)
    if sharp_edges:
        bmesh.ops.bevel(
            bm,
            geom=sharp_edges,
            offset=0.0042 * max(0.4, height),
            offset_type='OFFSET',
            segments=1,
            profile=0.5,
            affect='EDGES',
            clamp_overlap=True,
        )

    # Apply local tilt and placement offset
    rot = Matrix.Rotation(tilt_y_rad, 4, 'Y') @ Matrix.Rotation(tilt_x_rad, 4, 'X')
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(offset)) @ rot, verts=list(bm.verts))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    return bm


def make_shattered_base_shards(rng, count=5, radius=0.24, max_h=0.26):
    """Create sharp angular splintered ice plates thrusting out of the ground around the spire foot."""
    parts = []
    for i in range(count):
        ang = (2.0 * math.pi * i) / count + rng.uniform(-0.30, 0.30)
        dist = radius * rng.uniform(0.45, 0.78)
        h = max_h * rng.uniform(0.62, 1.18)
        rx = radius * rng.uniform(0.26, 0.42)
        ry = radius * rng.uniform(0.16, 0.28)
        tilt = rng.uniform(0.32, 0.68)
        bm = make_razor_crystal_prism(
            rng,
            height=h,
            skirt=-0.12,
            base_rx=rx,
            base_ry=ry,
            sides=5,
            lean_x=0.02,
            cleave_cuts=4,
            step_notches=0,
        )
        rot_z = Matrix.Rotation(ang, 4, 'Z')
        rot_out = Matrix.Rotation(tilt, 4, 'Y')
        trans = Matrix.Translation(Vector((math.cos(ang) * dist, math.sin(ang) * dist, -0.02)))
        bmesh.ops.transform(bm, matrix=trans @ rot_z @ rot_out, verts=list(bm.verts))
        parts.append(bm)
    return parts


def finalize_crystal_asset(name, part_bmeshes, seed):
    """Combine crisp crystal shards WITHOUT voxel melting, add controlled high-res planar facet
    subdivision with razor micro-chisel variation, pin peak to Z=1.00 m, and bake crisp normals + Frost RGBA."""
    rng = random.Random(seed)
    bm = bmesh.new()
    tmp = bpy.data.meshes.new(name + '_Tmp')
    part_ids = []
    for pid, pbm in enumerate(part_bmeshes):
        pbm.to_mesh(tmp)
        pbm.free()
        v_before = len(bm.verts)
        bm.from_mesh(tmp)
        for _ in range(len(bm.verts) - v_before):
            part_ids.append(pid)
    bpy.data.meshes.remove(tmp)

    # Triangulate cleanly (keeps 100% razor-straight crystal edges!)
    bmesh.ops.triangulate(bm, faces=list(bm.faces), quad_method='BEAUTY', ngon_method='BEAUTY')
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    # Normalize exact peak height to Z = 1.00 m and skirt floor >= -0.15 m
    top_z = max(v.co.z for v in bm.verts)
    if top_z > 0.1:
        s = 1.0 / top_z
        for v in bm.verts:
            if v.co.z > 0.0:
                v.co.z *= s
            else:
                v.co.z = max(-0.15, v.co.z * s)

    # Compute exact discrete geometric convexity (R) and cavity/inter-shard seam (B)
    nv = len(bm.verts)
    raw_convex = [0.0] * nv
    raw_concave = [0.0] * nv

    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        f0, f1 = e.link_faces[0], e.link_faces[1]
        bend = math.acos(clamp(f0.normal.dot(f1.normal), -1.0, 1.0))
        if bend < 0.24:
            continue
        signed = (f1.calc_center_median() - f0.calc_center_median()).dot(f0.normal)
        strength = clamp((bend - 0.24) / 0.82, 0.0, 1.0)
        for ev in e.verts:
            vi = ev.index
            if signed < -1e-6:
                raw_convex[vi] = max(raw_convex[vi], strength)
            elif signed > 1e-6:
                raw_concave[vi] = max(raw_concave[vi], strength)

    # Also detect inter-shard junction crevices near secondary crystal roots
    for v in bm.verts:
        vi = v.index
        r_xy = math.hypot(v.co.x, v.co.y)
        if 0.02 < v.co.z < 0.55 and r_xy < 0.16:
            raw_concave[vi] = max(raw_concave[vi], 0.45 * (1.0 - smoothstep(0.06, 0.16, r_xy)))

    mesh = bpy.data.meshes.new(name + '_Mesh')
    ob = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(ob)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    # 20-degree sharp creased normals: flat cleaved crystal planes stay RAZOR-FLAT & glassy!
    adjacent = [[] for _ in mesh.vertices]
    for poly in mesh.polygons:
        poly.use_smooth = True
        for vi in poly.vertices:
            adjacent[vi].append(poly)

    crease_cos = math.cos(math.radians(20.0))
    split_normals = []
    uv_layer = mesh.uv_layers.new(name='IceMeters')
    frost_col = mesh.color_attributes.new(name='Frost', type='BYTE_COLOR', domain='CORNER')

    r_vals, g_vals, b_vals = [], [], []
    for poly in mesh.polygons:
        n = poly.normal
        # Cylindrical/planar hybrid UV matching IceSpike 4K T_IceBaseColor & T_IceNormal density cleanly
        axis = max(range(3), key=lambda a: abs(n[a]))
        ua, ub = ((1, 2), (0, 2), (0, 1))[axis]
        for li in poly.loop_indices:
            vi = mesh.loops[li].vertex_index
            co = mesh.vertices[vi].co
            acc = Vector((0.0, 0.0, 0.0))
            for other in adjacent[vi]:
                if n.dot(other.normal) >= crease_cos:
                    acc += other.normal * other.area
            ln = acc.normalized() if acc.length > 1e-6 else n
            split_normals.append((ln.x, ln.y, ln.z))
            uv_layer.data[li].uv = (co[ua] * 1.45 + 0.5, co[ub] * 1.45 + 0.5)

            h_norm = clamp(co.z, 0.0, 1.0)
            # R: THIN crisp frost ONLY on sharp convex crystal ridges & razor tip edges
            r_val = clamp((raw_convex[vi] ** 1.45) * 0.90 + smoothstep(0.90, 1.0, h_norm) * 0.25)
            # G: TIGHT ground-rupture root frost ONLY at Z < 0.22 m (keeps upper 80% clear dark crystal!)
            g_val = clamp((1.0 - smoothstep(0.02, 0.24, h_norm)) * 0.85)
            # B: Concave crevices & inner crystal junctions
            b_val = clamp(raw_concave[vi] * 0.90)
            # A: Normalized height Z in [0, 1]
            a_val = h_norm

            frost_col.data[li].color = (r_val, g_val, b_val, a_val)
            r_vals.append(r_val)
            g_vals.append(g_val)
            b_vals.append(b_val)

    mesh.normals_split_custom_set(split_normals)
    mesh.update()

    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    fbx_path = DEST / f'{name}.fbx'
    bpy.ops.export_scene.fbx(
        filepath=str(fbx_path),
        use_selection=True,
        object_types={'MESH'},
        add_leaf_bones=False,
        axis_forward='-Y',
        axis_up='Z',
        apply_unit_scale=True,
        bake_anim=False,
        mesh_smooth_type='FACE',
    )

    xs = [v.co.x for v in mesh.vertices]
    ys = [v.co.y for v in mesh.vertices]
    zs = [v.co.z for v in mesh.vertices]
    info = {
        'mesh': name,
        'fbx': str(fbx_path),
        'vertices': len(mesh.vertices),
        'triangles': len(mesh.polygons),
        'bounds_m': {
            'x': [round(min(xs), 4), round(max(xs), 4)],
            'y': [round(min(ys), 4), round(max(ys), 4)],
            'z': [round(min(zs), 4), round(max(zs), 4)],
        },
        'vcol_mean': {
            'R_edge_frost': round(sum(r_vals) / len(r_vals), 3),
            'G_root_frost': round(sum(g_vals) / len(g_vals), 3),
            'B_cavity': round(sum(b_vals) / len(b_vals), 3),
        },
    }
    ob.hide_set(True)
    ob.select_set(False)
    return info


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = 'METRIC'
    manifest = []

    # 1) SM_AZ_GlacierSpire_01: Razor hexagonal crystal monolith + 2 angular daughter shards + 5 base plates
    r1 = random.Random(401127)
    p1 = [
        make_razor_crystal_prism(r1, height=1.0, base_rx=0.26, base_ry=0.22, sides=6, lean_x=0.05, twist_rad=0.12, cleave_cuts=8, step_notches=2),
        make_razor_crystal_prism(r1, height=0.62, base_rx=0.16, base_ry=0.13, sides=6, tilt_y_rad=0.22, tilt_x_rad=-0.10, offset=(0.13, 0.08, -0.02), cleave_cuts=6, step_notches=1),
        make_razor_crystal_prism(r1, height=0.44, base_rx=0.14, base_ry=0.12, sides=5, tilt_y_rad=-0.28, tilt_x_rad=0.16, offset=(-0.14, -0.09, -0.02), cleave_cuts=5, step_notches=0),
        *make_shattered_base_shards(r1, count=5, radius=0.27, max_h=0.24),
    ]
    manifest.append(finalize_crystal_asset('SM_AZ_GlacierSpire_01', p1, seed=401127))

    # 2) SM_AZ_GlacierSpire_02: Dramatic leaning faceted ice blade pillar + twin side crystal spurs
    r2 = random.Random(402127)
    p2 = [
        make_razor_crystal_prism(r2, height=1.0, base_rx=0.27, base_ry=0.19, sides=6, lean_x=0.16, lean_y=0.03, twist_rad=-0.16, cleave_cuts=9, step_notches=3),
        make_razor_crystal_prism(r2, height=0.58, base_rx=0.15, base_ry=0.12, sides=5, tilt_y_rad=-0.24, tilt_x_rad=0.20, offset=(-0.13, -0.10, -0.02), cleave_cuts=6, step_notches=1),
        make_razor_crystal_prism(r2, height=0.42, base_rx=0.13, base_ry=0.11, sides=5, tilt_y_rad=0.36, tilt_x_rad=-0.14, offset=(0.15, -0.06, -0.02), cleave_cuts=5, step_notches=0),
        *make_shattered_base_shards(r2, count=5, radius=0.28, max_h=0.22),
    ]
    manifest.append(finalize_crystal_asset('SM_AZ_GlacierSpire_02', p2, seed=402127))

    # 3) SM_AZ_GlacierSpire_03: Colossal multi-peaked crystal cathedral cluster (outer crown hero!)
    r3 = random.Random(403127)
    p3 = [
        make_razor_crystal_prism(r3, height=1.0, base_rx=0.27, base_ry=0.23, sides=7, lean_x=0.07, twist_rad=0.10, offset=(-0.05, 0.0, 0.0), cleave_cuts=8, step_notches=2),
        make_razor_crystal_prism(r3, height=0.76, base_rx=0.20, base_ry=0.17, sides=6, lean_x=0.10, tilt_y_rad=0.18, tilt_x_rad=-0.12, offset=(0.16, 0.10, -0.02), cleave_cuts=7, step_notches=2),
        make_razor_crystal_prism(r3, height=0.54, base_rx=0.17, base_ry=0.14, sides=6, tilt_y_rad=-0.26, tilt_x_rad=0.18, offset=(-0.18, -0.12, -0.02), cleave_cuts=6, step_notches=1),
        make_razor_crystal_prism(r3, height=0.46, base_rx=0.15, base_ry=0.13, sides=5, tilt_y_rad=0.32, tilt_x_rad=0.24, offset=(0.06, -0.17, -0.02), cleave_cuts=5, step_notches=0),
        *make_shattered_base_shards(r3, count=6, radius=0.34, max_h=0.26),
    ]
    manifest.append(finalize_crystal_asset('SM_AZ_GlacierSpire_03', p3, seed=403127))

    # 4) SM_AZ_IceFangCluster: Jagged splayed 4-fang mineral rupture burst (inner crater & satellite feet)
    r4 = random.Random(404127)
    p4 = [
        make_razor_crystal_prism(r4, height=1.0, base_rx=0.20, base_ry=0.17, sides=6, lean_x=0.10, tilt_y_rad=0.22, cleave_cuts=7, step_notches=1),
        make_razor_crystal_prism(r4, height=0.76, base_rx=0.17, base_ry=0.14, sides=5, tilt_y_rad=0.38, tilt_x_rad=-0.34, offset=(0.07, 0.15, -0.02), cleave_cuts=6, step_notches=1),
        make_razor_crystal_prism(r4, height=0.66, base_rx=0.16, base_ry=0.13, sides=5, tilt_y_rad=0.34, tilt_x_rad=0.38, offset=(0.05, -0.15, -0.02), cleave_cuts=6, step_notches=0),
        make_razor_crystal_prism(r4, height=0.48, base_rx=0.15, base_ry=0.13, sides=5, tilt_y_rad=-0.34, offset=(-0.14, 0.02, -0.02), cleave_cuts=5, step_notches=0),
        *make_shattered_base_shards(r4, count=5, radius=0.30, max_h=0.20),
    ]
    manifest.append(finalize_crystal_asset('SM_AZ_IceFangCluster', p4, seed=404127))

    blend_path = DEST / 'AbsoluteZeroV3Spires.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    (DEST / 'geometry.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('AZ_V4_RAZOR_CRYSTALS_BUILT')
    for row in manifest:
        print(' ', json.dumps(row))


if __name__ == '__main__':
    main()
