"""AAA builders for Jump Rail, 4-Wheel Hay Wagon (zero-clip 3-strand braided ropes!) & Yard Lamp Post (UE cm)."""
import math
from mathutils import Vector

from props_geom import AssetBuilder, sample_beziers


def build_jump_rail(out_dir):
    """Playable equestrian schooling jump hurdle (384 x 96 x 136 cm) with iron drop-pin chains & hoof-scuff weathering."""
    b = AssetBuilder('SM_Stable_JumpRail', seed=4423, ground_mud_cm=38.0)

    for sx in (-1, 1):
        px = sx * 152.0
        b.plank(f'BaseSkidLong_{sx}', (px, 0.0, 4.5), (13.5, 96.0, 9.0), mat='DarkWood', wear=0.08)
        b.plank(f'BaseSkidWing_{sx}', (px + sx * 16.0, 0.0, 4.5), (46.0, 13.0, 9.0), mat='DarkWood', wear=0.06)
        # Forged iron skid-end bumper caps & anchor straps
        for sy in (-1, 1):
            b.block(f'FootStrap_{sx}_{sy}', (px, sy * 9.5, 10.2), (11.6, 5.2, 2.2), mat='ScaleIron', bevel_cm=0.16)
            b.bolt((px, sy * 11.2, 11.4), axis='Z', radius_cm=0.62, mat='Iron')
            b.block(f'SkidEndCap_{sx}_{sy}', (px, sy * 47.0, 4.5), (14.4, 2.6, 9.4), mat='ScaleIron', bevel_cm=0.18)

        b.plank(f'MainPost_{sx}', (px, 0.0, 66.0), (11.2, 11.2, 120.0), mat='Oak', wear=0.09)
        b.block(f'PostNeck_{sx}', (px, 0.0, 127.0), (13.0, 13.0, 2.6), mat='DarkWood', bevel_cm=0.35)
        b.lathe(f'PostFinial_{sx}', (px, 0.0, 128.3),
                [(0.0, 6.2), (2.2, 5.4), (5.8, 2.2), (7.6, 0.0)], mat='OiledOak', axis='Z', sides=4, rot_deg=(0, 0, 45))
        b.block(f'PostTopBand_{sx}', (px, 0.0, 122.0), (12.2, 12.2, 2.8), mat='ScaleIron', bevel_cm=0.16)

        for sy in (-1, 1):
            b.beam(f'SkidBrace_{sx}_{sy}', (px, sy * 38.0, 8.0), (px, sy * 4.5, 56.0), 7.4, 7.4, mat='Oak')
            b.peg((px + sx * 4.8, sy * 5.2, 52.0), axis='X')

        wx = px + sx * 35.0
        b.plank(f'WingOuterPost_{sx}', (wx, 0.0, 52.0), (8.6, 8.6, 94.0), mat='Oak', wear=0.07)
        b.block(f'WingCap_{sx}', (wx, 0.0, 100.0), (10.2, 10.2, 2.4), mat='DarkWood', bevel_cm=0.3)
        for z_rail in (30.0, 58.0, 86.0):
            b.plank(f'WingRail_{sx}_{z_rail}', (px + sx * 17.5, 0.0, z_rail), (34.0, 4.4, 7.2), mat='OiledOak', wear=0.06)
            b.peg((wx, 4.5, z_rail), axis='Y')
        b.beam(f'WingDiag_{sx}', (px + sx * 4.0, 0.0, 14.0), (wx - sx * 3.0, 0.0, 86.0), 4.6, 5.4, mat='Sawn')

        b.block(f'PinTrack_{sx}', (px - sx * 5.9, 0.0, 68.0), (1.1, 4.4, 88.0), mat='ScaleIron', bevel_cm=0.14)
        for hole_z in range(36, 114, 10):
            b.bolt((px - sx * 6.5, 0.0, float(hole_z)), axis='X', radius_cm=0.58, height_cm=0.35, mat='Iron')

        for cup_z in (60.0, 98.0):
            cx = px - sx * 9.8
            b.block(f'CupPlate_{sx}_{cup_z}', (px - sx * 6.6, 0.0, cup_z), (1.4, 6.2, 9.6), mat='ScaleIron', bevel_cm=0.15)
            cup_pts = [(cx, 5.2 * math.cos(math.radians(-165.0 + k * 15.0)),
                        cup_z + 5.2 * math.sin(math.radians(-165.0 + k * 15.0))) for k in range(11)]
            b.strap(f'JumpCup_{sx}_{cup_z}', cup_pts, 6.4, 0.9, mat='ScaleIron', up_hint=(1, 0, 0))
            b.bolt((px, 5.9, cup_z), axis='Y', radius_cm=0.72, height_cm=1.6, mat='Iron')
            # Small hanging iron keeper chain below each cup pin
            for ci in range(3):
                b.ring_torus(f'PinChain_{sx}_{cup_z}_{ci}', (px, 6.8, cup_z - 2.0 - ci * 2.1),
                             1.15, 0.28, mat='Iron', axis='Y' if ci % 2 == 0 else 'X', major_segs=10)

    # Dual Turned High-Contrast Banded Jump Rails (Z = 60 cm & Z = 98 cm)
    for r_idx, rail_z in enumerate((60.0, 98.0)):
        n_bands = 8
        band_len = 296.0 / n_bands
        for bi in range(n_bands):
            x0 = -148.0 + bi * band_len
            x1 = x0 + band_len
            is_lime = (bi + r_idx) % 2 == 1
            mat = 'Lime' if is_lime else 'OiledOak'
            rad = 4.65 if is_lime else 4.55
            prof = [(x0, rad - 0.25), (x0 + 0.6, rad), (x1 - 0.6, rad), (x1, rad - 0.25)]
            b.lathe(f'JumpBar_{r_idx}_{bi}', (0.0, 0.0, rail_z), prof, mat=mat, axis='X', sides=20,
                    cap_mat='Endgrain' if (bi in (0, n_bands - 1)) else mat)
        for sx in (-1, 1):
            b.lathe(f'PoleFerrule_{r_idx}_{sx}', (sx * 146.0, 0.0, rail_z),
                    [(-1.8, 4.78), (-1.4, 4.92), (1.4, 4.92), (1.8, 4.78)], mat='ScaleIron', axis='X', sides=20)

    # Ground Takeoff Cavaletti Pole in strapped oak chocks
    b.lathe('GroundPole', (0.0, -18.0, 10.5),
            [(-144.0, 4.2), (-142.0, 5.2), (142.0, 5.2), (144.0, 4.2)], mat='DarkWood', axis='X', sides=16)
    for sx in (-112.0, 112.0):
        b.block(f'PoleChock_{sx}', (sx, -18.0, 3.8), (11.0, 18.0, 7.6), mat='Oak', bevel_cm=0.32)
        b.block(f'ChockBand_{sx}', (sx, -18.0, 7.2), (3.2, 18.4, 1.2), mat='ScaleIron', bevel_cm=0.12)

    b.add_collider((-166.0, 0.0, 68.0), (54.0, 96.0, 136.0))
    b.add_collider((166.0, 0.0, 68.0), (54.0, 96.0, 136.0))
    b.add_collider((0.0, 0.0, 51.0), (296.0, 16.0, 102.0))
    return b.finish(out_dir)


