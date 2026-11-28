"""Original village defence game props. Centimetres, +X forward. Paired carry grips run along X."""
from pathlib import Path
import sys
from math import atan2, cos, sin, tau
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "GarrisonWorkshop"))
from author_workshop import Shop, TILES
import source_mesh

CAST_IRON = "OilCastIron"
AGED_BRASS = "OilAgedBrass"
CHARRED_OAK = "OilCharredOak"
EMBERS = "OilHearthEmbers"
FOOTING = "Footing"

# Register new HotOil prop slots in Shop texture tiling table (cm per UV tile).
TILES.update({
    CAST_IRON: 48.0,
    AGED_BRASS: 24.0,
    CHARRED_OAK: 28.0,
    EMBERS: 34.0,
})


class OilShop(Shop):
    def smooth_triangle(self, a, b, c, na, nb, nc, ua, ub, uc, mat):
        g = self.groups[mat]
        start = len(g["vertices"])
        for p, n, uv in zip((a, b, c), (na, nb, nc), (ua, ub, uc)):
            g["vertices"].append(tuple(float(v) for v in p))
            g["normals"].append(tuple(float(v) for v in n))
            g["uv0"].append(tuple(float(v) for v in uv))
            g["uv1"].append((max(0.0, float(p[2])) / 170.0, 0.0))
        # Match wall_geometry.Mesh.triangle UE winding order.
        g["triangles"].append([start, start + 2, start + 1])

    def smooth_lathe(self, profile, n_seg, mat, tile_u=96.0, tile_v=48.0, center=(0.0, 0.0, 0.0), spout=None):
        """Revolve (radius, z) profile into outward-facing smooth-normal rings with cylindrical UVs.
        If profile goes outer-rim -> belly -> inner-wall -> floor, outward normals follow curve tangents cleanly.
        Optional spout=(angle_rad, half_width_rad, boost_fn(r, z)->dr) adds a molded pouring beak."""
        cx, cy, cz = center
        pts = np.asarray(profile, dtype=float)
        m_pts = len(pts)
        # Arc-length V parameter along the profile.
        arc = np.zeros(m_pts, dtype=float)
        for k in range(1, m_pts):
            arc[k] = arc[k - 1] + float(np.hypot(pts[k, 0] - pts[k - 1, 0], pts[k, 1] - pts[k - 1, 1]))

        # 2D profile tangent -> outward normal in (dr, dz) plane.
        t2d = np.zeros((m_pts, 2), dtype=float)
        for k in range(m_pts):
            k0 = max(0, k - 1)
            k1 = min(m_pts - 1, k + 1)
            d = pts[k1] - pts[k0]
            l = float(np.hypot(d[0], d[1]))
            t2d[k] = d / max(l, 1e-8)

        verts = np.zeros((m_pts, n_seg, 3), dtype=float)
        norms = np.zeros((m_pts, n_seg, 3), dtype=float)
        uvs = np.zeros((m_pts, n_seg, 2), dtype=float)

        for i in range(n_seg):
            ang = i * tau / n_seg
            ca, sa = cos(ang), sin(ang)
            radial = np.array([ca, sa, 0.0])
            spout_w = 0.0
            if spout is not None:
                s_ang, s_hw = spout[0], spout[1]
                da = abs((ang - s_ang + np.pi) % tau - np.pi)
                if da < s_hw:
                    u_s = 1.0 - da / s_hw
                    spout_w = u_s * u_s * (3.0 - 2.0 * u_s)
            for k in range(m_pts):
                r, z = float(pts[k, 0]), float(pts[k, 1])
                dr = 0.0
                dz = 0.0
                if spout_w > 0.0 and len(spout) > 2:
                    dr, dz = spout[2](r, z)
                    r += dr * spout_w
                    z += dz * spout_w
                verts[k, i] = [cx + r * ca, cy + r * sa, cz + z]
                # Outward normal for bottom->outer->lip->inner->floor CCW revolution: (tz, 0, -tr)
                nr = t2d[k, 1]
                nz = -t2d[k, 0]
                n_vec = np.array([nr * ca, nr * sa, nz], dtype=float)
                nl = float(np.linalg.norm(n_vec))
                norms[k, i] = n_vec / max(nl, 1e-8)
                uvs[k, i] = [ang / tau * (tile_u / TILES[mat]), arc[k] / TILES[mat]]

        for k in range(m_pts - 1):
            for i in range(n_seg):
                j = (i + 1) % n_seg
                p00, p01 = verts[k, i], verts[k, j]
                p10, p11 = verts[k + 1, i], verts[k + 1, j]
                n00, n01 = norms[k, i], norms[k, j]
                n10, n11 = norms[k + 1, i], norms[k + 1, j]
                u00, u01 = uvs[k, i], uvs[k, j]
                u10, u11 = uvs[k + 1, i], uvs[k + 1, j]
                # Skip microscopic/degenerate faces (< 0.01 cm^2) that trigger DynamicMesh welding mismatches.
                if np.linalg.norm(np.cross(p01 - p00, p11 - p00)) > 1e-3:
                    self.smooth_triangle(p00, p01, p11, n00, n01, n11, u00, u01, u11, mat)
                if np.linalg.norm(np.cross(p11 - p00, p10 - p00)) > 1e-3:
                    self.smooth_triangle(p00, p11, p10, n00, n11, n10, u00, u11, u10, mat)

    def smooth_spindle(self, start, end, profile, mat, sides=32):
        """Revolve a smooth lathe spindle with grain UV V running along the bar axis."""
        a, b = np.asarray(start, dtype=float), np.asarray(end, dtype=float)
        span = b - a
        length = float(np.linalg.norm(span))
        unit = span / max(length, 1e-8)
        ref = np.array([0.0, 0.0, 1.0]) if abs(unit[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
        u_ax = np.cross(ref, unit)
        u_ax /= max(np.linalg.norm(u_ax), 1e-8)
        v_ax = np.cross(unit, u_ax)

        pts = np.asarray(profile, dtype=float)  # (t, r)
        m_pts = len(pts)
        # Convert (r, t*length) for normal evaluation.
        rz = np.column_stack((pts[:, 1], pts[:, 0] * length))
        t2d = np.zeros((m_pts, 2), dtype=float)
        for k in range(m_pts):
            d = rz[min(m_pts - 1, k + 1)] - rz[max(0, k - 1)]
            t2d[k] = d / max(np.hypot(d[0], d[1]), 1e-8)

        verts = np.zeros((m_pts, sides, 3), dtype=float)
        norms = np.zeros((m_pts, sides, 3), dtype=float)
        uvs = np.zeros((m_pts, sides, 2), dtype=float)
        circ_r = float(np.max(pts[:, 1])) * tau

        for i in range(sides):
            ang = i * tau / sides
            rad_dir = cos(ang) * u_ax + sin(ang) * v_ax
            for k in range(m_pts):
                t, r = float(pts[k, 0]), float(pts[k, 1])
                verts[k, i] = a + span * t + r * rad_dir
                n_vec = t2d[k, 1] * rad_dir - t2d[k, 0] * unit
                norms[k, i] = n_vec / max(np.linalg.norm(n_vec), 1e-8)
                # Keep U circumferential and V along bar axis so wood grain flows along length!
                uvs[k, i] = [ang / tau * circ_r / TILES[mat], (t * length) / TILES[mat]]

        for k in range(m_pts - 1):
            for i in range(sides):
                j = (i + 1) % sides
                p00, p01 = verts[k, i], verts[k, j]
                p10, p11 = verts[k + 1, i], verts[k + 1, j]
                n00, n01 = norms[k, i], norms[k, j]
                n10, n11 = norms[k + 1, i], norms[k + 1, j]
                u00, u01 = uvs[k, i], uvs[k, j]
                u10, u11 = uvs[k + 1, i], uvs[k + 1, j]
                if np.linalg.norm(np.cross(p01 - p00, p11 - p00)) > 1e-3:
                    self.smooth_triangle(p00, p01, p11, n00, n01, n11, u00, u01, u11, mat)
                if np.linalg.norm(np.cross(p11 - p00, p10 - p00)) > 1e-3:
                    self.smooth_triangle(p00, p11, p10, n00, n11, n10, u00, u11, u10, mat)

    def domed_rivet(self, base, axis, r, mat=AGED_BRASS, sides=8):
        ax = np.asarray(axis, dtype=float)
        end = np.asarray(base, dtype=float) + ax
        profile = [
            (0.0, r * 1.15),
            (0.32, r * 0.94),
            (0.72, r * 0.62),
            (1.00, max(0.06, r * 0.20)),
        ]
        self.smooth_spindle(base, end, profile, mat, sides=sides)


def add_hoop(m, r, z, width_z, thick, segs=48, mat=CAST_IRON, collar_r_mult=1.0):
    half = width_z * 0.5
    cham = min(thick * 0.38, half * 0.28)
    prof = [
        (r - 0.05 * collar_r_mult, z - half),
        (r + thick - cham, z - half),
        (r + thick, z - half + cham),
        (r + thick, z + half - cham),
        (r + thick - cham, z + half),
        (r - 0.05 * collar_r_mult, z + half),
    ]
    m.smooth_lathe(prof, segs, mat, tile_u=r * tau)


def vessel(m, r, z, hand=False):
    # Keep both props < 8000 tris so import_kit uses crisp non-Nanite authored normals (no 1% fallback faceting).
    segs = 48
    # High-detail thick cast-iron bowl profile:
    # center underside boss -> recessed forged diffuser base -> curved lower belly ->
    # straighter shoulder -> rolled thick rim lip -> crisp inner rim -> curved interior cavity -> floor
    pole_r = 0.02 * r
    profile = [
        (pole_r, 0.015 * r),
        (0.11 * r, 0.015 * r),
        (0.13 * r, 0.0),
        (0.26 * r, 0.0),
        (0.29 * r, 0.028 * r),
        (0.39 * r, 0.032 * r),
        (0.54 * r, 0.105 * r),
        (0.69 * r, 0.215 * r),
        (0.82 * r, 0.355 * r),
        (0.91 * r, 0.515 * r),
        (0.97 * r, 0.690 * r),
        (0.998 * r, 0.850 * r),
        (1.032 * r, 0.888 * r),
        (1.036 * r, 0.935 * r),
        (1.005 * r, 0.972 * r),
        (0.942 * r, 0.972 * r),
        (0.922 * r, 0.935 * r),
        (0.918 * r, 0.835 * r),
        (0.896 * r, 0.700 * r),
        (0.805 * r, 0.465 * r),
        (0.625 * r, 0.255 * r),
        (0.365 * r, 0.132 * r),
        (0.145 * r, 0.116 * r),
        (pole_r, 0.114 * r),
    ]

    # On the carried hand pot, flare a distinct pouring beak centered at VillageOilMotion::Lip (11.58, -7.74).
    spout = None
    if hand:
        lip_ang = atan2(-7.74, 11.58)

        def spout_fn(pr, pz):
            if pz < 0.76 * r or pr < 0.82 * r:
                return 0.0, 0.0
            u_z = min(1.0, max(0.0, (pz - 0.76 * r) / (0.212 * r)))
            return (0.16 * r * u_z, 0.032 * r * u_z)

        spout = (lip_ang, 0.34, spout_fn)

    scaled_profile = [(pr, z + pz) for pr, pz in profile]
    m.smooth_lathe(scaled_profile, segs, CAST_IRON, tile_u=r * tau, spout=spout)

    # Twin forged reinforcing belly hoops with smooth beveled edges.
    add_hoop(m, 0.978 * r, z + 0.675 * r, 0.036 * r, 0.018 * r, segs=segs, mat=CAST_IRON)
    add_hoop(m, 0.996 * r, z + 0.782 * r, 0.034 * r, 0.018 * r, segs=segs, mat=CAST_IRON)

    # Underside forged heat-ring (brass trim on hand pot for crisp 1P pour silhouette).
    add_hoop(m, 0.38 * r if hand else 0.25 * r, z + 0.012 * r, 0.030 * r, 0.020 * r, segs=32, mat=AGED_BRASS if hand else CAST_IRON)

    # Domed burnished brass rivets seated along the upper iron band.
    rivet_n = 12 if hand else 16
    for i in range(rivet_n):
        a = tau * (i + 0.5) / rivet_n
        # Leave space right on handle escutcheons (-Y and +Y).
        if abs(abs(sin(a)) - 1.0) < 0.04:
            continue
        m.domed_rivet(
            (r * 1.008 * cos(a), r * 1.008 * sin(a), z + r * 0.782),
            (r * 0.028 * cos(a), r * 0.028 * sin(a), 0.0),
            r * 0.024,
            AGED_BRASS,
            sides=8 if hand else 6,
        )

    # Twin side handles: riveted wall mount plates, forged tapered bracket arms,
    # burnished brass end ferrules, and smooth turned charred-oak grips.
    for s in (-1, 1):
        y = s * r
        # Forged wall escutcheon saddle strap spanning both handle roots.
        m.member((-0.56 * r, s * 0.94 * r, z + 0.735 * r), (0.56 * r, s * 0.94 * r, z + 0.735 * r),
                 0.065 * r, 0.145 * r, CAST_IRON)
        for rx in (-0.49 * r, 0.0, 0.49 * r):
            m.domed_rivet((rx, s * 0.96 * r, z + 0.735 * r), (0.0, s * 0.038 * r, 0.0),
                          0.022 * r, AGED_BRASS, sides=6)

        # Tapered forged gooseneck handle brackets (preserves exact handle end x = +-0.48*r, y = +-1.35*r, z + 0.9*r).
        for sx in (-1, 1):
            bx = sx * 0.45 * r
            gx = sx * 0.48 * r
            m.member((bx, s * 0.89 * r, z + 0.715 * r), (gx, s * 1.35 * r, z + 0.90 * r),
                     0.115 * r, 0.088 * r, CAST_IRON)
            # Brass collar ferrule & domed end pommel framing the oak spindle.
            m.smooth_spindle(
                (sx * 0.43 * r, s * 1.35 * r, z + 0.90 * r),
                (sx * 0.52 * r, s * 1.35 * r, z + 0.90 * r),
                [(0.0, 0.082 * r), (0.35, 0.098 * r if not hand else 2.52),
                 (0.75, 0.088 * r if not hand else 2.30), (1.0, 0.045 * r)],
                AGED_BRASS,
                sides=16 if hand else 12,
            )

        grip = 0.079 * r
        # Preserve exact hand-grip barrel radius (3.065 cm) & endpoints (-0.48*r .. +0.48*r, +-18.9, 5.6) for VR/1P/3P contact!
        grip_profile = (
            [(0.0, 2.25), (0.06, 2.58), (0.14, 2.94), (0.21, 3.065),
             (0.50, 3.065), (0.79, 3.065), (0.86, 2.94), (0.94, 2.58), (1.0, 2.25)]
            if hand
            else [(0.0, grip * 0.88), (0.12, grip * 1.08), (0.18, grip),
                  (0.82, grip), (0.88, grip * 1.08), (1.0, grip * 0.88)]
        )
        m.smooth_spindle(
            (-r * 0.48, s * r * 1.35, z + 0.9 * r),
            (r * 0.48, s * r * 1.35, z + 0.9 * r),
            grip_profile,
            CHARRED_OAK,
            sides=32 if hand else 14,
        )


def hearth_embers(m):
    """Sculpted glowing coal mound & crossed charred logs inside the stone brazier."""
    coal_profile = [
        (0.5, 18.8),
        (9.0, 18.4),
        (19.0, 17.1),
        (30.0, 14.9),
        (40.0, 12.2),
        (47.0, 10.2),
        (48.5, 9.5),
    ]
    m.smooth_lathe(coal_profile, 24, EMBERS, center=(0.0, 0.0, 0.0), tile_u=95.0)
    # Crossed charred firewood billets resting in the coals.
    logs = [
        ((-28.0, -14.0, 15.5), (27.0, 12.0, 19.2)),
        ((-24.0, 16.0, 16.8), (26.0, -15.0, 15.0)),
        ((-10.0, -29.0, 14.6), (14.0, 28.0, 17.5)),
    ]
    for a, b in logs:
        m.smooth_spindle(a, b, [(0.0, 2.4), (0.12, 3.8), (0.50, 4.1), (0.88, 3.7), (1.0, 2.2)], EMBERS, sides=8)


def station(m):
    """Staggered stone siege brazier with arched grate, glowing coals, cradle legs, and riveted cast-iron cauldron."""
    m.coping(-79, 79, -77, 77, 0, 10, FOOTING)
    for row in range(3):
        for i in range(14):
            a = (i + (row % 2) * 0.5) * tau / 14
            if cos(a) > 0.74 and row < 2:
                continue
            a0, a1 = a - 0.209, a + 0.209

            def course(z, shrink):
                return [(rr * cos(t), rr * sin(t), z)
                        for rr, t in ((69 - shrink, a0), (69 - shrink, a1), (48 + shrink, a1), (48 + shrink, a0))]

            h = 10 + row * 10
            m.solid([course(h, 0.7), course(h + 1, 0), course(h + 9, 0), course(h + 10, 0.8)], FOOTING)

    # Heavy forged firebox grate frame & arched lintel at the front (+X) mouth.
    for y in range(-32, 33, 8):
        m.member((36, y, 16), (62, y, 36), 3.4, 3.0, CAST_IRON)
    m.member((56, -34, 35), (56, 34, 35), 4.5, 4.0, CAST_IRON)
    for gy in (-24, 0, 24):
        m.domed_rivet((58.5, gy, 35), (1.5, 0.0, 0.0), 1.6, AGED_BRASS, sides=8)

    hearth_embers(m)

    # Four stout wrought-iron cradle legs anchored into stone coping with riveted pads.
    for a in np.arange(4) * tau / 4 + tau / 8:
        ca, sa = cos(a), sin(a)
        m.member((60 * ca, 60 * sa, 35), (43 * ca, 43 * sa, 62), 9.2, 10.2, CAST_IRON)
        m.member((61 * ca, 61 * sa, 12), (60 * ca, 60 * sa, 36), 11.0, 6.5, CAST_IRON)
        m.domed_rivet((64.5 * ca, 64.5 * sa, 35), (1.8 * ca, 1.8 * sa, 0.0), 2.1, AGED_BRASS, sides=8)

    vessel(m, 63, 35)
    m.collision(-61, 61, -60, 60, 9, 96)
    m.collision(-79, 79, -77, 77, 0, 10)


def fluid(m):
    n = 64
    for i in range(n):
        a, b = i * tau / n, (i + 1) * tau / n
        pts = ((0, 0, 0), (cos(a) * 50, sin(a) * 50, 0), (cos(b) * 50, sin(b) * 50, 0))
        m.triangle(*pts, "Bronze")
        m.groups["Bronze"]["uv0"][-3:] = [(0.5 + x / 100, 0.5 + y / 100) for x, y, _ in pts]


if __name__ == "__main__":
    source_mesh.OUT = HERE
    for name, build in (("SM_OilHearth", station), ("SM_OilHandPot", lambda m: vessel(m, 14, -7, True)), ("SM_OilSurface", fluid)):
        if "--hand-pot-only" in sys.argv and name != "SM_OilHandPot":
            continue
        mesh = OilShop(9153)
        build(mesh)
        mesh.save(name)
