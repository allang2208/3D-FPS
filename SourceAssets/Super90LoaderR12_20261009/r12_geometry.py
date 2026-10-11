"""R12 loader geometry: contoured port funnel, slotted tube, grip post plunger.

exec() after r12_core.py. Funnel vertices are in native bind space (the gun
mesh space). Tube vertices are in tube space (+Y toward the nose, body on -Y);
plunger vertices are in grip-post space (post axis +Z, PUSH toward the nose).
Game attachment geometry, not manufacturing data.
"""
import bmesh
from mathutils.bvhtree import BVHTree

def _receiver_tree():
    body = bpy.data.objects['Super90_body']; me = body.data; me.calc_loop_triangles()
    vs = [body.matrix_world @ v.co for v in me.vertices]
    return BVHTree.FromPolygons(vs, [tuple(t.vertices) for t in me.loop_triangles], all_triangles=True)

def rounded_rect(cx, cy, hx, hy, r, n):
    """Closed outline, counter-clockwise, evenly spaced by arc length."""
    r = min(r, hx, hy); sx, sy = hx - r, hy - r
    segs = []
    corners = [(sx, sy, 0.), (-sx, sy, math.pi / 2), (-sx, -sy, math.pi), (sx, -sy, 1.5 * math.pi)]
    for i, (ox, oy, a0) in enumerate(corners):
        segs.append(('arc', ox, oy, a0)); nxt = corners[(i + 1) % 4]
        segs.append(('line', ox + r * math.cos(a0 + math.pi / 2), oy + r * math.sin(a0 + math.pi / 2),
                     nxt[0] + r * math.cos(nxt[2]), nxt[1] + r * math.sin(nxt[2])))
    lengths = [math.pi / 2 * r if s[0] == 'arc' else math.hypot(s[3] - s[1], s[4] - s[2]) for s in segs]
    total = sum(lengths); pts = []
    for k in range(n):
        d = total * k / n
        for s, ln in zip(segs, lengths):
            if d <= ln + 1e-12:
                t = d / ln if ln else 0.
                if s[0] == 'arc':
                    a = s[3] + t * math.pi / 2; pts.append((cx + s[1] + r * math.cos(a), cy + s[2] + r * math.sin(a)))
                else:
                    pts.append((cx + s[1] + (s[3] - s[1]) * t, cy + s[2] + (s[4] - s[2]) * t))
                break
            d -= ln
    return pts

def _new_object(name, verts, faces, materials, face_materials):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces)
    for m in materials: me.materials.append(m)
    for poly, mi in zip(me.polygons, face_materials): poly.material_index = mi
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces)); bm.to_mesh(me); bm.free()
    me.shade_smooth()
    try: me.set_sharp_from_angle(angle=math.radians(38))
    except Exception: pass
    ob = bpy.data.objects.new(name, me); scene.collection.objects.link(ob)
    return ob

def _loft(rings, closed_top=False):
    """Quads between consecutive equal-length closed rings."""
    verts = [v for ring in rings for v in ring]; n = len(rings[0]); faces = []
    for r in range(len(rings) - 1):
        a = r * n; b = (r + 1) * n
        for i in range(n):
            j = (i + 1) % n; faces.append((a + i, a + j, b + j, b + i))
    return verts, faces