def _add_spoked_wheel(b, name, center_cm, outer_r, rim_w, n_spokes=12, rot_z_deg=0.0):
    """True dished European wooden cart wheel with exact ground touch at Z = center.z - outer_r."""
    b.push_xform(center_cm, (0.0, 0.0, rot_z_deg))
    tire_th = 1.65
    felloe_th = 6.8
    inner_felloe_r = outer_r - tire_th - felloe_th
    outer_felloe_r = outer_r - tire_th

    hw = rim_w * 0.5 + 8.5
    hub_prof = [
        (-hw, 5.4), (-hw + 1.2, 6.2), (-hw + 4.8, 7.4),
        (-6.2, 9.6), (-3.0, 10.4), (3.0, 10.4), (6.2, 9.6),
        (hw - 4.8, 7.4), (hw - 1.2, 6.2), (hw, 5.4),
    ]
    b.lathe(name + '_Hub', (0, 0, 0), hub_prof, mat='DarkWood', axis='Y', sides=22)
    for hy, hr in ((-hw + 2.2, 6.8), (-6.8, 9.8), (6.8, 9.8), (hw - 2.2, 6.8)):
        b.lathe(f'{name}_HubBand_{hy:.1f}', (0, hy, 0),
                [(-1.25, hr - 0.15), (-1.0, hr + 0.35), (1.0, hr + 0.35), (1.25, hr - 0.15)],
                mat='ScaleIron', axis='Y', sides=22)
    b.lathe(name + '_AxleCap', (0, hw + 2.4, 0), [(-2.4, 3.6), (1.6, 3.3), (2.4, 2.2), (2.8, 0.0)],
            mat='Iron', axis='Y', sides=14)
    b.block(name + '_Linchpin', (0, hw + 1.2, 0), (1.2, 1.3, 8.8), mat='Iron', bevel_cm=0.14)

    for k in range(n_spokes):
        ang = k * math.tau / n_spokes
        p_in = (9.0 * math.cos(ang), -0.6, 9.0 * math.sin(ang))
        p_out = ((inner_felloe_r + 1.4) * math.cos(ang), 1.6, (inner_felloe_r + 1.4) * math.sin(ang))
        b.beam(f'{name}_Spoke_{k}', p_in, p_out, 3.2, 4.2, mat='Sawn', wear=0.05, endgrain=False)

    segs = 36
    felloe_r = 0.5 * (inner_felloe_r + outer_felloe_r)
    felloe_pts = [(felloe_r * math.cos(i * math.tau / segs), 1.6, felloe_r * math.sin(i * math.tau / segs))
                  for i in range(segs)]
    fr, fw, c = felloe_th * 0.5, rim_w * 0.5, 0.55
    felloe_sec = [(-fr + c, -fw), (fr - c, -fw), (fr, -fw + c), (fr, fw - c),
                  (fr - c, fw), (-fr + c, fw), (-fr, fw - c), (-fr, -fw + c)]
    b.sweep_section(name + '_Felloe', felloe_pts, felloe_sec, mat='DarkWood', cyclic=True, up_hint=(0, 1, 0))

    tire_r = outer_felloe_r + tire_th * 0.5
    tire_pts = [(tire_r * math.cos(i * math.tau / segs), 1.6, tire_r * math.sin(i * math.tau / segs))
                for i in range(segs)]
    tr, tw, tc = tire_th * 0.5, (rim_w + 0.5) * 0.5, 0.25
    tire_sec = [(-tr + tc, -tw), (tr - tc, -tw), (tr, -tw + tc), (tr, tw - tc),
                (tr - tc, tw), (-tr + tc, tw), (-tr, tw - tc), (-tr, -tw + tc)]
    b.sweep_section(name + '_IronTire', tire_pts, tire_sec, mat='ScaleIron', cyclic=True, up_hint=(0, 1, 0))
    for k in range(6):
        ang = (k + 0.5) * math.tau / 6
        b.block(f'{name}_TireRivet_{k}', ((outer_r - 0.1) * math.cos(ang), 1.6, (outer_r - 0.1) * math.sin(ang)),
                (0.8, 1.3, 0.8), mat='Iron', bevel_cm=0.12)
    b.pop_xform()


