"""Author SM_SmartTurret modular meshes (Scheme B) in UE centimetres (+X aim, -X console, Z=0 base)."""
from pathlib import Path
import sys
from math import atan2, cos, pi, sin, sqrt, tau
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "GarrisonWorkshop"))
sys.path.insert(0, str(HERE.parent / "HotOil"))
sys.path.insert(0, str(HERE.parent / "LightningSpire"))
from author_workshop import TILES
from author_spire import SpireShop
import source_mesh

STONE = "TurretStone"
IRON = "TurretCastIron"
BRASS = "TurretBrass"
GUNMETAL = "TurretGunmetal"
CHROME = "TurretSteelChrome"
OPTIC = "TurretOpticGlow"

TILES.update({
    STONE: 88.0,
    IRON: 52.0,
    BRASS: 34.0,
    GUNMETAL: 42.0,
    CHROME: 32.0,
    OPTIC: 16.0,
})


def _ortho_frame(axis, up_hint=(0.0, 0.0, 1.0)):
    ax = np.array(axis, dtype=float, copy=True)
    ax /= max(float(np.linalg.norm(ax)), 1e-8)
    ref = np.asarray(up_hint, dtype=float)
    if abs(float(np.dot(ax, ref))) > 0.94:
        ref = np.array([1.0, 0.0, 0.0]) if abs(ax[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = np.cross(ref, ax)
    u /= max(float(np.linalg.norm(u)), 1e-8)
    v = np.cross(ax, u)
    v /= max(float(np.linalg.norm(v)), 1e-8)
    return ax, u, v


class TurretShop(SpireShop):
    def add_oriented_quad(self, p0, p1, p2, p3, norm, mat, uv_rect=None):
        n = np.asarray(norm, dtype=float)
        n /= max(float(np.linalg.norm(n)), 1e-8)
        if uv_rect is not None:
            pts = [np.asarray(p, float) for p in (p0, p1, p2, p3)]
            self.add_oriented_tri(pts[0], pts[1], pts[2], n, n, n, uv_rect[0], uv_rect[1], uv_rect[2], mat)
            self.add_oriented_tri(pts[0], pts[2], pts[3], n, n, n, uv_rect[0], uv_rect[2], uv_rect[3], mat)
        else:
            self._add_flat_quad(p0, p1, p2, p3, mat)

    def chamfered_box(self, cx, cy, cz, sx, sy, sz, mat, bevel=0.8):
        """Axis-aligned beveled steel/iron block with crisp edge highlights."""
        hx, hy, hz = sx * 0.5, sy * 0.5, sz * 0.5
        b = min(bevel, hx * 0.42, hy * 0.42, hz * 0.42)
        if b <= 0.15:
            b = 0.0
        # Use 8-point bevel along Z or full octo prism when b > 0
        c = np.array([cx, cy, cz], dtype=float)
        if b <= 0.0:
            self.add_oriented_plate((cx, cy, cz), (1, 0, 0), (0, 0, 1), sy, sz, sx, mat)
            return

        # Outer & inset Z-rings for clean chamfered box
        def corners(dx, dy, z_val):
            return [
                c + np.array([dx, -dy, z_val]),
                c + np.array([dx, dy, z_val]),
                c + np.array([-dx, dy, z_val]),
                c + np.array([-dx, -dy, z_val]),
            ]

        # 4 beveled Z bands + 4 beveled X/Y corner chamfers on main walls via lofted 8-gon rings
        def oct_ring(ix, iy, z_val):
            bx = min(b, ix * 0.45)
            by = min(b, iy * 0.45)
            return [
                c + np.array([ix - bx, -iy, z_val]),
                c + np.array([ix, -iy + by, z_val]),
                c + np.array([ix, iy - by, z_val]),
                c + np.array([ix - bx, iy, z_val]),
                c + np.array([-ix + bx, iy, z_val]),
                c + np.array([-ix, iy - by, z_val]),
                c + np.array([-ix, -iy + by, z_val]),
                c + np.array([-ix + bx, -iy, z_val]),
            ]

        r0 = oct_ring(hx - b, hy - b, -hz)
        r1 = oct_ring(hx, hy, -hz + b)
        r2 = oct_ring(hx, hy, hz - b)
        r3 = oct_ring(hx - b, hy - b, hz)
        rings = (r0, r1, r2, r3)
        for k in range(3):
            ra, rb = rings[k], rings[k + 1]
            for i in range(8):
                j = (i + 1) % 8
                self._add_flat_quad(ra[i], ra[j], rb[j], rb[i], mat)
        # Bottom & top caps (8-gon fan)
        for ring, nz in ((r0, -1.0), (r3, 1.0)):
            cap_c = c + np.array([0.0, 0.0, nz * hz])
            n_vec = np.array([0.0, 0.0, nz])
            t = TILES[mat]
            for i in range(8):
                j = (i + 1) % 8
                pa, pb = (ring[j], ring[i]) if nz < 0 else (ring[i], ring[j])
                self.add_oriented_tri(
                    cap_c, pa, pb, n_vec, n_vec, n_vec,
                    (cap_c[0] / t, cap_c[1] / t), (pa[0] / t, pa[1] / t), (pb[0] / t, pb[1] / t), mat
                )

    def oriented_chamfer_beam(self, p_start, p_end, width_y, thick_z, mat, bevel=0.9, up_hint=(0.0, 0.0, 1.0)):
        """Chamfered 8-sided structural beam running from p_start to p_end."""
        a = np.asarray(p_start, dtype=float)
        b = np.asarray(p_end, dtype=float)
        along, u, v = _ortho_frame(b - a, up_hint)
        hw, ht = width_y * 0.5, thick_z * 0.5
        cut = min(bevel, hw * 0.35, ht * 0.35)
        prof = [
            (-hw + cut, -ht), (hw - cut, -ht), (hw, -ht + cut), (hw, ht - cut),
            (hw - cut, ht), (-hw + cut, ht), (-hw, ht - cut), (-hw, -ht + cut),
        ]
        ra = [a + px * u + pz * v for px, pz in prof]
        rb = [b + px * u + pz * v for px, pz in prof]
        for i in range(8):
            j = (i + 1) % 8
            self._add_flat_quad(ra[i], ra[j], rb[j], rb[i], mat)
        t = TILES[mat]
        for pt_c, ring, n_vec in ((a, ra, -along), (b, rb, along)):
            for i in range(8):
                j = (i + 1) % 8
                p0, p1 = (ring[j], ring[i]) if n_vec is along else (ring[i], ring[j])
                self.add_oriented_tri(
                    pt_c, p0, p1, n_vec, n_vec, n_vec,
                    (pt_c[0] / t, pt_c[2] / t), (p0[0] / t, p0[2] / t), (p1[0] / t, p1[2] / t), mat
                )

    def rotated_cylinder_x(self, x0, x1, y_c, z_c, r_x0, r_x1, segs, mat, cap_start=True, cap_end=True):
        """Cylinder/frustum aligned along +X axis centered at (y_c, z_c)."""
        ring0, ring1 = [], []
        norms = []
        for i in range(segs):
            ang = i * tau / segs
            ca, sa = cos(ang), sin(ang)
            ring0.append(np.array([x0, y_c + r_x0 * ca, z_c + r_x0 * sa]))
            ring1.append(np.array([x1, y_c + r_x1 * ca, z_c + r_x1 * sa]))
            # Radial normal tilted slightly for tapered cones
            n_dir = np.array([-(r_x1 - r_x0), (x1 - x0) * ca, (x1 - x0) * sa])
            n_dir /= max(float(np.linalg.norm(n_dir)), 1e-8)
            norms.append(n_dir)
        t = TILES[mat]
        arc_u = max(r_x0, r_x1) * tau
        for i in range(segs):
            j = (i + 1) % segs
            u0, u1 = (i / segs) * arc_u / t, ((i + 1) / segs) * arc_u / t
            v0, v1 = 0.0, abs(x1 - x0) / t
            self.add_oriented_tri(ring0[i], ring0[j], ring1[j], norms[i], norms[j], norms[j], (u0, v0), (u1, v0), (u1, v1), mat)
            self.add_oriented_tri(ring0[i], ring1[j], ring1[i], norms[i], norms[j], norms[i], (u0, v0), (u1, v1), (u0, v1), mat)
        if cap_start and r_x0 > 0.1:
            c0 = np.array([x0, y_c, z_c])
            n0 = np.array([-1.0, 0.0, 0.0])
            for i in range(segs):
                j = (i + 1) % segs
                self.add_oriented_tri(
                    c0, ring0[j], ring0[i], n0, n0, n0,
                    (0.5, 0.5), (0.5 + 0.45 * cos(j * tau / segs), 0.5 + 0.45 * sin(j * tau / segs)),
                    (0.5 + 0.45 * cos(i * tau / segs), 0.5 + 0.45 * sin(i * tau / segs)), mat
                )
        if cap_end and r_x1 > 0.1:
            c1 = np.array([x1, y_c, z_c])
            n1 = np.array([1.0, 0.0, 0.0])
            for i in range(segs):
                j = (i + 1) % segs
                self.add_oriented_tri(
                    c1, ring1[i], ring1[j], n1, n1, n1,
                    (0.5, 0.5), (0.5 + 0.45 * cos(i * tau / segs), 0.5 + 0.45 * sin(i * tau / segs)),
                    (0.5 + 0.45 * cos(j * tau / segs), 0.5 + 0.45 * sin(j * tau / segs)), mat
                )

    def rotated_cylinder_y(self, y0, y1, x_c, z_c, r, segs, mat, cap_ends=True):
        """Cylinder aligned along Y axis centered at (x_c, z_c)."""
        ring0, ring1, norms = [], [], []
        for i in range(segs):
            ang = i * tau / segs
            ca, sa = cos(ang), sin(ang)
            ring0.append(np.array([x_c + r * ca, y0, z_c + r * sa]))
            ring1.append(np.array([x_c + r * ca, y1, z_c + r * sa]))
            norms.append(np.array([ca, 0.0, sa]))
        t = TILES[mat]
        arc_u = r * tau
        for i in range(segs):
            j = (i + 1) % segs
            u0, u1 = (i / segs) * arc_u / t, ((i + 1) / segs) * arc_u / t
            v0, v1 = 0.0, abs(y1 - y0) / t
            self.add_oriented_tri(ring0[i], ring1[j], ring0[j], norms[i], norms[j], norms[j], (u0, v0), (u1, v1), (u1, v0), mat)
            self.add_oriented_tri(ring0[i], ring1[i], ring1[j], norms[i], norms[i], norms[j], (u0, v0), (u0, v1), (u1, v1), mat)
        if cap_ends and r > 0.1:
            for yc, ring, ny in ((y0, ring0, -1.0), (y1, ring1, 1.0)):
                c = np.array([x_c, yc, z_c])
                nv = np.array([0.0, ny, 0.0])
                for i in range(segs):
                    j = (i + 1) % segs
                    pa, pb = (ring[j], ring[i]) if ny > 0 else (ring[i], ring[j])
                    self.add_oriented_tri(c, pa, pb, nv, nv, nv, (0.5, 0.5), (0.0, 0.5), (0.5, 0.0), mat)

    def helical_spring(self, p_start, p_end, coil_r, wire_r, turns, mat, segs_per_turn=14, wire_sides=8):
        """Swept helical recoil spring between p_start and p_end."""
        a = np.asarray(p_start, dtype=float)
        b = np.asarray(p_end, dtype=float)
        axis = b - a
        _, u, v = _ortho_frame(axis)
        steps = max(24, int(turns * segs_per_turn))
        pts = []
        for k in range(steps + 1):
            t = k / float(steps)
            ang = t * turns * tau
            pts.append(a + axis * t + coil_r * (cos(ang) * u + sin(ang) * v))
        self.swept_tube(pts, wire_r, wire_sides, mat, closed=False, cap_ends=True)

    def toothed_gear_ring(self, z0, z1, r_inner, r_root, r_tip, num_teeth, mat):
        """Machined 3D slewing gear ring with distinct trapezoidal gear teeth."""
        # Inner drum collar
        self.smooth_lathe(
            [(r_inner, z0), (r_root + 0.15, z0), (r_root + 0.15, z1), (r_inner, z1), (r_inner, z0)],
            48, mat, tile_u=r_root * tau
        )
        # Individual trapezoidal teeth around circumference
        tooth_step = tau / num_teeth
        half_base = tooth_step * 0.27
        half_tip = tooth_step * 0.15
        for i in range(num_teeth):
            ac = i * tooth_step
            angs = (ac - half_base, ac - half_tip, ac + half_tip, ac + half_base)
            rads = (r_root - 0.15, r_tip, r_tip, r_root - 0.15)
            bot = [np.array([r * cos(a), r * sin(a), z0]) for a, r in zip(angs, rads)]
            top = [np.array([r * cos(a), r * sin(a), z1]) for a, r in zip(angs, rads)]
            for k in range(4):
                kn = (k + 1) % 4
                self._add_flat_quad(bot[k], bot[kn], top[kn], top[k], mat)
            self._add_flat_quad(top[0], top[1], top[2], top[3], mat)
            self._add_flat_quad(bot[3], bot[2], bot[1], bot[0], mat)

    def optic_lens_disc(self, center, axis_fwd, up_hint, radius, dome_depth, mat, rings=6, segs=24):
        """Convex sapphire lens mapped strictly to centered [0,1]x[0,1] UVs of TurretOpticGlow."""
        ax, u, v = _ortho_frame(axis_fwd, up_hint)
        c = np.asarray(center, dtype=float)
        ring_pts, ring_norms, ring_uvs = [], [], []
        for rk in range(1, rings + 1):
            frac = rk / float(rings)
            rr = radius * frac
            dz = dome_depth * (1.0 - frac * frac)
            pts, nms, uvs = [], [], []
            for i in range(segs):
                a = i * tau / segs
                ca, sa = cos(a), sin(a)
                p = c + rr * (ca * u + sa * v) + dz * ax
                # Analytic spherical normal
                radial = ca * u + sa * v
                slope = (2.0 * dome_depth * frac) / max(radius, 1e-4)
                nm = ax + slope * radial
                nm /= max(float(np.linalg.norm(nm)), 1e-8)
                uv = (0.5 + 0.44 * frac * ca, 0.5 + 0.44 * frac * sa)
                pts.append(p)
                nms.append(nm)
                uvs.append(uv)
            ring_pts.append(pts)
            ring_norms.append(nms)
            ring_uvs.append(uvs)
        c_apex = c + dome_depth * ax
        for i in range(segs):
            j = (i + 1) % segs
            self.add_oriented_tri(
                c_apex, ring_pts[0][i], ring_pts[0][j],
                ax, ring_norms[0][i], ring_norms[0][j],
                (0.5, 0.5), ring_uvs[0][i], ring_uvs[0][j], mat
            )
        for rk in range(rings - 1):
            for i in range(segs):
                j = (i + 1) % segs
                self.add_oriented_tri(
                    ring_pts[rk][i], ring_pts[rk + 1][i], ring_pts[rk + 1][j],
                    ring_norms[rk][i], ring_norms[rk + 1][i], ring_norms[rk + 1][j],
                    ring_uvs[rk][i], ring_uvs[rk + 1][i], ring_uvs[rk + 1][j], mat
                )
                self.add_oriented_tri(
                    ring_pts[rk][i], ring_pts[rk + 1][j], ring_pts[rk][j],
                    ring_norms[rk][i], ring_norms[rk + 1][j], ring_norms[rk][j],
                    ring_uvs[rk][i], ring_uvs[rk + 1][j], ring_uvs[rk][j], mat
                )

    def recessed_brass_dial(self, center, normal, up_hint, radius, brass_mat=BRASS, iron_mat=IRON):
        """Circular antique-brass indicator gauge with forged-iron bezel ring & center boss."""
        ax, u, v = _ortho_frame(normal, up_hint)
        c = np.asarray(center, dtype=float)
        segs = 20
        # Outer dark iron bezel ring
        ring_pts = [(c + (radius + 0.9) * (cos(i * tau / segs) * u + sin(i * tau / segs) * v)) for i in range(segs)]
        self.swept_tube(ring_pts, 1.0, 8, iron_mat, closed=True)
        # Stepped brass dial face
        outer = [c + radius * (cos(i * tau / segs) * u + sin(i * tau / segs) * v) + ax * 0.4 for i in range(segs)]
        inner = [c + (radius * 0.68) * (cos(i * tau / segs) * u + sin(i * tau / segs) * v) + ax * 0.7 for i in range(segs)]
        t = TILES[brass_mat]
        for i in range(segs):
            j = (i + 1) % segs
            self.add_oriented_tri(
                c + ax * 0.85, inner[i], inner[j], ax, ax, ax,
                (0.5, 0.5), (inner[i][1] / t, inner[i][2] / t), (inner[j][1] / t, inner[j][2] / t), brass_mat
            )
            self._add_flat_quad(outer[i], outer[j], inner[j], inner[i], brass_mat)
        # Center pivot pin & needle bar
        self.domed_rivet(c + ax * 0.7, ax * 1.4, 1.1, iron_mat, sides=8)
        self.oriented_chamfer_beam(c + ax * 1.1, c + ax * 1.1 + (u * 0.5 + v * 0.85) * (radius * 0.72), 0.7, 0.5, iron_mat, bevel=0.15, up_hint=ax)


def build_base(m):
    """SM_SmartTurretBase: Z=0..76 cm octagonal basalt stone masonry pedestal, 8 forged straps, anchor feet."""
    # Stepped octagonal fortress basalt foundation plinth (Z = 0..14.5 cm, R = 67 -> 62.5)
    m.flat_octa_prism([(67.0, 0.0), (67.0, 10.5), (64.5, 13.5), (58.0, 14.5)], 8, STONE)

    # 4 courses of beveled ashlar basalt stone blocks (Z = 14.5..70.5)
    courses = (
        (14.5, 28.0, 58.0, 57.2),
        (28.0, 42.0, 56.6, 56.2),
        (42.0, 56.0, 56.0, 55.6),
        (56.0, 70.5, 55.4, 55.2),
    )
    for idx, (z0, z1, r0, r1) in enumerate(courses):
        m.flat_octa_prism(
            [(r0 - 1.1, z0), (r0, z0 + 1.0), (r1, z1 - 1.0), (r1 - 1.1, z1)],
            8, STONE,
        )
        # Staggered vertical stone block relief slabs on alternate octagon faces
        for f in range(8):
            a_face = f * tau / 8.0
            ca, sa = cos(a_face), sin(a_face)
            face_r = (r0 + r1) * 0.5 * cos(pi / 8.0) - 0.1
            sub_shift = 7.5 if (idx % 2 == 0) else -7.5
            for half_w, shift in ((14.5, -10.5 + sub_shift * 0.35), (14.5, 10.5 + sub_shift * 0.35)):
                tx, ty = -sa, ca
                cx = face_r * ca + shift * tx
                cy = face_r * sa + shift * ty
                m.add_oriented_plate(
                    (cx, cy, (z0 + z1) * 0.5),
                    (ca, sa, 0.0), (0.0, 0.0, 1.0),
                    half_w * 1.18, (z1 - z0) - 2.4, 2.2, STONE
                )

    # Top beveled stone cornice cap (Z = 70.5..74.8 cm) + dark forged-iron base collar (Z = 72..76.2 cm)
    m.flat_octa_prism([(54.0, 70.2), (58.2, 71.8), (58.2, 74.2), (54.5, 75.2)], 8, STONE)
    m.smooth_lathe([(42.0, 72.5), (53.5, 72.5), (54.2, 74.2), (53.5, 76.0), (36.0, 76.0)], 32, IRON, tile_u=52.0 * tau)

    # 8 Blackened Forged-Iron Corner Straps + Ground Anchor Feet + Rivets (matching concept B)
    for i in range(8):
        a = i * tau / 8.0 + pi / 8.0
        ca, sa = cos(a), sin(a)
        strap_pts = [
            (69.2 * ca, 69.2 * sa, 1.2),
            (66.2 * ca, 66.2 * sa, 9.5),
            (60.5 * ca, 60.5 * sa, 14.5),
            (57.2 * ca, 57.2 * sa, 29.0),
            (56.2 * ca, 56.2 * sa, 54.0),
            (58.4 * ca, 58.4 * sa, 71.5),
            (56.0 * ca, 56.0 * sa, 75.0),
            (50.0 * ca, 50.0 * sa, 75.2),
        ]
        # Flattened iron strap built via swept hexagonal bar + anchor foot pad
        m.swept_tube(strap_pts, [3.8, 3.3, 2.8, 2.55, 2.55, 2.75, 2.55, 2.2], 6, IRON, cap_ends=True)
        # Flared ground-anchor plinth shoe at Z = 0..5.5 cm
        m.oriented_chamfer_beam(
            (65.5 * ca, 65.5 * sa, 2.6), (70.8 * ca, 70.8 * sa, 2.2),
            9.2, 4.4, IRON, bevel=0.7
        )
        # Anchor bolt & 3 strap rivets
        m.domed_rivet((67.5 * ca, 67.5 * sa, 4.5), (0.0, 0.0, 2.6), 1.65, IRON, sides=6)
        for rz, rr in ((22.0, 58.8), (42.0, 57.8), (63.0, 57.8)):
            m.domed_rivet((rr * ca, rr * sa, rz), (1.9 * ca, 1.9 * sa, 0.0), 1.45, IRON, sides=6)

    m.collision(-68.0, 68.0, -68.0, 68.0, 0.0, 16.0)
    m.collision(-58.0, 58.0, -58.0, 58.0, 16.0, 76.0)


def build_yaw(m, z_off=0.0):
    """SM_SmartTurretYaw: 360° brass gear ring, iron deck, rear -X console & dual spring/piston yoke."""
    # 1. Antique Brass 48-Tooth Slewing Gear Ring (local Z = 0..14.5 -> world 76..90.5)
    m.smooth_lathe(
        [(36.0, z_off + 0.0), (49.5, z_off + 0.0), (49.5, z_off + 3.2), (45.2, z_off + 3.8)],
        40, BRASS, tile_u=49.0 * tau
    )
    m.toothed_gear_ring(z_off + 3.4, z_off + 10.6, 40.0, 45.2, 48.8, 48, BRASS)
    m.smooth_lathe(
        [(45.5, z_off + 10.4), (45.5, z_off + 12.2), (42.5, z_off + 14.5), (34.0, z_off + 14.5)],
        40, BRASS, tile_u=45.0 * tau
    )
    # Dark forged-iron bearing collar atop gear ring (Z_loc = 14.2..18.0)
    m.smooth_lathe(
        [(30.0, z_off + 14.2), (41.8, z_off + 14.2), (42.4, z_off + 16.5), (40.5, z_off + 18.2), (28.0, z_off + 18.2)],
        32, IRON, tile_u=42.0 * tau
    )

    # 2. Forged-Iron Turntable Deck Chassis (Z_loc = 18..27, low center well so mags drop freely!)
    # Lower structural bed plate (below gun mag bay)
    m.chamfered_box(-2.0, 0.0, z_off + 21.5, 52.0, 68.0, 7.2, IRON, bevel=1.4)
    # Left & Right raised saddle rails under yoke pivots (inset cleanly inside pivot hubs to prevent Z-clipping)
    for sy in (-1, 1):
        m.chamfered_box(-3.0, sy * 28.0, z_off + 25.6, 52.0, 10.6, 7.2, IRON, bevel=1.1)
        m.domed_rivet((19.0, sy * 33.4, z_off + 25.6), (0.0, sy * 1.4, 0.0), 1.35, BRASS, sides=6)
        m.domed_rivet((-21.0, sy * 33.4, z_off + 25.6), (0.0, sy * 1.4, 0.0), 1.35, BRASS, sides=6)

    # 3. Rear (-X) Forged-Iron Operator Control Console (Z_loc = 15..38 -> world 91..114, matches concept B!)
    # Heavy rear support bracket connecting turntable deck to console box
    m.chamfered_box(-32.0, 0.0, z_off + 21.5, 22.0, 26.0, 9.0, IRON, bevel=1.1)
    # Main angled lectern body
    m.chamfered_box(-41.5, 0.0, z_off + 27.5, 20.0, 34.0, 14.5, IRON, bevel=1.5)
    # Sloped rear top face facing operator (-X, +Z)
    console_n = np.array([-0.68, 0.0, 0.73])
    m.add_oriented_plate((-43.5, 0.0, z_off + 33.0), console_n, (0.0, 0.0, 1.0), 32.0, 16.5, 3.6, IRON, fit_uv=False)
    # Brass circular control dial on operator's left (-Y side of rear console)
    m.recessed_brass_dial((-46.0, -7.8, z_off + 34.6), console_n, (0.0, 0.0, 1.0), 5.6, BRASS, IRON)
    # Twin forged-steel control levers in slotted tracks on operator's right (+Y side)
    for ly, tilt_x in ((4.5, -5.5), (10.5, -2.5)):
        # Lever base slot housing
        m.add_oriented_plate((-44.2, ly, z_off + 34.0), console_n, (0.0, 0.0, 1.0), 4.2, 11.5, 2.2, GUNMETAL, fit_uv=False)
        # Stalk + turned brass knob handle
        p_base = (-43.5, ly, z_off + 34.5)
        p_top = (-44.5 + tilt_x, ly, z_off + 47.0)
        m.oriented_chamfer_beam(p_base, p_top, 1.35, 1.35, CHROME, bevel=0.3)
        m.smooth_spindle(
            (-44.5 + tilt_x * 0.9, ly, z_off + 45.2),
            (-44.8 + tilt_x * 1.06, ly, z_off + 50.2),
            [(0.0, 1.2), (0.35, 2.05), (0.75, 2.1), (1.0, 0.8)],
            BRASS, sides=10,
        )

    # 4. Twin Bold Angled Elevation Yoke Arms (pivot center at world Z=145 -> z_off + 69.0 cm!)
    for sy in (-1, 1):
        yc = sy * 31.2
        # Lower front pivot drum at (X = +14.5, Z_loc = 27.5)
        m.rotated_cylinder_y(yc - 5.0, yc + 5.0, 14.5, z_off + 27.5, 9.2, 20, IRON)
        m.rotated_cylinder_y(yc - 5.9, yc + 5.9, 14.5, z_off + 27.5, 5.2, 16, BRASS)
        m.domed_rivet((14.5, yc + sy * 5.9, z_off + 27.5), (0.0, sy * 1.5, 0.0), 2.1, IRON, sides=8)

        # Twin side cheek flanges shifted slightly -X so the exposed helical spring stands proud in front (+X)!
        for dy_plate in (-4.1, 4.1):
            yp = yc + dy_plate
            m.oriented_chamfer_beam((11.5, yp, z_off + 27.5), (-7.2, yp, z_off + 76.5), 2.1, 8.2, GUNMETAL, bevel=0.45)
        # Rear backing web forming deep spring trough
        m.oriented_chamfer_beam((7.8, yc, z_off + 26.5), (-9.8, yc, z_off + 72.5), 7.4, 3.2, GUNMETAL, bevel=0.55)

        # Proudly Exposed 8-Turn Honed-Chrome Helical Spring over Dark Gunmetal Core (crisp coil silhouette!)
        sp0 = np.array([18.4, yc, z_off + 33.8])
        sp1 = np.array([4.4, yc, z_off + 66.4])
        m.swept_tube([sp0, sp1], 0.95, 10, GUNMETAL, cap_ends=False)
        # Antique brass spring cups anchoring into yoke arm
        m.swept_tube([sp0 - (sp1 - sp0) * 0.05, sp0 + (sp1 - sp0) * 0.08], 3.9, 14, BRASS, cap_ends=True)
        m.swept_tube([sp1 - (sp1 - sp0) * 0.08, sp1 + (sp1 - sp0) * 0.05], 3.9, 14, BRASS, cap_ends=True)
        m.helical_spring(
            sp0 + (sp1 - sp0) * 0.09,
            sp1 - (sp1 - sp0) * 0.09,
            coil_r=3.55, wire_r=0.72, turns=8.0, mat=CHROME, segs_per_turn=14, wire_sides=8
        )

        # Rear (-X) Hydraulic Elevation Strut (Cylinder Barrel + Chrome Piston Rod)
        h_base = np.array([-21.5, yc, z_off + 25.5])
        h_top = np.array([-4.5, yc, z_off + 64.5])
        h_mid = h_base + (h_top - h_base) * 0.56
        m.rotated_cylinder_y(yc - 3.0, yc + 3.0, h_base[0], h_base[2], 3.6, 12, IRON)
        m.swept_tube([h_base, h_mid], 2.55, 12, GUNMETAL, cap_ends=True)
        m.swept_tube([h_mid, h_mid + (h_top - h_base) * 0.05], 2.95, 12, BRASS, cap_ends=True)
        m.swept_tube([h_mid, h_top], 1.45, 10, CHROME, cap_ends=True)

        # Upper Pitch Trunnion Bearing Housing centered strictly at (0, +/-30.8, z_off + 69.0)
        m.rotated_cylinder_y(yc - 5.2, yc + 5.2, 0.0, z_off + 69.0, 9.4, 24, IRON)
        m.rotated_cylinder_y(yc - 5.8, yc + 5.8, 0.0, z_off + 69.0, 6.2, 20, BRASS)
        m.domed_rivet((0.0, yc + sy * 5.8, z_off + 69.0), (0.0, sy * 1.6, 0.0), 2.5, GUNMETAL, sides=8)
        # Upper rounded mechanical knuckle cap
        m.rotated_cylinder_y(yc - 4.4, yc + 4.4, -5.5, z_off + 77.0, 6.0, 16, GUNMETAL)

    m.collision(-48.0, 48.0, -48.0, 48.0, 0.0, 26.0)
    m.collision(-54.0, -24.0, -20.0, 20.0, 14.0, 42.0)
    m.collision(-24.0, 22.0, -37.0, -24.0, 24.0, 82.0)
    m.collision(-24.0, 22.0, 24.0, 37.0, 24.0, 82.0)


def build_cradle(m, z_off=0.0):
    """SM_SmartTurretCradle: pitch-pivoting U-clamp carriage, open magwell, chrome rails & -Y sapphire pod."""
    # 1. Coaxial Trunnion Axle Shafts engaging Yaw hubs (Y = +/-20..36 cm, Z = z_off)
    for sy in (-1, 1):
        m.rotated_cylinder_y(sy * 19.0, sy * 36.6, 0.0, z_off, 4.1, 18, CHROME)
        # Inner cradle-to-trunnion forged mounting flange
        m.chamfered_box(0.0, sy * 21.8, z_off - 3.8, 22.0, 5.4, 14.5, GUNMETAL, bevel=0.8)

    # 2. Twin Lower Longitudinal Cheek Beams (Y = +/-17.2 cm, Z = z_off - 7.8)
    for sy in (-1, 1):
        m.chamfered_box(-1.5, sy * 17.2, z_off - 7.8, 59.0, 5.2, 9.2, GUNMETAL, bevel=0.85)
        # Precision Honed-Chrome Recoil Guide Rails (spanning front-to-rear at Y = +/-13.4, Z = z_off - 4.2)
        m.rotated_cylinder_x(-27.0, 25.0, sy * 13.4, z_off - 4.2, 1.15, 1.15, 12, CHROME)

    # 3. Front Open-Top Universal U-Clamp Fork (X = +20..+28.5 -> totally clear on top & center magwell!)
    # Lower structural under-bridge
    m.chamfered_box(24.0, 0.0, z_off - 11.2, 10.5, 39.0, 5.6, GUNMETAL, bevel=0.9)
    for sy in (-1, 1):
        # Swept shoulder brackets & tall U-fork upright cheeks (18.4 cm clear inner width: Y = +/-9.2)
        m.chamfered_box(24.0, sy * 12.2, z_off - 1.5, 10.5, 5.6, 17.5, GUNMETAL, bevel=0.9)
        m.chamfered_box(24.0, sy * 12.2, z_off + 7.2, 9.2, 5.0, 4.5, IRON, bevel=0.7)
        # Brass hinge/retention bolts on front fork
        m.domed_rivet((24.0, sy * 15.0, z_off - 5.5), (0.0, sy * 1.4, 0.0), 1.35, BRASS, sides=6)

    # 4. Rear Stabilizer U-Bridge (X = -31.5..-22.5 -> 5.2 cm recoil clearance from slide at -17.25)
    m.chamfered_box(-27.0, 0.0, z_off - 10.6, 9.0, 38.0, 5.2, GUNMETAL, bevel=0.8)
    for sy in (-1, 1):
        m.chamfered_box(-27.0, sy * 10.8, z_off - 3.5, 9.0, 5.0, 11.5, GUNMETAL, bevel=0.8)
        m.domed_rivet((-27.0, sy * 13.3, z_off - 5.5), (0.0, sy * 1.4, 0.0), 1.25, BRASS, sides=6)

    # 5. Side-Mounted (-Y, camera-facing flank!) Hooded Brass Rune-Optic Targeting Pod (pitches with cradle!)
    # Coaxial cantilevered mounting arm extending outside Left Yaw yoke arm (Y = -36.5 -> -44.8)
    m.chamfered_box(0.0, -40.2, z_off + 0.5, 11.0, 9.5, 8.2, IRON, bevel=0.8)
    m.rotated_cylinder_y(-45.0, -35.0, 0.0, z_off + 0.5, 3.6, 14, BRASS)

    # Main Armored Brass Sensor Cylinder (Y = -45.2, Z = z_off + 1.5, X = -12.5..+14.5)
    pod_y = -45.2
    pod_z = z_off + 1.5
    # Tapered octo/round brass pod shell
    m.rotated_cylinder_x(-12.5, 13.5, pod_y, pod_z, 6.4, 7.6, 16, BRASS, cap_start=True, cap_end=False)
    # Forged-iron armored clamping waist belt + overhanging protective top visor hood
    m.rotated_cylinder_x(-3.5, 4.5, pod_y, pod_z, 8.1, 8.1, 16, IRON, cap_start=True, cap_end=True)
    m.chamfered_box(13.8, pod_y, pod_z + 6.4, 7.8, 12.6, 3.2, BRASS, bevel=0.6)
    # Front gunmetal lens bezel collar
    m.rotated_cylinder_x(12.8, 15.2, pod_y, pod_z, 7.3, 6.8, 20, GUNMETAL, cap_start=False, cap_end=True)
    # Primary Convex Cyan Sapphire Lens (+X facing targets!)
    m.optic_lens_disc((15.0, pod_y, pod_z), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), 5.6, 1.45, OPTIC, rings=6, segs=24)

    # Lower Secondary Rangefinder / Illuminator Lens slung beneath main pod
    sub_z = pod_z - 8.2
    m.rotated_cylinder_x(-5.5, 12.5, pod_y, sub_z, 3.2, 3.6, 16, BRASS, cap_start=True, cap_end=False)
    m.rotated_cylinder_x(11.8, 13.4, pod_y, sub_z, 3.5, 3.3, 16, GUNMETAL, cap_start=False, cap_end=True)
    m.optic_lens_disc((13.3, pod_y, sub_z), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), 2.65, 0.75, OPTIC, rings=5, segs=18)

    # Rear (-X) Brass Pod End-Cap with subtle rune crest embossing (matching concept B right!)
    m.add_oriented_plate((-12.8, pod_y, pod_z), (-1.0, 0.0, 0.0), (0.0, 0.0, 1.0), 7.8, 7.8, 1.2, IRON)
    m.domed_rivet((-13.4, pod_y, pod_z), (-1.2, 0.0, 0.0), 1.4, BRASS, sides=6)


