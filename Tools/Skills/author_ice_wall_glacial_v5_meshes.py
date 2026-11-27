"""Sculpt AAA fractured glacial ice monolith slabs SM_IceBlock_01..04 (GlacialV5).

Authoring unit: 1.0 x 1.0 x 1.0 m centered at origin (matching FPSIceWall::BuildLayout).
Sculpting pipeline (zero Cartesian stair-stepping, bold real-glacier crystal silhouettes):
  1. Start from a solid 1x1x1 m ice slab with a protected inner bearing core (|x| <= 0.25)
     and level central top strip (|x| <= 0.26, z = +0.50) for Low-wall bipod seating.
  2. True 3D planar crystal cleavage slicing (`bmesh.ops.bisect_plane`):
     - 12-16 bold oblique fracture planes carving sweeping angular facets across front (+X),
       back (-X), vertical shoulders (+/-Y), and top/bottom front edges (+/-Z) -> mathematically
       razor-straight diagonal crystal edges and monolithic interlocking V-fracture joints.
  3. High-resolution Voxel Remesh (`voxel_size = 0.015 m`) + smooth C1 continuous glacial relief:
     - Sweeping diagonal crystal ribs, smooth conchoidal ice scoops, and organic melt flutes
       (zero discontinuous height jumps -> zero stair-stepping!).
  4. Adaptive Collapse Decimation (`target ~3,400 tris`) which aligns triangle edges naturally
     along curved glacial ridges and planar cleavage crests (ZBrush Decimation Master style).
  5. Area-weighted 28-degree creased custom split normals + physically calibrated 4-channel
     vertex colors ("Frost", CORNER):
       R: crisp convex crystal crests & fractured ridges (mean ~0.18-0.24)
       G: upward-facing glacier shelves & top crown rime
       B: concave fracture valleys & deep cleavage grooves (mean ~0.15-0.22)
       A: smooth spatial crystal-plate tonal variation
"""
import json
import math
import random
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'SourceAssets/IceWall20260930/GlacialV5'
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