def _add_hay_bale(b, name, center_cm, size_cm, rot_deg=(0, 0, 0), seed_off=0):
    """Chunky hand-tied farm hay bale with recessed twine grooves & 3-strand braided hemp baling twine."""
    b.push_xform(center_cm, rot_deg)
    lx, ly, lz = size_cm
    hx, hy, hz = lx * 0.5, ly * 0.5, lz * 0.5
    nx, ny = 24, 18
    verts, faces = [], []

    def sp(a, e):
        return math.copysign(abs(a) ** e, a)

    for j in range(1, ny):
        lat = -math.pi * 0.5 + j * math.pi / ny
        clat, slat = math.cos(lat), math.sin(lat)
        for i in range(nx):
            lon = i * math.tau / nx
            px = hx * sp(math.cos(lon), 0.34) * sp(clat, 0.38)
            py = hy * sp(math.sin(lon), 0.42) * sp(clat, 0.42)
            pz = hz * sp(slat, 0.44)
            pinch = sum(math.exp(-((px - tx) / 3.2) ** 2) for tx in (-lx * 0.25, lx * 0.25))
            pinch_k = 1.0 - 0.08 * pinch
            py *= pinch_k
            pz *= pinch_k
            # Organic pitched straw tufts & shoulder roughness
            n1 = math.sin(px * 0.18 + py * 0.15 + seed_off) * 1.45
            n2 = math.cos(py * 0.25 - pz * 0.21 + seed_off * 1.7) * 1.05
            verts.append((px + n1 * 0.38, py + n2 * 0.58, pz + (n1 + n2) * 0.48))

    for j in range(ny - 2):
        for i in range(nx):
            i2 = (i + 1) % nx
            faces.append((j * nx + i, j * nx + i2, (j + 1) * nx + i2, (j + 1) * nx + i))
    bot_i = len(verts)
    verts.append((0.0, 0.0, -hz * 0.96))
    top_i = len(verts)
    verts.append((0.0, 0.0, hz * 0.96))
    for i in range(nx):
        i2 = (i + 1) % nx
        faces.append((bot_i, i2, i))
        faces.append((top_i, (ny - 2) * nx + i, (ny - 2) * nx + i2))

    obj = b._new_mesh_obj(name + '_Straw', verts, faces, 'Hay')
    b._bake_smooth(obj, 68.0)
    b._uv_box(obj, long_axis=0)

    # Twin 3-strand braided baling-twine loops seated cleanly proud (+1.4 cm above compressed pinch groove) — ZERO burial!
    for ti, tx in enumerate((-lx * 0.25, lx * 0.25)):
        ring_pts = [(tx, (hy * 0.995 + 1.15) * sp(math.cos(k * math.tau / 28), 0.42),
                     (hz * 0.995 + 1.15) * sp(math.sin(k * math.tau / 28), 0.44))
                    for k in range(28)]
        b.rope_braid(f'{name}_Twine_{ti}', ring_pts, radius_cm=0.78, mat='Rope', cyclic=True, pitch_cm=4.8, sample_step_cm=2.2)
    b.pop_xform()