def build_funnel(materials):
    """Low-profile flared funnel hugging the receiver underside around the port."""
    tree = _receiver_tree(); N = 72
    def floor_z(x, y):
        best = None
        for dx in (0., .0012, -.0012):
            hit = tree.ray_cast(Vector((x + dx, y, -.86)), Vector((0, 0, 1)), .09)[0]
            if hit is not None and hit.z < -.776: best = hit.z if best is None else max(best, hit.z)
        return best
    # Receiver bottom is flat across the port edges (-.7875 .. -.7880).
    edge = [floor_z(sx * .0128, -.058 + .083 * k / 20) for sx in (-1, 1) for k in range(21)]
    edge = [z for z in edge if z is not None]
    z_floor = sum(edge) / len(edge) if edge else -.7877
    z_top = z_floor - .00035                       # bearing face 0.35 mm below the steel
    depth = .012; z_mouth = z_top - depth
    yc_port, hy_port = -.0165, .0415
    lip = rounded_rect(0., yc_port, .0090, hy_port - .0015, .0055, N)          # covers the port edge 1.5 mm
    throat = rounded_rect(0., yc_port, .0108, hy_port + .0003, .0062, N)
    mouth_in = rounded_rect(0., -.0145, .0188, .0455, .0105, N)
    mouth_out = rounded_rect(0., -.0145, .0213, .0480, .0128, N)
    top_out = rounded_rect(0., yc_port + .0003, .01500, hy_port + .0030, .0080, N)
    skirt = rounded_rect(0., yc_port + .0003, .01530, hy_port + .0036, .0084, N)
    rings = []
    # Inner: lip (chamfered over the port edge) -> throat -> flared trumpet -> mouth.
    rings.append([(x, y, z_top + .0002) for x, y in lip])
    rings.append([(x, y, z_top - .0016) for x, y in throat])
    for k in range(1, 8):
        t = k / 7; e = t ** 1.7
        rings.append([(a[0] + (b[0] - a[0]) * e, a[1] + (b[1] - a[1]) * e, z_top - .0016 + (z_mouth + .0012 - (z_top - .0016)) * t)
                      for a, b in zip(throat, mouth_in)])
    # Rounded mouth lip (quarter circles inside -> outside).
    for k in range(1, 5):
        a = math.pi / 2 * k / 4
        rings.append([(pi[0] + (po[0] - pi[0]) * (1 - math.cos(a)), pi[1] + (po[1] - pi[1]) * (1 - math.cos(a)), z_mouth + .0012 - .0012 * math.sin(a))
                      for pi, po in zip(mouth_in, mouth_out)])
    # Outer: mouth -> slight bulge -> top edge -> skirt rising onto the receiver side.
    for k in range(1, 7):
        t = k / 6; e = 1 - (1 - t) ** 1.5
        rings.append([(a[0] + (b[0] - a[0]) * e, a[1] + (b[1] - a[1]) * e, z_mouth + .0006 + (z_top - .0010 - (z_mouth + .0006)) * t)
                      for a, b in zip(mouth_out, top_out)])
    rings.append([(x, y, z_top + .0026) for x, y in skirt])
    rings.append([(x * .985, y, z_top + .0034) for x, y in skirt])
    # Bearing face back to the lip ring closes the shell.
    rings.append([(x, y, z_top + .0002) for x, y in rounded_rect(0., yc_port + .0003, .0145, hy_port + .0024, .0076, N)])
    rings.append(rings[0])
    verts, faces = _loft([[Vector(v) for v in r] for r in rings[:-1]] + [[Vector(v) for v in rings[0]]])
    # The duplicated closing ring is welded below.
    mats = [0] * len(faces)
    # Guide rails along the inner side walls (insertion keys) and pin ears.
    def box(center, size, axes):
        cx, cy, cz = center; base = len(verts)
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    verts.append(Vector(center) + axes[0] * (sx * size[0] / 2) + axes[1] * (sy * size[1] / 2) + axes[2] * (sz * size[2] / 2))
        for q in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
            faces.append(tuple(base + i for i in q)); mats.append(1)
    ax = (Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
    for sx in (-1, 1):
        for k in range(3):
            t0, t1 = k / 3, (k + 1) / 3
            def wall(t):
                e = t ** 1.7; return .0108 + (.0188 - .0108) * e, z_top - .0016 + (z_mouth + .0012 - (z_top - .0016)) * t
            (x0, z0), (x1, z1) = wall(t0), wall(t1)
            xm, zm = (x0 + x1) / 2, (z0 + z1) / 2
            tilt = Vector((x1 - x0, 0, z1 - z0)).normalized(); nrm = Vector((0, 1, 0)).cross(tilt).normalized() * sx
            box((sx * (xm - .0007), -.024, zm), (.0016, .022, (Vector((x1 - x0, 0, z1 - z0))).length + .0004), (nrm, ax[1], tilt))
        # Ear rising onto the receiver side, with a cross-pin head.
        box((sx * .01565, -.0505, z_top + .0058), (.0016, .0115, .0086), ax)
    pin = []
    for sx in (-1, 1):
        base = len(verts); c = Vector((sx * .0173, -.0505, z_top + .0070)); n = 20
        for ring_x in (0., .0011):
            for k in range(n):
                a = 2 * math.pi * k / n
                verts.append(c + Vector((sx * ring_x, .0025 * math.cos(a), .0025 * math.sin(a)) if ring_x == 0. else (sx * ring_x, .0020 * math.cos(a), .0020 * math.sin(a))))
        for k in range(n):
            j = (k + 1) % n; faces.append((base + k, base + j, base + n + j, base + n + k)); mats.append(1)
        faces.append(tuple(base + n + k for k in range(n))); mats.append(1)
    ob = _new_object('SM_Super90_LoaderGuide', verts, faces, materials, mats)
    bm = bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces)); bm.to_mesh(ob.data); bm.free()
    ob.data.shade_smooth()
    try: ob.data.set_sharp_from_angle(angle=math.radians(38))
    except Exception: pass
    return ob, {'z_floor_m': z_floor, 'z_top_m': z_top, 'z_mouth_m': z_mouth, 'depth_m': depth,
                'port_inner_half_m': [.0108, hy_port], 'mouth_inner_half_m': [.0188, .0455], 'wall_m': .0025}