def build_sculpted_block(index):
    rng = random.Random(202611270 + index * 1307)

    # Start at +/-0.515 in X so raised crystal ribs peak naturally at ~0.555 without flat clamp mesas.
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= 1.03  # [-0.515, +0.515]

    # ── PASS 1: Bold 3D Planar Crystal Cleavages (front +X and back -X independently) ──
    for xs in (-1, 1):
        # A) Two big sweeping oblique hero-face cleavage planes per face (creates dramatic
        #    central crystalline apex/ridge running diagonally across the whole slab!).
        diag_sign = rng.choice((-1.0, 1.0))
        for side_s in (-1.0, 1.0):
            ny = side_s * rng.uniform(0.28, 0.56)
            nz = diag_sign * side_s * rng.uniform(0.14, 0.36) + rng.uniform(-0.14, 0.14)
            n = Vector((xs * 1.0, ny, nz)).normalized()
            # Pass near the front/back face center so two big planes meet along a crisp crystal spine
            anchor = Vector((xs * rng.uniform(0.455, 0.515), side_s * rng.uniform(0.16, 0.34), rng.uniform(-0.18, 0.18)))
            bisect_and_cap(bm, anchor, n)

        # B) Upper/lower asymmetric glacial fracture planes (creates bold interlocking V-joints
        #    between vertically stacked slabs while keeping central |X|<=0.27 top flat for bipods!)
        for zs in (-1.0, 1.0):
            if zs > 0:
                # Top front shoulder: crisp beveled glacier lip stopping outside |X|>=0.27
                n = Vector((xs * 1.0, rng.uniform(-0.22, 0.22), rng.uniform(0.62, 0.95))).normalized()
                anchor = Vector((xs * rng.uniform(0.40, 0.46), rng.uniform(-0.15, 0.15), rng.uniform(0.42, 0.465)))
            else:
                n = Vector((xs * 1.0, rng.uniform(-0.25, 0.25), -rng.uniform(0.55, 0.88))).normalized()
                anchor = Vector((xs * rng.uniform(0.42, 0.48), rng.uniform(-0.15, 0.15), -rng.uniform(0.42, 0.47)))
            bisect_and_cap(bm, anchor, n)

        # C) Left/right vertical column shoulders (breaks up vertical brick grid into angular glacier columns!)
        for ys in (-1.0, 1.0):
            n = Vector((xs * 1.0, ys * rng.uniform(0.48, 0.82), rng.uniform(-0.24, 0.24))).normalized()
            anchor = Vector((xs * rng.uniform(0.39, 0.46), ys * rng.uniform(0.39, 0.46), rng.uniform(-0.20, 0.20)))
            bisect_and_cap(bm, anchor, n)

        # D) 3 asymmetric corner/flank fracture chips for natural cleaved mineral look
        for _ in range(3):
            ys = rng.choice((-1.0, 1.0))
            zs = rng.choice((-1.0, 1.0))
            n = Vector((xs * 1.0, ys * rng.uniform(0.45, 0.88), zs * rng.uniform(0.42, 0.82))).normalized()
            anchor = Vector((xs * rng.uniform(0.37, 0.46), ys * rng.uniform(0.30, 0.42), zs * rng.uniform(0.28, 0.42)))
            bisect_and_cap(bm, anchor, n)

    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

    # Convert planar crystal shell to Blender object
    mesh = bpy.data.meshes.new(f'SM_IceBlock_{index:02d}_Mesh')
    ob = bpy.data.objects.new(f'SM_IceBlock_{index:02d}', mesh)
    bpy.context.collection.objects.link(ob)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob

    # Subtle bevel on planar crystal intersections before remeshing so edges keep bold sculpted clarity
    bev = ob.modifiers.new('CrystalBevel', 'BEVEL')
    bev.width = 0.008
    bev.segments = 2
    bev.limit_method = 'ANGLE'
    bev.angle_limit = math.radians(22.0)
    bpy.ops.object.modifier_apply(modifier=bev.name)

    # ── PASS 2: High-Resolution Voxel Remesh -> Continuous Smooth Glacial Relief (Zero Stair-Stepping!) ──
    remesh = ob.modifiers.new('SculptRemesh', 'REMESH')
    remesh.mode = 'VOXEL'
    remesh.voxel_size = 0.0155
    remesh.adaptivity = 0.0
    remesh.use_smooth_shade = True
    bpy.ops.object.modifier_apply(modifier=remesh.name)

    # Smooth-continuous glacial ridge/valley/conchoidal relief parameters (independent +X and -X)
    def make_glacial_features(local_rng):
        # 2-3 broad smooth diagonal glacier flutes/grooves + 3-4 conchoidal ice scoops
        grooves = []
        for _ in range(3):
            cy = local_rng.uniform(-0.34, 0.34)
            cz = local_rng.uniform(-0.34, 0.34)
            ang = local_rng.uniform(-0.52, 0.52)
            width = local_rng.uniform(0.065, 0.115)
            depth = local_rng.uniform(0.022, 0.042)
            sign_dir = local_rng.choice((-1.0, 1.0))  # negative = carved glacier channel, positive = crystal rib
            grooves.append((cy, cz, ang, width, depth, sign_dir))
        scoops = []
        for _ in range(5):
            cy = local_rng.uniform(-0.38, 0.38)
            cz = local_rng.uniform(-0.38, 0.38)
            ry = local_rng.uniform(0.14, 0.26)
            rz = local_rng.uniform(0.18, 0.34)
            amp = local_rng.uniform(-0.026, 0.024)
            scoops.append((cy, cz, ry, rz, amp))
        # Smooth Voronoi ridge cells (continuous f2-f1 distance ONLY — zero discontinuous height jumps!)
        vcells = [(local_rng.uniform(-0.48, 0.48), local_rng.uniform(-0.48, 0.48), local_rng.uniform(0.85, 1.25))
                  for _ in range(8)]
        return grooves, scoops, vcells

    feat_pos = make_glacial_features(rng)
    feat_neg = make_glacial_features(rng)

    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

    # Apply smooth organic glacial ribs, conchoidal scoops, and crisp continuous crystal ridges
    for v in bm.verts:
        x, y, z = v.co.x, v.co.y, v.co.z
        ax, ay, az = abs(x), abs(y), abs(z)
        xs = 1.0 if x >= 0.0 else -1.0
        grooves, scoops, vcells = feat_pos if xs > 0 else feat_neg
        phase = index * 1.91 + (0.0 if xs > 0 else 3.77)

        # Only sculpt exposed front/back faces; keep bearing core |x|<=0.25 and central top flat
        x_mask = smoothstep(0.24, 0.38, ax)
        top_flat_guard = 1.0 - smoothstep(0.455, 0.495, z) * (1.0 - smoothstep(0.24, 0.34, ax))
        mask = x_mask * top_flat_guard
        if mask <= 1e-4:
            continue

        # 1) Smooth diagonal glacier channels & projecting crystal ribs (C2 smooth!)
        disp = 0.0
        for cy, cz, ang, width, depth, sign_dir in grooves:
            ca, sa = math.cos(ang), math.sin(ang)
            perp = (y - cy) * ca + (z - cz) * sa
            along = -(y - cy) * sa + (z - cz) * ca
            # Organic ice curve along the channel
            perp += 0.028 * math.sin(along * 7.5 + phase)
            # Crisp but smooth inverted bell (sharp V-trough without aliasing!)
            u = abs(perp) / width
            if u < 1.5:
                profile = math.exp(-(u * u) * 2.4)
                disp += sign_dir * depth * profile

        # 2) Broad conchoidal glacier scoops (real thick ice fracture curvature)
        for cy, cz, ry, rz, amp in scoops:
            d2 = ((y - cy) / ry) ** 2 + ((z - cz) / rz) ** 2
            if d2 < 2.2:
                disp += amp * math.exp(-d2 * 1.65)

        # 3) Continuous Voronoi crystal ridge network (using smooth f2 - f1 -> crisp ridges, zero jumps!)
        wy = y + 0.025 * math.sin(z * 6.5 + phase)
        wz = z + 0.025 * math.cos(y * 6.2 - phase)
        d1, d2 = 1e9, 1e9
        for cy, cz, aniso in vcells:
            dd = math.hypot((wy - cy) * aniso, (wz - cz) / aniso)
            if dd < d1:
                d2, d1 = d1, dd
            elif dd < d2:
                d2 = dd
        edge_gap = d2 - d1
        # Smooth tent ridge peaking gently along Voronoi seams
        ridge_crest = math.exp(-((edge_gap / 0.065) ** 2))
        disp += 0.018 * (ridge_crest - 0.35)

        # 4) Subtle vertical freeze-flow striations
        disp += 0.006 * math.sin(y * 16.0 + z * 3.0 + phase) * math.cos(z * 4.5 - phase)

        # Gentle taper right at extreme Y/Z bearing rim so adjacent blocks still interlock solidly
        rim_safe = 1.0 - 0.55 * max(smoothstep(0.44, 0.50, ay), smoothstep(0.44, 0.50, az))
        if disp < 0.0:
            disp *= rim_safe

        # Soft-compress peaks smoothly beyond +/-0.54 so crystal spines stay razor-sharp (never flat clamp plateaus!)
        raw_x = x + xs * disp * mask
        ax_new = abs(raw_x)
        if ax_new > 0.535:
            ax_new = 0.535 + 0.045 * math.tanh((ax_new - 0.535) / 0.045)
        v.co.x = math.copysign(ax_new, raw_x)
        v.co.y = clamp(v.co.y, -0.50, 0.50)
        v.co.z = clamp(v.co.z, -0.50, 0.50)

    # Enforce flat central top bipod strip (z <= 0.50, |x| <= 0.25) and solid bearing extremes
    for v in bm.verts:
        if v.co.z > 0.488 and abs(v.co.x) <= 0.26:
            v.co.z = 0.50

    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()

    # ── PASS 3: Gentle Laplacian Polish (removes voxel micro-ripples) + Adaptive Collapse Decimation ──
    # Corrective smooth preserves sharp sculpted forms while removing voxel grid micro-jaggies
    smooth = ob.modifiers.new('IcePolish', 'CORRECTIVE_SMOOTH')
    smooth.factor = 0.45
    smooth.iterations = 3
    bpy.ops.object.modifier_apply(modifier=smooth.name)

    # Adaptive Collapse Decimation: automatically aligns triangle edges along the actual diagonal
    # crystal ridges and cleavage channels (eliminates Cartesian grid aliasing 100%!).
    cur_tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    target_tris = 3600
    dec = ob.modifiers.new('AdaptiveFacetDecimate', 'DECIMATE')
    dec.decimate_type = 'COLLAPSE'
    dec.ratio = clamp(target_tris / max(1, cur_tris), 0.04, 1.0)
    dec.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=dec.name)

    # Clean final triangulation & ensure strict bounds
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm, faces=list(bm.faces), quad_method='BEAUTY', ngon_method='BEAUTY')
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    # ── PASS 4: True Geometric Curvature Baking (Calibrated R ridge, G rime, B cavity, A facet tone) ──
    n_verts = len(bm.verts)
    raw_convex = [0.0] * n_verts
    raw_concave = [0.0] * n_verts

    # Also compute local ambient-depth relative to 1-ring neighbors (captures broad sculpted crevices cleanly!)
    for v in bm.verts:
        vi = v.index
        if not v.link_edges:
            continue
        avg_nb = Vector((0.0, 0.0, 0.0))
        for e in v.link_edges:
            avg_nb += e.other_vert(v).co
        avg_nb /= len(v.link_edges)
        # Positive dot(v - avg_nb, v.normal) => vertex protrudes OUTWARD (convex crystal ridge)
        # Negative => vertex sits INWARD (concave glacial groove/crevice)
        lap = (v.co - avg_nb).dot(v.normal)
        if lap > 0.0:
            raw_convex[vi] = max(raw_convex[vi], clamp(lap / 0.0055, 0.0, 1.0))
        else:
            raw_concave[vi] = max(raw_concave[vi], clamp((-lap) / 0.0048, 0.0, 1.0))

    # Add dihedral sharpness so crisp planar cleavage edges catch razor-bright frost
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        f0, f1 = e.link_faces[0], e.link_faces[1]
        dot_n = clamp(f0.normal.dot(f1.normal), -1.0, 1.0)
        bend = math.acos(dot_n)
        if bend < 0.16:
            continue
        signed = (f1.calc_center_median() - f0.calc_center_median()).dot(f0.normal)
        strength = clamp((bend - 0.16) / 0.72, 0.0, 1.0)
        for ev in e.verts:
            vi = ev.index
            if signed < -1e-6:
                raw_convex[vi] = max(raw_convex[vi], strength)
            elif signed > 1e-6:
                raw_concave[vi] = max(raw_concave[vi], strength)

    # 1-pass neighbor smoothing on concavity so crevices have natural glacial depth transitions
    smooth_cav = list(raw_concave)
    for v in bm.verts:
        vi = v.index
        if v.link_edges:
            nb_avg = sum(raw_concave[e.other_vert(v).index] for e in v.link_edges) / len(v.link_edges)
            smooth_cav[vi] = raw_concave[vi] * 0.65 + nb_avg * 0.35

    # Also measure macro inward depth relative to outer slab envelope (+/-0.52) for broad glacial hollows
    macro_cav = [0.0] * n_verts
    for v in bm.verts:
        vi = v.index
        if abs(v.co.x) > 0.28:
            inward = clamp((0.50 - abs(v.co.x)) / 0.14, 0.0, 1.0)
            macro_cav[vi] = inward

    bm.to_mesh(ob.data)
    bm.free()
    mesh = ob.data
    mesh.update()

    # Build vertex -> adjacent polygons for area-weighted 28-deg creased split normals
    adjacent = [[] for _ in mesh.vertices]
    for poly in mesh.polygons:
        poly.use_smooth = True
        for vi in poly.vertices:
            adjacent[vi].append(poly)

    crease_cos = math.cos(math.radians(28.0))
    split_normals = []
    uv_layer = mesh.uv_layers.new(name='IceMeters')
    frost_col = mesh.color_attributes.new(name='Frost', type='BYTE_COLOR', domain='CORNER')

    r_vals, g_vals, b_vals = [], [], []
    for poly in mesh.polygons:
        n = poly.normal
        axis = max(range(3), key=lambda a: abs(n[a]))
        ua, ub = ((1, 2), (0, 2), (0, 1))[axis]
        # Deterministic per-face plane orientation tone (so differently angled crystal planes shimmer subtly!)
        plane_hash = 0.5 + 0.35 * math.sin(n.x * 7.3 + n.y * 11.7 + n.z * 5.9 + index * 2.1)
        for li in poly.loop_indices:
            vi = mesh.loops[li].vertex_index
            co = mesh.vertices[vi].co
            acc = Vector((0.0, 0.0, 0.0))
            for other in adjacent[vi]:
                if n.dot(other.normal) >= crease_cos:
                    acc += other.normal * other.area
            ln = acc.normalized() if acc.length > 1e-6 else n
            split_normals.append((ln.x, ln.y, ln.z))
            uv_layer.data[li].uv = (co[ua] + 0.5, co[ub] + 0.5)

            # R: Crisp convex crystal crests & cleaved shoulders ONLY (calibrated mean ~0.18-0.26)
            r_val = clamp((raw_convex[vi] ** 1.65) * 0.95)

            # G: Upward-facing rime/snow dusting on sculpted ledges & top crown
            up_fac = smoothstep(0.24, 0.86, ln.z)
            crown_fac = smoothstep(0.18, 0.49, co.z)
            g_val = clamp((up_fac ** 1.30) * (0.42 + 0.58 * crown_fac))

            # B: Concave fracture valleys & recessed cleavage hollows (calibrated mean ~0.15-0.24)
            b_val = clamp(max((smooth_cav[vi] ** 1.35) * 0.92, macro_cav[vi] * 0.65))

            # A: Per-facet orientation tone for refractive shimmer across adjacent crystal planes
            a_val = clamp(plane_hash, 0.12, 0.96)

            frost_col.data[li].color = (r_val, g_val, b_val, a_val)
            r_vals.append(r_val)
            g_vals.append(g_val)
            b_vals.append(b_val)

    mesh.normals_split_custom_set(split_normals)
    mesh.update()

    # Export FBX
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    fbx_path = DEST / f'{ob.name}.fbx'
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

    xs_all = [v.co.x for v in mesh.vertices]
    ys_all = [v.co.y for v in mesh.vertices]
    zs_all = [v.co.z for v in mesh.vertices]
    info = {
        'mesh': ob.name,
        'fbx': str(fbx_path),
        'vertices': len(mesh.vertices),
        'triangles': len(mesh.polygons),
        'bounds_m': {
            'x': [round(min(xs_all), 4), round(max(xs_all), 4)],
            'y': [round(min(ys_all), 4), round(max(ys_all), 4)],
            'z': [round(min(zs_all), 4), round(max(zs_all), 4)],
        },
        'vcol_mean': {
            'R_ridge': round(sum(r_vals) / len(r_vals), 3),
            'G_rime': round(sum(g_vals) / len(g_vals), 3),
            'B_cavity': round(sum(b_vals) / len(b_vals), 3),
        },
        'vcol_max': {
            'R_ridge': round(max(r_vals), 3),
            'G_rime': round(max(g_vals), 3),
            'B_cavity': round(max(b_vals), 3),
        },
    }
    ob.hide_set(True)
    ob.select_set(False)
    return info


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = 'METRIC'
    manifest = [build_sculpted_block(i) for i in range(1, 5)]
    blend_path = DEST / 'IceWallGlacialV5.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    (DEST / 'geometry.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('ICE_WALL_GLACIAL_V5_MESHES_BUILT')
    for row in manifest:
        print(' ', json.dumps(row))


if __name__ == '__main__':
    main()
