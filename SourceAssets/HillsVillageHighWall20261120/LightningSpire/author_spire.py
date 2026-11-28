"""Author SM_LightningSpire modular meshes in centimetres (+X aim forward, -X operator rear, Z=0 roof base)."""
from pathlib import Path
import sys
from math import cos, pi, sin, tau
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "GarrisonWorkshop"))
sys.path.insert(0, str(HERE.parent / "HotOil"))
from author_workshop import TILES
from author_oil import OilShop
import source_mesh

STONE = "SpireStone"
IRON = "SpireCastIron"
COPPER = "SpireCopperBrass"
INSULATOR = "SpireInsulator"
RUNE = "SpireRuneGlow"
CRYSTAL = "SpireCrystal"

TILES.update({
    STONE: 110.0,
    IRON: 56.0,
    COPPER: 36.0,
    INSULATOR: 30.0,
    RUNE: 42.0,
    CRYSTAL: 46.0,
})


def _rot_matrix(rx=0.0, ry=0.0, rz=0.0):
    cx, sx = cos(rx), sin(rx)
    cy, sy = cos(ry), sin(ry)
    cz, sz = cos(rz), sin(rz)
    mx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]], dtype=float)
    my = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]], dtype=float)
    mz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]], dtype=float)
    return mz @ my @ mx