def _add_cleat_hitch_knot(b, name, x_cm, y_cleat, z_cleat, sy):
    """Cinched braided rope hitch wrap + knotted loose rope tail hanging cleanly off a forged tie-cleat."""
    # Cinched collar loop wrapping around cleat ring
    b.ring_torus(name + '_Wrap', (x_cm, y_cleat + sy * 1.4, z_cleat), 2.3, 0.95, mat='Rope', axis='Y', major_segs=14)
    # Short dangling knotted tail end
    tail = sample_beziers((x_cm, y_cleat + sy * 2.2, z_cleat - 0.8), [
        ((x_cm + 1.8, y_cleat + sy * 3.6, z_cleat - 6.5),
         (x_cm + 3.2, y_cleat + sy * 2.8, z_cleat - 12.5),
         (x_cm + 2.4, y_cleat + sy * 2.0, z_cleat - 17.5)),
    ], 6)
    b.rope_braid(name + '_Tail', tail, radius_cm=1.05, mat='Rope', pitch_cm=5.5, sample_step_cm=2.2)


def build_hay_wagon(out_dir):
    """Hero 4-wheel fodder wain (382 x 178 x 198 cm) with zero-clip external 3-strand braided hemp ropes & weathered detail."""
    b = AssetBuilder('SM_Stable_HayWagon', seed=4437, ground_mud_cm=52.0)

    rear_x, rear_r = -92.0, 56.0
    front_x, front_r = 76.0, 44.0
    track_half = 76.0
    steer_deg = 10.0

    # --- 1. Four True Dished Spoked Wheels ---
    _add_spoked_wheel(b, 'WheelRL', (rear_x, -track_half, rear_r), rear_r, rim_w=8.4, n_spokes=12, rot_z_deg=0.0)
    _add_spoked_wheel(b, 'WheelRR', (rear_x, track_half, rear_r), rear_r, rim_w=8.4, n_spokes=12, rot_z_deg=180.0)
    b.push_xform((front_x, 0.0, 0.0), (0.0, 0.0, steer_deg))
    _add_spoked_wheel(b, 'WheelFL', (0.0, -track_half, front_r), front_r, rim_w=7.6, n_spokes=10, rot_z_deg=0.0)
    _add_spoked_wheel(b, 'WheelFR', (0.0, track_half, front_r), front_r, rim_w=7.6, n_spokes=10, rot_z_deg=180.0)

    b.plank('FrontAxle', (0.0, 0.0, front_r), (12.5, track_half * 2.0 + 10.0, 12.0), mat='Oak', wear=0.10)
    b.plank('FrontBolster', (0.0, 0.0, front_r + 16.0), (14.0, 114.0, 13.0), mat='DarkWood', wear=0.08)
    b.lathe('FifthWheelRing', (0.0, 0.0, front_r + 23.0),
            [(0.0, 16.0), (1.8, 16.0), (1.8, 12.0), (0.0, 12.0)], mat='ScaleIron', axis='Z', sides=24)
    for sy in (-1, 1):
        b.block(f'FrontAxleStrap_{sy}', (0.0, sy * 48.0, front_r + 8.0), (14.5, 4.2, 26.0), mat='ScaleIron', bevel_cm=0.16)
        b.beam(f'FrontHound_{sy}', (-26.0, sy * 8.0, front_r + 5.0), (32.0, sy * 28.0, front_r + 3.0), 6.2, 7.2, mat='Oak')
        sh_pts = sample_beziers((18.0, sy * 34.0, front_r + 2.0), [
            ((55.0, sy * 36.0, front_r - 1.5), (95.0, sy * 35.0, front_r - 14.0), (132.0, sy * 32.0, 12.0)),
        ], 10)
        b.strap(f'DraughtShaft_{sy}', sh_pts, 6.4, 7.2, mat='DarkWood', up_hint=(0, 0, 1))
        b.block(f'ShaftTipIron_{sy}', (132.0, sy * 32.0, 12.0), (5.5, 7.4, 8.2), mat='ScaleIron', bevel_cm=0.18)
        b.ring_torus(f'ShaftTraceHook_{sy}', (125.0, sy * 36.5, 16.5), 2.0, 0.42, mat='Iron', axis='Z', major_segs=12)
    b.plank('SplinterBar', (32.0, 0.0, front_r + 3.0), (7.6, 86.0, 7.4), mat='OiledOak', wear=0.06)
    b.block('SingletreeBracket', (36.5, 0.0, front_r + 3.0), (4.8, 12.0, 5.2), mat='ScaleIron', bevel_cm=0.16)
    b.pop_xform()

    # --- 2. Rear Axle & Running Gear ---
    b.plank('RearAxle', (rear_x, 0.0, rear_r), (14.5, track_half * 2.0 + 12.0, 13.5), mat='Oak', wear=0.10)
    b.plank('RearBolster', (rear_x, 0.0, rear_r + 14.0), (14.5, 118.0, 12.0), mat='DarkWood', wear=0.07)
    for sy in (-1, 1):
        b.block(f'RearAxleStrap_{sy}', (rear_x, sy * 50.0, rear_r + 7.0), (16.5, 4.5, 25.0), mat='ScaleIron', bevel_cm=0.16)
        b.beam(f'RearHound_{sy}', (rear_x, sy * 34.0, rear_r + 4.0), (rear_x + 68.0, sy * 8.0, rear_r - 2.0), 6.4, 7.4, mat='Oak')
    b.beam('ReachPole', (rear_x - 10.0, 0.0, rear_r + 3.0), (front_x + 8.0, 0.0, front_r + 6.0), 9.5, 10.5, mat='DarkWood')

    # --- 3. Planked Wagon Bed, Flared Slatted Hay-Ladder Raves & Driver's Footboard ---
    deck_z = 76.0
    bed_x0, bed_x1 = -142.0, 118.0
    bed_cx = 0.5 * (bed_x0 + bed_x1)
    bed_len = bed_x1 - bed_x0

    for sy in (-1, 1):
        b.plank(f'ChassisSill_{sy}', (bed_cx, sy * 48.0, deck_z - 5.5), (bed_len + 6.0, 9.5, 10.0), mat='DarkWood', wear=0.09)
    for bx in (-132.0, -72.0, -12.0, 48.0, 108.0):
        b.plank(f'CrossBolster_{bx:.0f}', (bx, 0.0, deck_z - 3.0), (8.2, 118.0, 6.2), mat='Oak', wear=0.06)
    for pi in range(7):
        b.plank(f'DeckPlank_{pi}', (bed_cx, -46.5 + pi * 15.5, deck_z + 1.8), (bed_len, 14.4, 3.6), mat='Oak', wear=0.12)

    # Angled wooden driver footboard jutting cleanly at front (+X)
    b.plank('FrontFootboard', (bed_x1 + 14.0, 0.0, deck_z + 2.0), (24.0, 88.0, 3.8), mat='OiledOak', rot_deg=(0, 16, 0), wear=0.08)
    for sy in (-32.0, 32.0):
        b.beam(f'FootBracket_{sy:.0f}', (bed_x1, sy, deck_z - 5.0), (bed_x1 + 22.0, sy, deck_z - 1.5), 3.6, 3.6, mat='ScaleIron', endgrain=False)

    # Outer side boards, splayed standards, iron tie-cleats (positioned OUTSIDE sill at Y=+-60, Z=80!) & top raves
    std_xs = (-134.0, -86.0, -38.0, 10.0, 58.0, 106.0)
    for sy in (-1, 1):
        for zi, (zz, yy) in enumerate(((85.5, 55.8), (97.5, 58.6), (109.5, 61.4))):
            b.plank(f'BoxBoard_{sy}_{zi}', (bed_cx, sy * yy, zz), (bed_len, 3.2, 11.2),
                    mat='OiledOak' if zi == 2 else 'Oak', rot_deg=(sy * -13.0, 0.0, 0.0), wear=0.11)
        for si, sx in enumerate(std_xs):
            b.beam(f'RackStd_{sy}_{si}', (sx, sy * 53.5, deck_z + 1.0), (sx, sy * 72.5, 146.0), 5.2, 5.8, mat='OiledOak', wear=0.06)
            if si in (0, 2, 3, 5):
                b.beam(f'SideBrace_{sy}_{si}', (sx, sy * 56.5, deck_z - 2.0), (sx, sy * 72.5, 134.0),
                       3.8, 4.4, mat='ScaleIron' if si in (0, 5) else 'Oak', wear=0.04)
            # Forged tie-cleats mounted clearly OUTSIDE the lower wagon box on standard stations (-86, +10, +58)
            if si in (1, 3, 4):
                b.block(f'CleatPlate_{sy}_{si}', (sx, sy * 58.5, deck_z + 3.0), (6.4, 2.2, 7.5), mat='ScaleIron', bevel_cm=0.16)
                b.ring_torus(f'RopeCleat_{sy}_{si}', (sx, sy * 61.5, deck_z + 3.0), 2.4, 0.48, mat='ScaleIron', axis='X', major_segs=14)
        for rz, ry in ((126.0, 66.8), (144.0, 71.8)):
            b.plank(f'RaveRail_{sy}_{rz:.0f}', (bed_cx, sy * ry, rz), (bed_len + 14.0, 4.8, 6.2),
                    mat='Sawn', rot_deg=(sy * -13.0, 0.0, 0.0), wear=0.08)
        for ex in (bed_x0 + 2.0, bed_x1 - 2.0):
            b.block(f'CornerIron_{sy}_{ex:.0f}', (ex, sy * 62.0, 109.0), (6.4, 4.6, 3.8), mat='ScaleIron', bevel_cm=0.16)
            b.bolt((ex, sy * 64.6, 109.0), axis='Y', radius_cm=0.55, mat='Iron')

    for end_s, ex in ((-1, bed_x0 - 2.0), (1, bed_x1 + 2.0)):
        for zz in (86.0, 98.0, 110.0):
            b.plank(f'EndBoard_{end_s}_{zz:.0f}', (ex, 0.0, zz), (3.4, 114.0, 11.2), mat='Oak', wear=0.09)
        for ey in (-48.0, -16.0, 16.0, 48.0):
            b.beam(f'EndStile_{end_s}_{ey:.0f}', (ex, ey, deck_z + 2.0), (ex + end_s * 18.0, ey, 152.0), 4.8, 5.2, mat='OiledOak')
        for rz, dx in ((128.0, 10.5), (146.0, 16.2)):
            b.plank(f'EndRung_{end_s}_{rz:.0f}', (ex + end_s * dx, 0.0, rz), (4.6, 134.0, 5.8), mat='Sawn', wear=0.06)

    b.beam('BrakeBeam', (rear_x + 34.0, -68.0, rear_r + 12.0), (rear_x + 34.0, 68.0, rear_r + 12.0), 4.8, 4.8, mat='ScaleIron', endgrain=False)
    for sy in (-1, 1):
        b.block(f'BrakeShoe_{sy}', (rear_x + 42.0, sy * 74.0, rear_r + 8.0), (8.0, 9.5, 22.0), mat='DarkWood', bevel_cm=0.35)
    b.beam('BrakeCrankShaft', (bed_x0 - 4.0, 58.0, 96.0), (bed_x0 - 24.0, 58.0, 118.0), 2.4, 2.4, mat='ScaleIron', endgrain=False)

    # --- 4. 7 Staggered Hand-Tied Hay Bales (slightly tucked inward from raves so external ropes have 100% ZERO clip!) ---
    _add_hay_bale(b, 'BaleL0', (-96.0, -23.0, 102.0), (94.0, 53.0, 45.0), rot_deg=(0, 0, 2), seed_off=1.1)
    _add_hay_bale(b, 'BaleL1', (-94.0, 24.0, 102.0), (92.0, 53.0, 45.0), rot_deg=(0, 0, -2), seed_off=2.4)
    _add_hay_bale(b, 'BaleL2', (24.0, -24.0, 102.0), (114.0, 53.0, 45.0), rot_deg=(0, 0, -1), seed_off=3.7)
    _add_hay_bale(b, 'BaleL3', (28.0, 24.0, 102.0), (112.0, 53.0, 45.0), rot_deg=(0, 0, 2), seed_off=4.9)

    # Middle tier (outer Y reaches +-53 cm, top Z reaches ~166 cm — comfortably inside top rave Y=+-71.8!)
    _add_hay_bale(b, 'BaleM0', (-88.0, 1.0, 144.0), (104.0, 90.0, 44.0), rot_deg=(1.2, 0.8, 88), seed_off=6.2)
    _add_hay_bale(b, 'BaleM1', (-10.0, -2.0, 145.5), (106.0, 92.0, 45.0), rot_deg=(-1.0, -0.6, 92), seed_off=7.5)
    _add_hay_bale(b, 'BaleM2', (68.0, 0.5, 143.5), (104.0, 88.0, 44.0), rot_deg=(0.8, -1.2, 87), seed_off=8.8)

    # Top crown cap bale (Y spans +-30 cm, Z spans 162..192 cm)
    _add_hay_bale(b, 'BaleTop', (-14.0, 0.0, 176.5), (134.0, 59.0, 32.0), rot_deg=(0, 0.8, 2.5), seed_off=10.3)

    # --- 5. ZERO-CLIP External 3-Strand Twisted Braided Hemp Lashing Ropes + Cinched Cleat Knots! ---
    # Every transverse rope runs cleanly OUTSIDE BoxBoard (Y=61.4), OUTSIDE RaveRail_126 (Y=69.2),
    # OVER top of RaveRail_144 (Y=75.6, Z=148.5), then steps cleanly OVER the hay bales (+2 cm clearance)!
    for ri, rx_c in enumerate((-86.0, 58.0)):
        # BaleM top is Z ~ 166.5, side shoulder Y ~ +-52 -> route rope cleanly at Y=+-76.2 outside raves, Z=169.0 across top!
        pts = sample_beziers((rx_c, -62.0, deck_z + 3.2), [
            ((rx_c, -68.5, 102.0), (rx_c, -76.2, 128.0), (rx_c, -76.5, 147.8)),
            ((rx_c, -74.5, 155.0), (rx_c, -56.0, 168.0), (rx_c, -36.0, 169.0)),
            ((rx_c, -12.0, 169.8), (rx_c, 12.0, 169.8), (rx_c, 36.0, 169.0)),
            ((rx_c, 56.0, 168.0), (rx_c, 74.5, 155.0), (rx_c, 76.5, 147.8)),
            ((rx_c, 76.2, 128.0), (rx_c, 68.5, 102.0), (rx_c, 62.0, deck_z + 3.2)),
        ], 7)
        b.rope_braid(f'HayRope_{ri}', pts, radius_cm=1.45, mat='Rope', pitch_cm=7.2, sample_step_cm=2.2)
        _add_cleat_hitch_knot(b, f'CleatKnot_{ri}_L', rx_c, -61.5, deck_z + 3.0, -1)
        _add_cleat_hitch_knot(b, f'CleatKnot_{ri}_R', rx_c, 61.5, deck_z + 3.0, 1)

    # Center rope (X=+10) clears outside raves (Y=+-76.5), rises cleanly over BaleM1 shoulder & BaleTop crown (Z=195.2)!
    mid_pts = sample_beziers((10.0, -62.0, deck_z + 3.2), [
        ((10.0, -68.5, 102.0), (10.0, -76.2, 128.0), (10.0, -76.5, 147.8)),
        ((10.0, -74.5, 155.0), (10.0, -56.0, 169.5), (10.0, -42.0, 171.5)),
        ((10.0, -33.5, 174.0), (10.0, -32.2, 192.5), (10.0, -18.0, 194.8)),
        ((10.0, 0.0, 195.4), (10.0, 18.0, 194.8), (10.0, 32.2, 192.5)),
        ((10.0, 33.5, 174.0), (10.0, 42.0, 171.5), (10.0, 56.0, 169.5)),
        ((10.0, 74.5, 155.0), (10.0, 76.5, 147.8), (10.0, 76.2, 128.0)),
        ((10.0, 72.0, 108.0), (10.0, 67.0, 94.0), (10.0, 62.0, deck_z + 3.2)),
    ], 7)
    b.rope_braid('HayRope_Mid', mid_pts, radius_cm=1.45, mat='Rope', pitch_cm=7.2, sample_step_cm=2.2)
    _add_cleat_hitch_knot(b, 'CleatKnot_Mid_L', 10.0, -61.5, deck_z + 3.0, -1)
    _add_cleat_hitch_knot(b, 'CleatKnot_Mid_R', 10.0, 61.5, deck_z + 3.0, 1)

    # Longitudinal crown tie-rope clears OVER EndRung_146 (X=-160/+136, Z=150.5) & hugs BaleM0 -> BaleTop -> BaleM2 tightly!
    long_pts = sample_beziers((-160.5, 0.0, 149.8), [
        ((-150.0, 0.0, 155.5), (-124.0, 0.0, 166.5), (-92.0, 0.0, 168.0)),
        ((-82.0, 0.0, 170.5), (-81.0, 0.0, 191.5), (-58.0, 0.0, 194.2)),
        ((-14.0, 0.0, 195.2), (30.0, 0.0, 194.2), (53.0, 0.0, 191.5)),
        ((55.0, 0.0, 170.5), (68.0, 0.0, 168.0), (100.0, 0.0, 166.5)),
        ((118.0, 0.0, 158.0), (130.0, 0.0, 153.5), (136.5, 0.0, 149.8)),
    ], 7)
    b.rope_braid('HayRidgeRope', long_pts, radius_cm=1.42, mat='Rope', pitch_cm=7.2, sample_step_cm=2.2)
    for ex_k in (-160.2, 136.2):
        b.ring_torus(f'EndRungHitch_{ex_k:.0f}', (ex_k, 0.0, 146.5), 3.6, 1.1, mat='Rope', axis='Y', major_segs=14)

    b.add_collider((-12.0, 0.0, 96.0), (272.0, 174.0, 192.0))
    b.add_collider((158.0, 14.0, 26.0), (105.0, 78.0, 48.0), yaw_deg=steer_deg)
    return b.finish(out_dir)