def _tube_mesh(lay):
    """Slotted loader tube in tube space; slot faces the grip post."""
    psi = math.radians(lay.get('post_psi', 0.))
    slot_dir = math.atan2(-math.cos(psi), -math.sin(psi))        # angle of radial in (x, z) plane
    R, r, N = .01325, .01165, 72; half = math.asin(.0040 / R)
    L = tube_len(lay); SL0 = -L + .012                               # slot starts just ahead of the rear cap
    stations = [-L, -L + .010, SL0, -.020, -.016, -.004, -.0015, 0.]
    def in_slot(a, y0, y1):
        d = (a - slot_dir + math.pi) % (2 * math.pi) - math.pi
        return abs(d) < half and y0 >= SL0 - 1e-6 and y1 <= -.020 + 1e-6
    verts = []; faces = []; mats = []
    def ring(y, rad):
        base = len(verts)
        for k in range(N):
            a = 2 * math.pi * k / N; verts.append(Vector((rad * math.cos(a), y, rad * math.sin(a))))
        return base
    outer = []; inner = []
    radii = {-.0015: R - .0006, 0.: R - .0016}
    for y in stations: outer.append(ring(y, radii.get(y, R)))
    for y in stations: inner.append(ring(y, r))
    for si in range(len(stations) - 1):
        y0, y1 = stations[si], stations[si + 1]
        steel = y0 >= -.016 - 1e-6 or y1 <= -L + .010 + 1e-6
        for k in range(N):
            j = (k + 1) % N; a = 2 * math.pi * (k + .5) / N
            if in_slot(a, y0, y1): continue
            faces.append((outer[si] + k, outer[si] + j, outer[si + 1] + j, outer[si + 1] + k)); mats.append(2 if steel else 0)
            faces.append((inner[si] + k, inner[si + 1] + k, inner[si + 1] + j, inner[si] + j)); mats.append(0)
    # Slot side walls and ends.
    si0 = stations.index(SL0); si1 = stations.index(-.020)
    for k in range(N):
        j = (k + 1) % N; a = 2 * math.pi * (k + .5) / N; an = 2 * math.pi * (j + .5) / N; ap = 2 * math.pi * (k - .5) / N
        if in_slot(a, SL0, -.020) and not in_slot(ap, SL0, -.020):
            faces.append((outer[si0] + k, outer[si1] + k, inner[si1] + k, inner[si0] + k)); mats.append(0)
        if in_slot(a, SL0, -.020) and not in_slot(an, SL0, -.020):
            faces.append((outer[si0] + j, inner[si0] + j, inner[si1] + j, outer[si1] + j)); mats.append(0)
        if in_slot(a, SL0, -.020):
            faces.append((outer[si0] + k, inner[si0] + k, inner[si0] + j, outer[si0] + j)); mats.append(0)
            faces.append((outer[si1] + k, outer[si1] + j, inner[si1] + j, inner[si1] + k)); mats.append(0)
    # Nose face ring and closed rear cap.
    for k in range(N):
        j = (k + 1) % N
        faces.append((outer[-1] + k, inner[-1] + k, inner[-1] + j, outer[-1] + j)); mats.append(2)
    faces.append(tuple(outer[0] + k for k in reversed(range(N)))); mats.append(2)
    faces.append(tuple(inner[0] + k for k in range(N))); mats.append(2)
    return verts, faces, mats