def build_slide(m, z_off=0.0):
    """SM_SmartTurretSlide: recoiling cold-steel vise sled with open underside magwell & brass thumbwheels."""
    # 4 Precision Linear Bearing Pillow Blocks sliding along cradle guide rails (Y = +/-13.4, Z = z_off - 4.2)
    for sy in (-1, 1):
        for bx in (-14.5, 15.5):
            m.chamfered_box(bx, sy * 13.4, z_off - 4.2, 6.2, 4.4, 4.4, IRON, bevel=0.55)
        # Side recoiling sled rails (Y = +/-9.6, X = -17..+19, leaving central Y = -8..+8 completely empty below Z=-4.2!)
        m.chamfered_box(1.0, sy * 9.8, z_off - 4.2, 36.5, 3.6, 5.2, GUNMETAL, bevel=0.6)

        # Front & Rear Universal Gun Clamping Vise Jaws (inner face at Y = +/-4.0 cm -> hugs rifle receivers/handguards cleanly)
        for jx, jlen, jh in ((13.5, 9.0, 7.8), (-12.5, 9.5, 7.2)):
            # Jaw clamp body
            m.chamfered_box(jx, sy * 6.8, z_off - 0.5, jlen, 4.8, jh, GUNMETAL, bevel=0.6)
            # Soft dark iron contact pad face
            m.chamfered_box(jx, sy * 4.35, z_off - 0.4, jlen - 1.2, 1.3, jh - 1.4, IRON, bevel=0.25)
            # Threaded chrome clamp screw + Knurled Antique-Brass Quick-Release Thumbwheel outside cheek rail
            m.rotated_cylinder_y(sy * 8.0, sy * 16.5, jx, z_off - 0.5, 0.75, 10, CHROME)
            tw0, tw1 = (sy * 14.8, sy * 17.2) if sy > 0 else (sy * 17.2, sy * 14.8)
            m.rotated_cylinder_y(tw0, tw1, jx, z_off - 0.5, 2.35, 14, BRASS)