def build_yard_lamp_post(out_dir):
    """Freestanding 292 cm stable yard oak & wrought-iron lamp post (retained as weathered library asset)."""
    b = AssetBuilder('SM_Stable_YardLampPost', seed=4449, ground_mud_cm=44.0)

    b.block('StoneBaseLower', (0.0, 0.0, 6.0), (42.0, 42.0, 20.0), mat='Stone', bevel_cm=1.4, segments=2)
    b.block('StoneBaseUpper', (0.0, 0.0, 23.0), (34.0, 34.0, 16.0), mat='Stone', bevel_cm=1.8, segments=2)
    b.lathe('StoneCapRing', (0.0, 0.0, 31.0),
            [(0.0, 22.0), (1.8, 21.0), (4.2, 16.2), (5.2, 14.5)], mat='Stone', axis='Z', sides=4, rot_deg=(0, 0, 45))

    b.block('ShaftFoot', (0.0, 0.0, 46.0), (18.5, 18.5, 24.0), mat='DarkWood', bevel_cm=0.55)
    b.plank('ShaftMain', (0.0, 0.0, 166.0), (16.8, 16.8, 222.0), mat='Oak', wear=0.10)
    b.block('PostNeckTrim', (0.0, 0.0, 276.5), (21.5, 21.5, 4.2), mat='DarkWood', bevel_cm=0.55)
    b.block('PostCapEave', (0.0, 0.0, 281.5), (25.5, 25.5, 5.2), mat='DarkWood', bevel_cm=0.65)
    b.lathe('PostCapPyramid', (0.0, 0.0, 284.1),
            [(0.0, 16.8), (3.5, 11.0), (7.4, 2.2), (8.4, 0.0)], mat='DarkWood', axis='Z', sides=4, rot_deg=(0, 0, 45))
    b.lathe('FinialSpike', (0.0, 0.0, 291.5),
            [(0.0, 2.2), (2.2, 1.5), (4.6, 2.4), (6.5, 1.2), (7.8, 0.0)], mat='ScaleIron', axis='Z', sides=12)

    for cz in (62.0, 152.0, 252.0):
        b.block(f'IronCollar_{cz:.0f}', (0.0, 0.0, cz), (18.4, 18.4, 4.2), mat='ScaleIron', bevel_cm=0.22)
        for sx in (-1, 1):
            b.bolt((sx * 9.3, 0.0, cz), axis='X', radius_cm=0.62, mat='Iron')
            b.bolt((0.0, sx * 9.3, cz), axis='Y', radius_cm=0.62, mat='Iron')
    b.block('BrassTrimCollar', (0.0, 0.0, 266.0), (18.2, 18.2, 2.8), mat='Brass', bevel_cm=0.2)

    b.block('BracketPlate', (9.1, 0.0, 232.0), (1.8, 7.6, 72.0), mat='ScaleIron', bevel_cm=0.22)
    for bz in (202.0, 222.0, 242.0, 262.0):
        b.bolt((10.1, 0.0, bz), axis='X', radius_cm=0.72, height_cm=0.65, mat='Iron')

    arm_pts = sample_beziers((9.2, 0.0, 250.0), [
        ((24.0, 0.0, 250.0), (38.0, 0.0, 250.2), (48.0, 0.0, 250.5)),
        ((53.5, 0.0, 250.8), (56.5, 0.0, 255.0), (54.2, 0.0, 258.6)),
        ((52.2, 0.0, 261.2), (48.2, 0.0, 260.4), (48.6, 0.0, 257.2)),
    ], 8)
    arm_secs = []
    for i in range(len(arm_pts)):
        t = i / (len(arm_pts) - 1)
        taper = 1.0 if t < 0.55 else max(0.38, 1.0 - (t - 0.55) * 1.4)
        hw, ht = 1.15 * taper, 1.45 * taper
        c = min(0.22, hw * 0.25)
        arm_secs.append([(-hw + c, -ht), (hw - c, -ht), (hw, -ht + c), (hw, ht - c),
                         (hw - c, ht), (-hw + c, ht), (-hw, ht - c), (-hw, -ht + c)])
    b.sweep_section('CraneMainArm', arm_pts, arm_secs, mat='ScaleIron', up_hint=(0, 1, 0))
    brace_pts = sample_beziers((9.2, 0.0, 204.0), [((15.0, 0.0, 224.0), (26.0, 0.0, 244.0), (41.0, 0.0, 249.6))], 12)
    b.strap('CraneArchBrace', brace_pts, 1.85, 2.2, mat='ScaleIron', up_hint=(0, 1, 0))
    scroll_pts = sample_beziers((10.5, 0.0, 244.0), [
        ((16.0, 0.0, 246.0), (20.5, 0.0, 240.0), (18.5, 0.0, 234.0)),
        ((16.5, 0.0, 228.0), (24.0, 0.0, 232.0), (29.0, 0.0, 242.5)),
        ((31.2, 0.0, 246.5), (27.5, 0.0, 248.5), (25.2, 0.0, 246.2)),
    ], 8)
    b.strap('CraneScrollFiligree', scroll_pts, 1.15, 1.35, mat='Iron', up_hint=(0, 1, 0))
    b.block('HangerSleeve', (36.0, 0.0, 250.2), (4.4, 3.6, 4.2), mat='Brass', bevel_cm=0.22)
    b.ring_torus('HangerLinkTop', (36.0, 0.0, 245.4), 2.1, 0.48, mat='ScaleIron', axis='Y', major_segs=16)
    b.ring_torus('HangerLinkMid', (36.0, 0.0, 241.2), 2.1, 0.48, mat='Iron', axis='X', major_segs=16)
    hook_pts = sample_beziers((36.0, 0.0, 239.2), [
        ((36.0, 0.0, 236.5), (36.0, 0.0, 233.5), (36.0, 0.0, 231.5)),
        ((36.0, 0.0, 229.8), (38.8, 0.0, 229.8), (39.6, 0.0, 232.4)),
    ], 8)
    b.tube('LanternHook', hook_pts, 0.52, mat='ScaleIron', sides=8)

    b.add_collider((0.0, 0.0, 16.0), (42.0, 42.0, 36.0))
    b.add_collider((0.0, 0.0, 162.0), (20.0, 20.0, 260.0))
    return b.finish(out_dir)