class SpireShop(OilShop):
    def add_oriented_tri(self, a, b, c, na, nb, nc, ua, ub, uc, mat):
        pa, pb, pc = np.asarray(a, float), np.asarray(b, float), np.asarray(c, float)
        e1, e2 = pb - pa, pc - pa
        cr = np.cross(e1, e2)
        if np.linalg.norm(cr) <= 1e-3:
            return
        nav = (np.asarray(na, float) + np.asarray(nb, float) + np.asarray(nc, float))
        if np.dot(cr, nav) < 0.0:
            self.smooth_triangle(pa, pc, pb, na, nc, nb, ua, uc, ub, mat)
        else:
            self.smooth_triangle(pa, pb, pc, na, nb, nc, ua, ub, uc, mat)

    def _add_flat_quad(self, p00, p01, p11, p10, mat, tile=None):
        t = TILES[mat] if tile is None else tile
        pts = [np.asarray(p, float) for p in (p00, p01, p11, p10)]
        n = np.cross(pts[1] - pts[0], pts[2] - pts[0])
        nl = float(np.linalg.norm(n))
        if nl <= 1e-4:
            return
        n /= nl
        ax = int(np.argmax(np.abs(n)))
        ia, ib = ((1, 2), (0, 2), (0, 1))[ax]
        uvs = [(p[ia] / t, -p[ib] / t) for p in pts]
        self.smooth_triangle(pts[0], pts[1], pts[2], n, n, n, uvs[0], uvs[1], uvs[2], mat)
        self.smooth_triangle(pts[0], pts[2], pts[3], n, n, n, uvs[0], uvs[2], uvs[3], mat)

    def flat_octa_prism(self, levels, sides, mat, rot_offset=pi / 8.0, twist=0.0):
        """Crisp faceted octagonal stone/hub column with beveled steps and end caps."""
        n_lv = len(levels)
        rings = np.zeros((n_lv, sides, 3), dtype=float)
        for k, (r, z) in enumerate(levels):
            ang_off = rot_offset + twist * (k / max(1, n_lv - 1))
            for i in range(sides):
                ang = i * tau / sides + ang_off
                rings[k, i] = [r * cos(ang), r * sin(ang), z]
        for k in range(n_lv - 1):
            for i in range(sides):
                j = (i + 1) % sides
                self._add_flat_quad(rings[k, i], rings[k, j], rings[k + 1, j], rings[k + 1, i], mat)
        # End caps if bottom/top radius > 1.0
        if levels[0][0] > 1.0:
            c0 = np.array([0.0, 0.0, levels[0][1]])
            n0 = np.array([0.0, 0.0, -1.0])
            t = TILES[mat]
            for i in range(sides):
                j = (i + 1) % sides
                self.add_oriented_tri(c0, rings[0, j], rings[0, i], n0, n0, n0,
                                      (0.0, 0.0), (rings[0, j][0] / t, rings[0, j][1] / t), (rings[0, i][0] / t, rings[0, i][1] / t), mat)
        if levels[-1][0] > 1.0:
            c1 = np.array([0.0, 0.0, levels[-1][1]])
            n1 = np.array([0.0, 0.0, 1.0])
            t = TILES[mat]
            for i in range(sides):
                j = (i + 1) % sides
                self.add_oriented_tri(c1, rings[-1, i], rings[-1, j], n1, n1, n1,
                                      (0.0, 0.0), (rings[-1, i][0] / t, rings[-1, i][1] / t), (rings[-1, j][0] / t, rings[-1, j][1] / t), mat)

    def swept_tube(self, centers, radii, sides, mat, closed=False, cap_ends=True):
        """Smooth swept circular/polygonal rib or tilted gyro ring with outward normals."""
        pts = np.asarray(centers, dtype=float)
        n_pts = len(pts)
        rads = np.broadcast_to(np.asarray(radii, dtype=float), (n_pts,))
        tangents = np.zeros((n_pts, 3), dtype=float)
        for k in range(n_pts):
            if closed:
                d = pts[(k + 1) % n_pts] - pts[(k - 1) % n_pts]
            else:
                k0 = max(0, k - 1)
                k1 = min(n_pts - 1, k + 1)
                d = pts[k1] - pts[k0]
            tangents[k] = d / max(np.linalg.norm(d), 1e-8)

        # Parallel-transport frame along curve
        t0 = tangents[0]
        ref = np.array([0.0, 0.0, 1.0]) if abs(t0[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
        u_ax = np.cross(ref, t0)
        u_ax /= max(np.linalg.norm(u_ax), 1e-8)
        v_ax = np.cross(t0, u_ax)

        ring_verts = np.zeros((n_pts, sides, 3), dtype=float)
        ring_norms = np.zeros((n_pts, sides, 3), dtype=float)
        ring_uvs = np.zeros((n_pts, sides, 2), dtype=float)
        arc = np.zeros(n_pts, dtype=float)
        for k in range(1, n_pts):
            arc[k] = arc[k - 1] + float(np.linalg.norm(pts[k] - pts[k - 1]))
        max_r = float(np.max(rads)) * tau

        for k in range(n_pts):
            if k > 0:
                tk = tangents[k]
                u_ax = u_ax - np.dot(u_ax, tk) * tk
                ul = float(np.linalg.norm(u_ax))
                if ul > 1e-6:
                    u_ax /= ul
                else:
                    ref = np.array([0.0, 0.0, 1.0]) if abs(tk[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
                    u_ax = np.cross(ref, tk)
                    u_ax /= max(np.linalg.norm(u_ax), 1e-8)
                v_ax = np.cross(tk, u_ax)
            for i in range(sides):
                ang = i * tau / sides
                radial = cos(ang) * u_ax + sin(ang) * v_ax
                ring_verts[k, i] = pts[k] + rads[k] * radial
                ring_norms[k, i] = radial / max(np.linalg.norm(radial), 1e-8)
                ring_uvs[k, i] = [ang / tau * (max_r / TILES[mat]), arc[k] / TILES[mat]]

        seg_end = n_pts if closed else n_pts - 1
        for k in range(seg_end):
            kn = (k + 1) % n_pts
            for i in range(sides):
                j = (i + 1) % sides
                self.add_oriented_tri(
                    ring_verts[k, i], ring_verts[k, j], ring_verts[kn, j],
                    ring_norms[k, i], ring_norms[k, j], ring_norms[kn, j],
                    ring_uvs[k, i], ring_uvs[k, j], ring_uvs[kn, j], mat,
                )
                self.add_oriented_tri(
                    ring_verts[k, i], ring_verts[kn, j], ring_verts[kn, i],
                    ring_norms[k, i], ring_norms[kn, j], ring_norms[kn, i],
                    ring_uvs[k, i], ring_uvs[kn, j], ring_uvs[kn, i], mat,
                )

        if not closed and cap_ends:
            for k_idx, sgn in ((0, -1.0), (n_pts - 1, 1.0)):
                if rads[k_idx] <= 0.3:
                    continue
                nc = tangents[k_idx] * sgn
                pc = pts[k_idx]
                for i in range(sides):
                    j = (i + 1) % sides
                    self.add_oriented_tri(pc, ring_verts[k_idx, i], ring_verts[k_idx, j], nc, nc, nc,
                                          (0.5, 0.5), (0.0, 0.5), (0.5, 0.0), mat)

    def add_oriented_plate(self, center, normal, up_hint, width, height, thick, mat, fit_uv=False):
        """Place a cleanly UV'd recessed/framed plate centered at `center` facing `normal`."""
        n = np.asarray(normal, float)
        n /= max(np.linalg.norm(n), 1e-8)
        u = np.cross(np.asarray(up_hint, float), n)
        u /= max(np.linalg.norm(u), 1e-8)
        v = np.cross(n, u)
        hw, hh, ht = width * 0.5, height * 0.5, thick * 0.5
        c = np.asarray(center, float)
        front = [c + n * ht - u * hw - v * hh, c + n * ht + u * hw - v * hh,
                 c + n * ht + u * hw + v * hh, c + n * ht - u * hw + v * hh]
        back = [p - n * thick for p in front]
        if fit_uv:
            if fit_uv == "tile_plate":
                tw, th = width / 20.0, height / 20.0
                uv_f = [(0.0, 0.0), (tw, 0.0), (tw, th), (0.0, th)]
            else:
                uv_f = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
            self.add_oriented_tri(front[0], front[1], front[2], n, n, n, uv_f[0], uv_f[1], uv_f[2], mat)
            self.add_oriented_tri(front[0], front[2], front[3], n, n, n, uv_f[0], uv_f[2], uv_f[3], mat)
        else:
            self._add_flat_quad(front[0], front[1], front[2], front[3], mat)
        self._add_flat_quad(back[1], back[0], back[3], back[2], mat)
        for i in range(4):
            j = (i + 1) % 4
            self._add_flat_quad(back[i], back[j], front[j], front[i], mat)


def build_base(m):
    """SM_LightningSpireBase: Z=0..118 cm octagonal pedestal, rune drum, slewing collar & -X operator lectern."""
    # Stepped octagonal fortress stone plinth (r=82 -> 64 cm)
    m.flat_octa_prism([(82, 0), (82, 16), (76, 20), (74, 34), (66, 40)], 8, STONE)
    # 8 heavy corner stone anchor piers + brass anchor bolts
    for i in range(8):
        a = i * tau / 8.0 + pi / 8.0
        ca, sa = cos(a), sin(a)
        m.member((68 * ca, 68 * sa, 4), (66 * ca, 66 * sa, 38), 14, 14, STONE)
        m.domed_rivet((75 * ca, 75 * sa, 18), (0.0, 0.0, 3.2), 2.4, COPPER, sides=6)

    # Lower cast-iron grounding collar around drum waist
    m.smooth_lathe([(63, 39), (66, 41), (66, 47), (60, 49)], 24, IRON, tile_u=64 * tau)

    # Tapered octagonal rune drum (Z = 44..102)
    m.flat_octa_prism([(58, 44), (56, 50), (50, 96), (54, 102)], 8, STONE)

    # 4 glowing rune tablets on cardinal faces (+-X, +-Y) framed in forged iron
    for ang in (0.0, pi * 0.5, pi, pi * 1.5):
        n = np.array([cos(ang), sin(ang), 0.10])
        c = np.array([50.5 * cos(ang), 50.5 * sin(ang), 73.0])
        m.add_oriented_plate(c, n, (0, 0, 1), 24.0, 36.0, 3.2, IRON, fit_uv=False)
        m.add_oriented_plate(c + n * 1.3, n, (0, 0, 1), 19.0, 30.0, 1.4, RUNE, fit_uv=True)

    # 4 heavy diagonal wrought-iron buttress fins (+-45 deg)
    for ang in (pi * 0.25, pi * 0.75, pi * 1.25, pi * 1.75):
        ca, sa = cos(ang), sin(ang)
        pts = [(70 * ca, 70 * sa, 36), (62 * ca, 62 * sa, 58), (55 * ca, 55 * sa, 84), (53 * ca, 53 * sa, 104)]
        m.swept_tube(pts, [6.2, 5.4, 4.4, 3.8], 6, IRON, cap_ends=True)
        m.domed_rivet((67 * ca, 67 * sa, 46), (2.2 * ca, 2.2 * sa, 0.0), 1.9, COPPER, sides=6)
        m.domed_rivet((57 * ca, 57 * sa, 94), (2.0 * ca, 2.0 * sa, 0.0), 1.7, COPPER, sides=6)

    # Slewing turntable collar at Z = 102..118
    m.smooth_lathe([(42, 102), (56, 102), (57, 106), (57, 113), (52, 118), (38, 118)], 32, IRON, tile_u=56 * tau)
    m.smooth_lathe([(55.5, 107), (58.2, 108.5), (58.2, 111.5), (55.5, 113)], 32, COPPER, tile_u=58 * tau)
    for i in range(16):
        a = i * tau / 16.0
        m.domed_rivet((57.8 * cos(a), 57.8 * sin(a), 110.0), (2.2 * cos(a), 2.2 * sin(a), 0.0), 1.6, COPPER, sides=6)

    # Rear (-X) Operator Aiming Lectern & Ergonomic Hand Grips
    m.member((-54, 0, 56), (-74, 0, 88), 12, 12, IRON)
    m.member((-74, 0, 88), (-78, 0, 116), 10, 10, IRON)
    m.member((-68, -22, 112), (-68, 22, 112), 7, 7, IRON)
    # Tilted rune sight console facing -X toward operator
    sight_n = np.array([-0.82, 0.0, 0.57])
    m.add_oriented_plate((-78, 0, 118), sight_n, (0, 0, 1), 30.0, 20.0, 3.8, IRON, fit_uv=False)
    m.add_oriented_plate((-79.5, 0, 119.2), sight_n, (0, 0, 1), 24.0, 15.0, 1.5, RUNE, fit_uv=True)
    # Twin side operator handles (-X rear) with copper-brass ferrules
    for s in (-1, 1):
        m.member((-74, s * 13, 114), (-84, s * 22, 114), 4.5, 4.5, IRON)
        m.smooth_spindle((-84, s * 22, 106), (-84, s * 22, 122),
                         [(0.0, 2.0), (0.16, 2.8), (0.50, 2.95), (0.84, 2.8), (1.0, 2.0)], COPPER, sides=10)

    m.collision(-82, 82, -82, 82, 0, 42)
    m.collision(-58, 58, -58, 58, 42, 118)
    m.collision(-92, -56, -28, 28, 70, 126)


def add_torus_coil(m, z_center, major_r, minor_r, tube_mat=COPPER, pin_count=12):
    segs = 40
    ring = [(major_r * cos(i * tau / segs), major_r * sin(i * tau / segs), z_center) for i in range(segs)]
    m.swept_tube(ring, minor_r, 14, tube_mat, closed=True)
    if pin_count > 0:
        for i in range(pin_count):
            a = i * tau / pin_count
            m.domed_rivet(
                ((major_r + minor_r * 0.85) * cos(a), (major_r + minor_r * 0.85) * sin(a), z_center),
                (2.2 * cos(a), 2.2 * sin(a), 0.0),
                1.6,
                COPPER,
                sides=6,
            )


def build_mast(m, z_off=0.0):
    """SM_LightningSpireMast: rotating turret coils, pylon ribs, twin +X discharge horns, finial rod."""
    # Turret base hub (local Z = 0..24)
    m.flat_octa_prism([(50, z_off + 0), (50, z_off + 12), (44, z_off + 24)], 8, IRON, rot_offset=0.0)

    # Central stone arcane conduit core + 4 vertical rune energy channels
    m.flat_octa_prism([(22, z_off + 18), (19, z_off + 144)], 8, STONE)
    for ang in (0.0, pi * 0.5, pi, pi * 1.5):
        c = np.array([19.5 * cos(ang), 19.5 * sin(ang), z_off + 80.0])
        m.add_oriented_plate(c, (cos(ang), sin(ang), 0.0), (0, 0, 1), 8.0, 108.0, 2.0, RUNE, fit_uv="tile_plate")

    # 4 tapered sweeping iron pylon ribs (local Z = 16..152)
    for ang in (pi * 0.25, pi * 0.75, pi * 1.25, pi * 1.75):
        ca, sa = cos(ang), sin(ang)
        rib = [
            (41 * ca, 41 * sa, z_off + 16),
            (38 * ca, 38 * sa, z_off + 62),
            (32 * ca, 32 * sa, z_off + 106),
            (25 * ca, 25 * sa, z_off + 144),
        ]
        m.swept_tube(rib, [5.0, 4.4, 3.8, 3.4], 6, IRON, cap_ends=True)

    # Triple stepped Copper-Brass Induction Coils + Dark Glazed Ceramic Insulator Discs
    coil_specs = [
        (46.0, 41.0, 5.4, 16),
        (82.0, 35.0, 4.8, 12),
        (118.0, 29.0, 4.3, 12),
    ]
    for zc, mr, mnr, pins in coil_specs:
        # Glazed porcelain insulator collars flanking each coil
        m.smooth_lathe(
            [(20, z_off + zc - 9.0), (mr - 5.5, z_off + zc - 7.5), (mr - 5.5, z_off + zc - 5.0),
             (22, z_off + zc - 4.0)],
            24, INSULATOR, tile_u=mr * tau,
        )
        m.smooth_lathe(
            [(22, z_off + zc + 4.0), (mr - 5.5, z_off + zc + 5.0), (mr - 5.5, z_off + zc + 7.5),
             (20, z_off + zc + 9.0)],
            24, INSULATOR, tile_u=mr * tau,
        )
        add_torus_coil(m, z_off + zc, mr, mnr, COPPER, pin_count=pins)

    # Upper Focusing Chamber Frame (local Z = 136..204, enclosing Crystal center at Z=166)
    m.smooth_lathe([(18, z_off + 136), (29, z_off + 139), (29, z_off + 146), (22, z_off + 149)], 24, IRON, tile_u=28 * tau)
    add_torus_coil(m, z_off + 198.0, 23.0, 2.8, COPPER, pin_count=8)
    for ang in (pi * 0.25, pi * 0.75, pi * 1.25, pi * 1.75):
        ca, sa = cos(ang), sin(ang)
        arch = [
            (27 * ca, 27 * sa, z_off + 142),
            (31 * ca, 31 * sa, z_off + 166),
            (26 * ca, 26 * sa, z_off + 190),
            (16 * ca, 16 * sa, z_off + 206),
        ]
        m.swept_tube(arch, [3.0, 2.6, 2.4, 2.2], 6, IRON, cap_ends=True)

    # Crowning Finial Lightning Rod & Brass Corona Orb (local Z = 200..252 -> world 370 cm)
    m.smooth_lathe(
        [(16.0, z_off + 198), (2.6, z_off + 204), (2.2, z_off + 229), (5.6, z_off + 233),
         (5.6, z_off + 239), (2.2, z_off + 244), (0.8, z_off + 252)],
        16, IRON, tile_u=24.0,
    )
    add_torus_coil(m, z_off + 216.0, 8.5, 1.8, INSULATOR, pin_count=0)
    add_torus_coil(m, z_off + 226.0, 7.2, 1.6, COPPER, pin_count=0)
    # 4 radial collector prongs + brass apex finial sphere
    for ang in (0.0, pi * 0.5, pi, pi * 1.5):
        ca, sa = cos(ang), sin(ang)
        m.swept_tube([(3 * ca, 3 * sa, z_off + 225), (11 * ca, 11 * sa, z_off + 231), (14 * ca, 14 * sa, z_off + 239)],
                     [1.4, 1.1, 0.7], 6, COPPER, cap_ends=True)
    m.smooth_spindle(
        (0, 0, z_off + 231), (0, 0, z_off + 245),
        [(0.0, 2.6), (0.25, 6.2), (0.55, 6.8), (0.85, 5.2), (1.0, 1.8)], COPPER, sides=12,
    )


def build_crystal(m, z_off=0.0):
    """SM_LightningSpireCrystal: double-terminated faceted sapphire crystal + brass rune cuffs."""
    m.flat_octa_prism(
        [(0.5, z_off - 28), (10.5, z_off - 17), (13.5, z_off - 4), (13.5, z_off + 4),
         (10.5, z_off + 17), (0.5, z_off + 28)],
        6, CRYSTAL, rot_offset=0.0,
    )
    for cz in (-11.5, 11.5):
        m.smooth_lathe(
            [(11.2, z_off + cz - 2.6), (14.4, z_off + cz - 1.8), (14.4, z_off + cz + 1.8), (11.2, z_off + cz + 2.6)],
            12, COPPER, tile_u=36.0,
        )


def build_rings(m, z_off=0.0):
    """SM_LightningSpireRings: twin inclined copper-brass gyro-inductor rings with glowing rune nodes."""
    segs = 32
    for r, tilt, n_nodes in ((35.0, (0.48, 0.22, 0.0), 4), (27.5, (-0.58, 0.35, 0.52), 4)):
        rot = _rot_matrix(*tilt)
        pts = []
        for i in range(segs):
            a = i * tau / segs
            p = rot @ np.array([r * cos(a), r * sin(a), 0.0]) + np.array([0.0, 0.0, z_off])
            pts.append(p)
        m.swept_tube(pts, 2.25, 8, COPPER, closed=True)
        for j in range(n_nodes):
            a = j * tau / n_nodes + 0.35
            n_dir = rot @ np.array([cos(a), sin(a), 0.0])
            c_node = rot @ np.array([(r + 1.5) * cos(a), (r + 1.5) * sin(a), 0.0]) + np.array([0.0, 0.0, z_off])
            m.add_oriented_plate(c_node, n_dir, (0, 0, 1), 5.2, 5.2, 2.2, RUNE, fit_uv=True)


def build_preview(m):
    """SM_LightningSpirePreview: complete assembled tower (Z = 0..370 cm)."""
    build_base(m)
    build_mast(m, z_off=118.0)
    build_crystal(m, z_off=284.0)
    build_rings(m, z_off=284.0)
    m.collision(-82, 82, -82, 82, 0, 42)
    m.collision(-58, 58, -58, 58, 42, 300)
    m.collision(-92, -56, -28, 28, 70, 126)


if __name__ == "__main__":
    source_mesh.OUT = HERE
    specs = (
        ("SM_LightningSpireBase", build_base),
        ("SM_LightningSpireMast", build_mast),
        ("SM_LightningSpireCrystal", build_crystal),
        ("SM_LightningSpireRings", build_rings),
        ("SM_LightningSpirePreview", build_preview),
    )
    for name, fn in specs:
        mesh = SpireShop(84107)
        fn(mesh)
        tris = sum(len(g["triangles"]) for g in mesh.groups.values())
        print(f"PART {name}: {tris} tris")
        for gname, g in mesh.groups.items():
            if g["triangles"]:
                verts = np.asarray(g["vertices"], dtype=float)
                norms = np.asarray(g["normals"], dtype=float)
                if not np.all(np.isfinite(verts)) or not np.all(np.isfinite(norms)):
                    raise SystemExit(f"Non-finite values in {name}/{gname}")
                print(f"  - {gname}: {len(g['triangles'])} tris")
        mesh.save(name)