def build_preview(m):
    """SM_SmartTurretPreview: full assembled turret (Base + Yaw@Z=76 + Cradle@Z=145 + Slide@Z=145)."""
    build_base(m)
    build_yaw(m, z_off=76.0)
    build_cradle(m, z_off=145.0)
    build_slide(m, z_off=145.0)
    m.boxes.clear()
    m.collision(-68.0, 68.0, -68.0, 68.0, 0.0, 18.0)
    m.collision(-58.0, 58.0, -58.0, 58.0, 18.0, 76.0)
    m.collision(-54.0, 48.0, -48.0, 48.0, 76.0, 122.0)
    m.collision(-32.0, 32.0, -52.0, 38.0, 122.0, 166.0)


if __name__ == "__main__":
    source_mesh.OUT = HERE
    specs = (
        ("SM_SmartTurretBase", build_base),
        ("SM_SmartTurretYaw", build_yaw),
        ("SM_SmartTurretCradle", build_cradle),
        ("SM_SmartTurretSlide", build_slide),
        ("SM_SmartTurretPreview", build_preview),
    )
    for name, fn in specs:
        mesh = TurretShop(20261127)
        fn(mesh)
        all_v = []
        tris = 0
        for gname, g in mesh.groups.items():
            if g["triangles"]:
                verts = np.asarray(g["vertices"], dtype=float)
                norms = np.asarray(g["normals"], dtype=float)
                if not np.all(np.isfinite(verts)) or not np.all(np.isfinite(norms)):
                    raise SystemExit(f"Non-finite values in {name}/{gname}")
                all_v.append(verts)
                tris += len(g["triangles"])
        stacked = np.vstack(all_v)
        lo, hi = stacked.min(axis=0), stacked.max(axis=0)
        print(
            f"PART {name}: {tris} tris | "
            f"X=[{lo[0]:.1f},{hi[0]:.1f}] Y=[{lo[1]:.1f},{hi[1]:.1f}] Z=[{lo[2]:.1f},{hi[2]:.1f}]"
        )
        for gname, g in mesh.groups.items():
            if g["triangles"]:
                print(f"  - {gname}: {len(g['triangles'])} tris")
        mesh.save(name)