def _plunger_mesh():
    """Grip post (polymer), base flange, gusset through the slot and pusher (steel)."""
    verts = []; faces = []; mats = []; N = 48
    R = POST['radius_m']; ztop = POST['top_m']; zbot = POST['base_m']; zt = POST['tube_axis_z_m']
    dome0 = ztop - R * .6
    profile = [(R * .92, zbot), (R, zbot + .0015)] + [(R, zbot + (dome0 - zbot) * k / 6) for k in range(1, 7)]
    profile += [(R * math.cos(a), dome0 + R * .6 * math.sin(a)) for a in [math.pi / 2 * k / 6 for k in range(1, 6)]]
    rings = []
    for rad, z in profile:
        base = len(verts)
        for k in range(N):
            a = 2 * math.pi * k / N; verts.append(Vector((rad * math.cos(a), rad * math.sin(a), z)))
        rings.append(base)
    for a, b in zip(rings, rings[1:]):
        for k in range(N):
            j = (k + 1) % N; faces.append((a + k, a + j, b + j, b + k)); mats.append(1)
    tip = len(verts); verts.append(Vector((0, 0, ztop)))
    for k in range(N):
        j = (k + 1) % N; faces.append((rings[-1] + k, rings[-1] + j, tip)); mats.append(1)
    bottom = len(verts); verts.append(Vector((0, 0, zbot)))
    for k in range(N):
        j = (k + 1) % N; faces.append((rings[0] + j, rings[0] + k, bottom)); mats.append(2)
    push = Vector(PUSH).normalized(); side = Vector((0, 0, 1)).cross(push).normalized()
    def block(c, ex, ey, ez):
        base = len(verts)
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1): verts.append(c + ex * sx + ey * sy + ez * sz)
        for q in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
            faces.append(tuple(base + i for i in q)); mats.append(2)
    # Base flange under the knob.
    block(Vector((0, 0, zbot - .0015)), push * .016, side * .016, Vector((0, 0, .0015)))
    # Load path knob -> tube, kept clear of the hypothenar: 4 mm plate down to a
    # carrier saddle riding on the tube, then a 7 mm web through the slot.
    hl, hw = POST.get('saddle_half_m', (.012, .007)); sb, st_ = POST.get('saddle_bottom_m', -.067), POST.get('saddle_top_m', -.058)
    block(Vector((0, 0, (zbot - .003 + st_) / 2)), push * hl, side * .002, Vector((0, 0, (zbot - .003 - st_) / 2)))
    block(Vector((0, 0, (sb + st_) / 2)), push * (hl + .002), side * hw, Vector((0, 0, (st_ - sb) / 2)))
    block(Vector((0, 0, (zt + sb) / 2)), push * .011, side * .0035, Vector((0, 0, (sb - zt) / 2)))
    # Pusher disc inside the tube (centred on the tube axis).
    c = Vector((0, 0, zt)); base = len(verts); n = 32
    for off in (-.010, .010):
        for k in range(n):
            a = 2 * math.pi * k / n
            verts.append(c + push * off + side * (.0110 * math.cos(a)) + Vector((0, 0, .0110 * math.sin(a))))
    for k in range(n):
        j = (k + 1) % n; faces.append((base + k, base + j, base + n + j, base + n + k)); mats.append(2)
    faces.append(tuple(base + k for k in reversed(range(n)))); mats.append(2)
    faces.append(tuple(base + n + k for k in range(n))); mats.append(2)
    return verts, faces, mats

def build_props(materials, lay):
    tv, tf, tm = _tube_mesh(lay)
    tube = _new_object('SpeedloaderTube', tv, tf, materials, tm)
    pv, pf, pm = _plunger_mesh()
    plunger = _new_object('SpeedloaderPlunger', pv, pf, materials, pm)
    return tube, plunger
