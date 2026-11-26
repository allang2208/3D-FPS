"""AAA 3D Saddle Stand & Tack Wall Rack builders (PropsR44: authentic pommel, stitched skirts, braided rope, weathering)."""
import math
from mathutils import Vector

from props_geom import AssetBuilder, sample_beziers


def _add_3d_buckle(b, prefix, center_cm, w_cm, h_cm, t_cm, mat='Brass', rot_deg=(0, 0, 0)):
    """Real open-frame forged buckle with cross-bar and tongue prong (no solid brick!)."""
    b.push_xform(center_cm, rot_deg)
    hw, hh = w_cm * 0.5, h_cm * 0.5
    bar = max(0.32, min(w_cm, h_cm) * 0.16)
    b.block(prefix + '_Top', (0.0, 0.0, hh - bar * 0.5), (w_cm, t_cm, bar), mat=mat, bevel_cm=0.10)
    b.block(prefix + '_Bot', (0.0, 0.0, -hh + bar * 0.5), (w_cm, t_cm, bar), mat=mat, bevel_cm=0.10)
    b.block(prefix + '_L', (-hw + bar * 0.5, 0.0, 0.0), (bar, t_cm, h_cm), mat=mat, bevel_cm=0.10)
    b.block(prefix + '_R', (hw - bar * 0.5, 0.0, 0.0), (bar, t_cm, h_cm), mat=mat, bevel_cm=0.10)
    b.block(prefix + '_PinBar', (0.0, -t_cm * 0.1, 0.0), (w_cm - bar, t_cm * 0.65, bar * 0.72), mat='Iron', bevel_cm=0.06)
    b.beam(prefix + '_Prong', (0.0, 0.0, 0.0), (0.0, t_cm * 0.35, -hh + bar * 0.35), bar * 0.55, bar * 0.55,
           mat='Iron', wear=0.0, endgrain=False)
    b.pop_xform()


def build_saddle_stand(out_dir):
    """Hero oak saddle horse + fringed woven wool blanket + RDR2-grade contoured warhorse saddle & aged iron stirrups."""
    b = AssetBuilder('SM_Stable_SaddleStand', seed=4411, ground_mud_cm=32.0)

    # --- 1. Hand-Hewn Mortise-and-Tenon Oak Saddle Horse (Z_min = 0.00 cm exact, forged iron floor ferrules) ---
    for sx in (-1, 1):
        for sy in (-1, 1):
            x_bot, x_top = sx * 42.5, sx * 34.0
            y_bot, y_top = sy * 28.0, sy * 6.5
            # Leg rests solidly into forged iron floor shoe ferrule (Z=0..6.5 cm)
            b.beam(f'Leg_{sx}_{sy}', (x_bot, y_bot, 0.2), (x_top, y_top, 72.0), 6.6, 6.6, mat='OiledOak', wear=0.10)
            b.block(f'FloorFerrule_{sx}_{sy}', (x_bot, y_bot, 3.2), (7.6, 7.6, 6.4), mat='ScaleIron', bevel_cm=0.22)
            b.bolt((x_bot + sx * 3.9, y_bot, 3.8), axis='X', radius_cm=0.45, mat='Iron')
            b.bolt((x_top + sx * 2.4, y_top + sy * 2.4, 65.5), axis='Y', radius_cm=0.58, mat='Iron')
            b.peg((x_bot * 0.48 + x_top * 0.52, y_bot * 0.48 + y_top * 0.52 + sy * 3.1, 31.5), axis='Y')

        b.beam(f'EndLowerTie_{sx}', (sx * 38.8, -22.5, 29.0), (sx * 38.8, 22.5, 29.0), 5.6, 6.6, mat='Oak')
        b.beam(f'EndUpperTie_{sx}', (sx * 34.5, -13.5, 62.0), (sx * 34.5, 13.5, 62.0), 5.8, 7.0, mat='OiledOak')
        # Forged iron A-frame gusset plate + rivets
        b.block(f'ApexStrap_{sx}', (sx * 34.5, 0.0, 67.6), (5.0, 16.2, 2.5), mat='ScaleIron', bevel_cm=0.18)
        for sy in (-1, 1):
            b.bolt((sx * 37.2, sy * 5.0, 67.6), axis='X', radius_cm=0.55, mat='Iron')
        # Protruding pegged through-tenon wedges at lower stretcher ends
        b.block(f'TenonEnd_{sx}', (sx * 43.2, 0.0, 29.0), (4.2, 4.6, 5.4), mat='Endgrain', bevel_cm=0.22)
        b.block(f'TenonWedge_{sx}', (sx * 43.8, 0.0, 29.5), (1.4, 2.2, 8.2), mat='DarkWood', bevel_cm=0.14)

    # Central heavy through-tenon stretcher + slatted tack shelf
    b.plank('CenterStretcher', (0.0, 0.0, 29.0), (84.0, 5.4, 6.6), mat='DarkWood', wear=0.08)
    for sy in (-1, 1):
        b.plank(f'ShelfRail_{sy}', (0.0, sy * 17.8, 30.2), (83.0, 4.4, 5.4), mat='Oak', wear=0.08)
    for k in range(5):
        yy = -14.0 + k * 7.0
        b.plank(f'ShelfSlat_{k}', (0.0, yy, 33.4), (78.0, 5.5, 2.1), mat='Sawn', wear=0.07)
        for sx in (-34.5, 34.5):
            b.bolt((sx, yy, 34.5), axis='Z', radius_cm=0.40, height_cm=0.30, mat='Iron')

    b.beam('UnderStrutA', (-32.0, 0.0, 33.5), (0.0, 0.0, 71.0), 4.8, 5.6, mat='Oak')
    b.beam('UnderStrutB', (32.0, 0.0, 33.5), (0.0, 0.0, 71.0), 4.8, 5.6, mat='Oak')

    # Arched heavy oiled-oak saddle spine beam with wrought-iron end-caps
    b.plank('SpineCore', (0.0, 0.0, 72.5), (92.0, 12.8, 11.2), mat='OiledOak', wear=0.07)
    b.lathe('SpineCrest', (0.0, 0.0, 77.2),
            [(-46.5, 0.0), (-45.5, 6.2), (-42.0, 7.6), (42.0, 7.6), (45.5, 6.2), (46.5, 0.0)],
            mat='OiledOak', axis='X', sides=22)
    for sy in (-1, 1):
        b.plank(f'SideWing_{sy}', (0.0, sy * 11.4, 68.0), (83.0, 8.8, 3.4), mat='Oak',
                rot_deg=(sy * 34.0, 0.0, 0.0), wear=0.06)

    # Turned front bridle-peg (+X) + brass ferrule + hanging coiled leather halter with brass ring!
    b.lathe('FrontBridlePeg', (47.0, 0.0, 74.5),
            [(0.0, 2.2), (2.4, 2.5), (6.8, 1.75), (11.2, 2.45), (13.4, 2.65), (14.8, 1.45), (15.4, 0.0)],
            mat='OiledOak', axis='X', rot_deg=(0, -14, 0), sides=16)
    b.lathe('FrontBrassCap', (59.2, 0.0, 77.6),
            [(0.0, 2.5), (1.1, 2.7), (2.2, 2.05), (2.9, 0.75), (3.2, 0.0)],
            mat='Brass', axis='X', rot_deg=(0, -14, 0), sides=16)
    # Coiled leather halter hanging naturally off the front bridle peg (X = 52..57, Z = 44..78)
    for hi, (hx_off, drop) in enumerate(((53.2, 46.0), (55.4, 50.0))):
        h_pts = [(hx_off + 0.6 * math.sin(k * math.tau * 2 / 24),
                  5.8 * math.sin(k * math.tau / 24),
                  (76.5 + drop) * 0.5 + (76.5 - drop) * 0.5 * math.cos(k * math.tau / 24))
                 for k in range(24)]
        b.strap(f'HalterLoop_{hi}', h_pts, 1.8, 0.52, mat='LeatherDark', cyclic=True, up_hint=(1, 0, 0))
    b.ring_torus('HalterBrassRing', (54.4, 0.0, 45.2), 2.1, 0.38, mat='Brass', axis='X', major_segs=16)

    # --- 2. Heavy Woven Striped Wool Saddle Blanket + Hanging Wool Fringe Tassels ---
    nu_b, nv_b = 22, 26
    blanket_grid = []
    for i in range(nu_b):
        u = i / (nu_b - 1)
        x = -34.5 + u * 67.0
        row = []
        for j in range(nv_b):
            v = (j / (nv_b - 1)) * 2.0 - 1.0
            av = abs(v)
            sgn = -1.0 if v < 0 else 1.0
            if av < 0.35:
                ang = (av / 0.35) * (math.pi * 0.44)
                y = sgn * (13.4 * math.sin(ang))
                z = 74.0 + 12.1 * math.cos(ang)
            else:
                t_drop = (av - 0.35) / 0.65
                y = sgn * (13.2 + 10.6 * math.sin(t_drop * math.pi * 0.48) + 2.0 * t_drop)
                z = 76.0 - 25.5 * t_drop
            fold = (math.sin(u * math.pi * 4.0 + v * 2.2) * 0.85 + math.cos(u * math.pi * 7.0) * 0.30) * (av ** 1.55)
            edge_lift = math.cos((u - 0.5) * math.pi) * 1.4 * (av ** 1.2)
            row.append((x, y + sgn * fold, z + edge_lift))
        blanket_grid.append(row)
    b.thick_grid('SaddleBlanket', blanket_grid, thick_cm=1.45, mat='Blanket')

    # Woven wool fringe tassels hanging cleanly outside lower rack slats along both bottom blanket hems
    for side_idx in (0, nv_b - 1):
        for i in range(1, nu_b - 1, 2):
            p = blanket_grid[i][side_idx]
            sgn_f = -1.0 if p[1] < 0 else 1.0
            fringe_pts = [(p[0], p[1], p[2] + 0.3), (p[0] + 0.2, p[1] + sgn_f * 0.4, p[2] - 1.5),
                          (p[0] + 0.35, p[1] + sgn_f * 0.7, p[2] - 3.0)]
            b.tube(f'BlanketFringe_{side_idx}_{i}', fringe_pts, 0.34, mat='Blanket', sides=6)

    # --- 3. AAA Sculpted Medieval Riding & Cavalry Saddle (Graceful Arched Pommel + Deep Cantle, Zero Doorknob!) ---
    # 3a. Contoured deep leather saddle tree & seat with high curved cantle & matching sculpted medieval pommel arch
    nu_s, nv_s = 28, 22
    seat_grid = []
    for i in range(nu_s):
        u = i / (nu_s - 1)  # 0 = rear cantle (-28 cm), 1 = front pommel arch (+26 cm)
        x = -28.0 + u * 54.0
        cantle_rise = 16.5 * max(0.0, (0.35 - u) / 0.35) ** 1.85
        # Sleek sculpted medieval curved pommel arch rising gracefully at front (matches cantle silhouette, NO stalk!)
        pommel_rise = 13.5 * max(0.0, (u - 0.62) / 0.38) ** 1.75
        pocket_dip = -4.6 * math.sin(max(0.0, min(1.0, (u - 0.10) / 0.72)) * math.pi)
        half_w = 18.8 * (0.74 + 0.32 * math.sin(u * math.pi) - 0.24 * max(0.0, (u - 0.66) / 0.34))
        row = []
        for j in range(nv_s):
            v = (j / (nv_s - 1)) * 2.0 - 1.0
            av = abs(v)
            x_wrap = x + (7.4 * (av ** 1.75) if u < 0.36 else -4.6 * (av ** 1.75) * max(0.0, (u - 0.62) / 0.38))
            y = v * half_w
            arch_drop = -11.6 * (av ** 1.95)
            cantle_bowl = cantle_rise * (1.0 - 0.48 * (av ** 2.1))
            pommel_arch = pommel_rise * (1.0 - 0.56 * (av ** 1.85))
            z = 88.2 + pocket_dip + cantle_bowl + pommel_arch + arch_drop
            row.append((x_wrap, y, z))
        seat_grid.append(row)
    b.thick_grid('SaddleSeat', seat_grid, thick_cm=2.5, mat='LeatherMain', rim_mat='LeatherDark')

    # Padded quilted leather rider seat cushion + recessed saddle-stitch border
    nu_c, nv_c = 16, 14
    cush_grid = []
    for i in range(nu_c):
        u = i / (nu_c - 1)
        x = -20.0 + u * 38.5
        row = []
        for j in range(nv_c):
            v = (j / (nv_c - 1)) * 2.0 - 1.0
            av = abs(v)
            hw = 13.8 * math.sqrt(max(0.06, 1.0 - ((u - 0.46) * 1.40) ** 2))
            y = v * hw
            z = 87.6 - 2.9 * math.sin(u * math.pi) + 4.4 * max(0.0, (0.36 - u) / 0.36) ** 1.6 \
                - 3.5 * (av ** 2.0) + 1.6 * math.cos(v * math.pi * 0.5) * math.sin(u * math.pi)
            row.append((x, y, z))
        cush_grid.append(row)
    b.thick_grid('SeatCushion', cush_grid, thick_cm=2.0, mat='LeatherMain', rim_mat='LeatherDark')
    # Quilted seat-welt stitching around cushion edge
    for s_side in (0, nv_c - 1):
        c_stitch = [(cush_grid[i][s_side][0], cush_grid[i][s_side][1] * 0.96, cush_grid[i][s_side][2] + 0.9)
                    for i in range(1, nu_c - 1)]
        b.tube(f'SeatStitch_{s_side}', c_stitch, 0.24, mat='WaxedThread', sides=6)

    # Rolled leather pommel arch welt, twin waxed-thread stitch rows, aged brass gullet emblem & breastplate D-rings
    pommel_pts = [(seat_grid[-1][j][0] + 0.4, seat_grid[-1][j][1], seat_grid[-1][j][2] + 0.9) for j in range(nv_s)]
    b.tube('PommelRimRoll', pommel_pts, 1.75, mat='LeatherDark', sides=12)
    for row_off, r_st in ((-1.35, 0.25), (-2.25, 0.22)):
        pst_pts = [(p[0] + row_off, p[1] * 0.93, p[2] - 0.50) for p in pommel_pts[1:-1]]
        b.tube(f'PommelStitch_{abs(row_off):.1f}', pst_pts, r_st, mat='WaxedThread', sides=6)
    # Recessed forged brass gullet plate & twin side breastplate rings (authentic Normandy road/warhorse saddle hardware!)
    b.lathe('PommelBrassBoss', (26.4, 0.0, 99.8),
            [(0.0, 2.8), (0.6, 2.9), (1.2, 2.2), (1.5, 0.0)], mat='Brass', axis='X', rot_deg=(0, -18, 0), sides=16)
    for sy in (-1, 1):
        b.ring_torus(f'BreastplateRing_{sy}', (22.2, sy * 11.4, 92.2), 1.65, 0.34, mat='Brass', axis='Y', major_segs=14)
        b.block(f'BreastplateTab_{sy}', (21.5, sy * 10.6, 93.2), (2.4, 1.4, 3.2), mat='LeatherDark', bevel_cm=0.12)

    # Double rolled cantle leather welt + crisp double waxed-thread stitch rows
    cantle_pts = [(seat_grid[0][j][0] - 0.4, seat_grid[0][j][1], seat_grid[0][j][2] + 1.0) for j in range(nv_s)]
    b.tube('CantleRimRoll', cantle_pts, 1.65, mat='LeatherDark', sides=12)
    for row_off, r_st in ((1.35, 0.25), (2.25, 0.22)):
        st_pts = [(p[0] + row_off, p[1] * 0.93, p[2] - 0.45) for p in cantle_pts[1:-1]]
        b.tube(f'CantleStitch_{row_off:.1f}', st_pts, r_st, mat='WaxedThread', sides=6)

    # 3b. Multi-Layered Contoured Saddle Skirts, Flaps, Sculpted Knee-Rolls & Detailed Stirrup Rigging (+Y / -Y)
    for sy in (-1, 1):
        # Layer 1: Wide contoured under-skirt (LeatherDark) peeking below the main flap like stable_saddle.png
        nu_u, nv_u = 16, 10
        under_grid = []
        for i in range(nu_u):
            u = i / (nu_u - 1)
            env = math.sin(u * math.pi) ** 0.5
            row = []
            for j in range(nv_u):
                v = j / (nv_u - 1)
                xc = -3.0 + 3.5 * v
                hs = 26.0 * (1.0 - 0.22 * (v ** 1.5))
                xv = xc + (u * 2.0 - 1.0) * hs
                zv = 84.5 - 3.0 * ((u * 2.0 - 1.0) ** 2) - (26.5 * (0.58 + 0.42 * env)) * v
                yv = sy * (15.0 + 7.2 * math.sin(v * math.pi * 0.50))
                row.append((xv, yv, zv))
            under_grid.append(row)
        b.thick_grid(f'UnderSkirt_{sy}', under_grid, thick_cm=1.25, mat='LeatherDark')

        # Layer 2: Main rounded bell/teardrop riding flap (LeatherMain) with rolled perimeter welt & contrast stitch
        nu_f, nv_f = 20, 14
        flap_grid = []
        for i in range(nu_f):
            u = i / (nu_f - 1)
            arch_env = math.sin(u * math.pi) ** 0.55
            row = []
            for j in range(nv_f):
                v = j / (nv_f - 1)
                x_center = -0.5 + 6.0 * (v ** 1.15)
                half_span = (22.0 * (1.0 - 0.34 * (v ** 1.6))) * (0.45 + 0.55 * (1.0 - v * 0.32))
                x_val = x_center + (u * 2.0 - 1.0) * half_span
                z_top = 85.0 - 3.6 * ((u * 2.0 - 1.0) ** 2)
                z_val = z_top - (31.5 * (0.52 + 0.48 * arch_env)) * v
                # Add subtle sculpted forward knee-roll bolster puff along front edge (u > 0.65)!
                knee_puff = 1.85 * math.exp(-((u - 0.78) / 0.16) ** 2) * math.sin(v * math.pi)
                y_val = sy * (16.4 + 7.2 * math.sin(v * math.pi * 0.52) + 1.2 * math.sin(u * math.pi) * math.sin(v * math.pi) + knee_puff)
                row.append((x_val, y_val, z_val))
            flap_grid.append(row)
        b.thick_grid(f'SaddleFlap_{sy}', flap_grid, thick_cm=1.55, mat='LeatherMain', rim_mat='LeatherDark')

        # Rolled leather edging & waxed-thread stitching tracing the lower flap contour
        rim_pts = [(p[0], p[1] + sy * 0.35, p[2]) for p in [flap_grid[i][-1] for i in range(nu_f)]]
        b.tube(f'FlapRimWelt_{sy}', rim_pts, 0.72, mat='LeatherDark', sides=8)
        st_pts = [(p[0], p[1] + sy * 0.92, p[2] + 1.35) for p in [flap_grid[i][-1] for i in range(1, nu_f - 1)]]
        b.tube(f'FlapStitch_{sy}', st_pts, 0.26, mat='WaxedThread', sides=6)

        # Layer 3: Soft contoured upper seat-jockey flap tucked neatly over waist (matches stable_saddle.png)
        nu_j, nv_j = 16, 8
        jockey_grid = []
        for i in range(nu_j):
            u = i / (nu_j - 1)
            scallop = math.sin(u * math.pi) ** 0.75
            row = []
            for j in range(nv_j):
                v = j / (nv_j - 1)
                x_val = -21.5 + u * 39.0 + 1.8 * v
                z_val = 86.2 - (10.2 * scallop + 2.2) * v - 2.2 * ((u * 2.0 - 1.0) ** 2)
                y_val = sy * (15.8 + 6.0 * math.sin(v * math.pi * 0.55) + 0.85 * scallop)
                row.append((x_val, y_val, z_val))
            jockey_grid.append(row)
        b.thick_grid(f'SeatJockey_{sy}', jockey_grid, thick_cm=1.35, mat='LeatherMain', rim_mat='LeatherDark')
        j_stitch = [(jockey_grid[i][-1][0], jockey_grid[i][-1][1] + sy * 0.72, jockey_grid[i][-1][2] + 0.8)
                    for i in range(1, nu_j - 1)]
        b.tube(f'JockeyStitch_{sy}', j_stitch, 0.22, mat='WaxedThread', sides=6)

        # Riveted front rigging strap yoke + aged brass concho rosettes + forged iron cinch D-ring
        yoke_pts = sample_beziers((19.5, sy * 11.4, 91.2),
                                  [((15.8, sy * 17.8, 86.2), (10.5, sy * 21.0, 81.8), (3.8, sy * 22.6, 79.6))], 10)
        b.strap(f'FrontYoke_{sy}', yoke_pts, 3.6, 0.90, mat='LeatherDark', up_hint=(0, sy, 0))
        for rx, ry, rz in ((16.5, 17.0, 86.8), (6.0, 22.2, 80.2), (-21.0, 15.8, 85.8)):
            b.lathe(f'BrassConcho_{sy}_{rx:.0f}', (rx, sy * ry, rz),
                    [(0.0, 1.45), (0.35, 1.38), (0.75, 0.85), (0.95, 0.0)], mat='Brass', axis='Y',
                    rot_deg=(0 if sy > 0 else 180, 0, 0), sides=14)
        b.ring_torus(f'FrontDRing_{sy}', (13.6, sy * 21.6, 81.2), 2.35, 0.44, mat='ScaleIron', axis='Y', major_segs=18)

        # 3c. Detailed Stirrup Leather + Punched Belt Holes + 3D Open-Frame Brass Buckle + Heavy Weathered Iron Stirrup
        sx_st = 3.2
        sy_st = sy * 25.6
        st_pts = sample_beziers((sx_st, sy * 21.0, 81.0), [
            ((sx_st, sy * 24.8, 73.5), (sx_st, sy * 26.2, 58.0), (sx_st, sy_st, 42.5)),
        ], 14)
        b.strap(f'StirrupLeather_{sy}', st_pts, 3.4, 0.90, mat='LeatherDark', up_hint=(0, sy, 0))
        # Real riveted leather belt-hole studs/eyelets along the upper stirrup strap
        for hz in (74.5, 71.0, 67.5, 64.0):
            b.lathe(f'StrapHole_{sy}_{hz:.0f}', (sx_st, sy * 25.6, hz),
                    [(0.0, 0.42), (0.55, 0.38)], mat='ScaleIron', axis='Y', sides=10)
        # Real open-frame 3D aged-brass buckle with cross-bar & prong + stitched leather keeper loop!
        _add_3d_buckle(b, f'StirrupBuckle_{sy}', (sx_st, sy * 26.2, 59.5), 4.8, 5.2, 1.25, mat='Brass',
                       rot_deg=(0, 0, 0 if sy > 0 else 180))
        b.block(f'StirrupKeeper_{sy}', (sx_st, sy * 25.9, 53.6), (4.2, 1.85, 2.2), mat='LeatherMain', bevel_cm=0.22)

        # Heavy forged aged-iron & burnished-steel warhorse stirrup (matching stable_saddle.png dark forged look!)
        st_top, st_bot = 42.8, 27.2
        b.block(f'StirrupEye_{sy}', (sx_st, sy_st, st_top), (4.6, 1.8, 2.6), mat='ScaleIron', bevel_cm=0.24)
        arch_pts = sample_beziers((sx_st - 7.0, sy_st, st_bot + 1.0), [
            ((sx_st - 7.8, sy_st, 35.0), (sx_st - 4.4, sy_st, 40.6), (sx_st, sy_st, st_top - 0.5)),
            ((sx_st + 4.4, sy_st, 40.6), (sx_st + 7.8, sy_st, 35.0), (sx_st + 7.0, sy_st, st_bot + 1.0)),
        ], 12)
        b.strap(f'StirrupArch_{sy}', arch_pts, 2.5, 1.35, mat='ScaleIron', up_hint=(0, sy, 0))
        # Wide forged stirrup tread plate with 3 raised anti-slip traction ribs
        b.block(f'StirrupTread_{sy}', (sx_st, sy_st, st_bot + 0.6), (14.8, 5.8, 1.5), mat='ScaleIron', bevel_cm=0.26)
        for tr_y in (-1.6, 0.0, 1.6):
            b.block(f'StirrupRib_{sy}_{tr_y:.1f}', (sx_st, sy_st + tr_y, st_bot + 1.45), (12.8, 0.55, 0.35),
                    mat='Steel', bevel_cm=0.08)

    b.add_collider((2.0, 0.0, 56.0), (106.0, 62.0, 112.0))
    return b.finish(out_dir)


def _add_horseshoe(b, name, center_cm, rot_deg=(0, 0, 0), radius=7.6):
    """High-detail hand-forged horseshoe with beveled fuller groove, toe clip & 7 recessed bright nail slots."""
    b.push_xform(center_cm, rot_deg)
    steps = 24
    pts, secs = [], []
    for i in range(steps + 1):
        t = i / steps
        ang = math.radians(-136.0 + t * 272.0)
        r = radius * (1.0 - 0.08 * (abs(t - 0.5) * 2.0) ** 1.8)
        pts.append((r * math.sin(ang), 0.0, r * math.cos(ang)))
        w = 2.55 - 0.55 * (abs(t - 0.5) * 2.0) ** 1.4
        th = 1.15
        hw, ht, c = w * 0.5, th * 0.5, 0.25
        secs.append([(-hw + c, -ht), (hw - c, -ht), (hw, -ht + c), (hw, ht - c),
                     (hw - c, ht), (-hw + c, ht), (-hw, ht - c), (-hw, -ht + c)])
    b.sweep_section(name + '_Web', pts, secs, mat='ScaleIron', up_hint=(0, 1, 0))
    b.block(name + '_ToeClip', (0.0, 0.45, radius + 1.2), (2.0, 0.70, 1.75), mat='ScaleIron', bevel_cm=0.16)
    for deg in (-98, -64, -32, 0, 32, 64, 98):
        a = math.radians(deg)
        b.block(f'{name}_Nail_{deg}', (radius * math.sin(a), 0.0, radius * math.cos(a)),
                (0.92, 1.32, 0.92), mat='Steel', rot_deg=(0, deg, 0), bevel_cm=0.12)
    b.pop_xform()


def build_tack_wall_rack(out_dir):
    """Wall-mounted chamfered oak tack rack with 3-strand braided hemp rope, bridle, 5 horseshoes & grooming tools."""
    b = AssetBuilder('SM_Stable_TackWallRack', seed=4419, is_wall_mounted=True)

    # --- 1. Chamfered Oak Wall Backboard ---
    for z_row in (-8.4, 8.4):
        b.plank(f'BackPlank_{z_row}', (0.0, 2.2, z_row), (130.0, 3.6, 15.8), mat='OiledOak', wear=0.09)
    for sx in (-48.0, 0.0, 48.0):
        b.plank(f'RearCleat_{sx}', (sx, 0.7, 0.0), (7.5, 1.4, 34.5), mat='DarkWood', wear=0.04)
    for sx in (-56.0, 56.0):
        b.block(f'IronMount_{sx}', (sx, 4.35, 0.0), (4.8, 1.15, 35.4), mat='ScaleIron', bevel_cm=0.16)
        for sz in (-12.5, 0.0, 12.5):
            b.bolt((sx, 5.0, sz), axis='Y', radius_cm=0.70, height_cm=0.60, mat='Iron')
    b.plank('TopLedge', (0.0, 8.2, 17.8), (132.0, 14.8, 3.2), mat='OiledOak', wear=0.06)
    for sx in (-46.0, 46.0):
        b.beam(f'Corbel_{sx}', (sx, 4.0, 4.0), (sx, 12.5, 16.5), 3.6, 4.4, mat='Oak')
        b.peg((sx, 4.2, 16.4), axis='Y')

    for idx_p, px in enumerate((-40.0, -12.0, 20.0, 46.0)):
        b.lathe(f'TackPeg_{idx_p}', (px, 4.0, -2.5),
                [(0.0, 2.4), (2.2, 2.6), (6.5, 1.65), (12.0, 1.85), (14.2, 2.45), (15.6, 1.4), (16.2, 0.0)],
                mat='OiledOak', axis='Y', rot_deg=(12, 0, 0), sides=16)
        b.lathe(f'PegCollar_{idx_p}', (px, 4.2, -2.5),
                [(0.0, 2.75), (1.1, 2.85), (1.8, 2.5)], mat='Brass', axis='Y', sides=16)

    for idx_h, hx in enumerate((5.0, 34.0)):
        hook_pts = sample_beziers((hx, 4.0, 3.5), [
            ((hx, 4.6, -4.5), (hx, 5.2, -8.5), (hx, 11.2, -9.2)),
            ((hx, 14.5, -9.2), (hx, 15.8, -5.8), (hx, 14.2, -2.8)),
        ], 8)
        b.strap(f'IronHook_{idx_h}', hook_pts, 1.65, 0.74, mat='ScaleIron', up_hint=(1, 0, 0))
        b.bolt((hx, 4.5, 3.2), axis='Y', radius_cm=0.55, mat='Iron')

    # --- 2. Mounted Leather Bridle, 3D Buckles, Jointed Snaffle Bit & Coiled Reins (X = -40) ---
    bx = -40.0
    crown_pts = sample_beziers((bx - 8.2, 11.8, -12.0), [
        ((bx - 8.8, 12.6, 2.0), (bx - 4.5, 13.4, 3.8), (bx, 13.6, 3.4)),
        ((bx + 4.5, 13.4, 3.8), (bx + 8.8, 12.6, 2.0), (bx + 8.2, 11.8, -12.0)),
    ], 9)
    b.strap('BridleCrown', crown_pts, 2.6, 0.75, mat='LeatherDark', up_hint=(0, 1, 0))
    for s in (-1, 1):
        cheek_pts = sample_beziers((bx + s * 8.2, 11.8, -12.0),
                                   [((bx + s * 8.0, 11.4, -22.0), (bx + s * 7.6, 11.0, -32.0), (bx + s * 7.2, 10.6, -40.0))], 8)
        b.strap(f'BridleCheek_{s}', cheek_pts, 2.15, 0.68, mat='LeatherMain', up_hint=(0, 1, 0))
        b.lathe(f'BridleRosette_{s}', (bx + s * 8.2, 12.3, -10.5),
                [(0.0, 1.95), (0.6, 1.85), (1.1, 1.0), (1.3, 0.0)], mat='Brass', axis='Y', sides=16)
        _add_3d_buckle(b, f'BridleBuckle_{s}', (bx + s * 7.8, 11.6, -24.0), 3.0, 3.2, 0.95, mat='Brass')
    brow_pts = sample_beziers((bx - 8.2, 12.2, -10.5),
                              [((bx - 3.5, 14.8, -12.5), (bx + 3.5, 14.8, -12.5), (bx + 8.2, 12.2, -10.5))], 8)
    b.strap('BridleBrowband', brow_pts, 2.1, 0.68, mat='LeatherDark', up_hint=(0, 1, 0))
    nose_pts = sample_beziers((bx - 7.5, 11.4, -31.5),
                              [((bx - 3.5, 15.2, -33.0), (bx + 3.5, 15.2, -33.0), (bx + 7.5, 11.4, -31.5))], 8)
    b.strap('BridleNoseband', nose_pts, 2.4, 0.72, mat='LeatherMain', up_hint=(0, 1, 0))
    for s in (-1, 1):
        b.ring_torus(f'SnaffleRing_{s}', (bx + s * 7.2, 10.6, -42.5), 3.4, 0.46, mat='Steel', axis='Y', major_segs=18)
    b.beam('BitLeft', (bx - 6.8, 10.6, -42.5), (bx - 0.5, 10.6, -43.5), 1.0, 1.0, mat='Steel', wear=0.0, endgrain=False)
    b.beam('BitRight', (bx + 0.5, 10.6, -43.5), (bx + 6.8, 10.6, -42.5), 1.0, 1.0, mat='Steel', wear=0.0, endgrain=False)
    b.ring_torus('BitCenterLink', (bx, 10.6, -43.5), 1.05, 0.34, mat='Steel', axis='X', major_segs=12)
    for loop_i, (y_off, drop_z) in enumerate(((14.2, -62.0), (16.4, -57.5))):
        rein_pts = [(bx + 9.2 * math.sin(k * math.tau / 28),
                     y_off + 1.4 * math.sin(k * math.tau / 14),
                     (-28.0 + drop_z * 0.5) + (30.0 - loop_i * 2.5) * math.cos(k * math.tau / 28))
                    for k in range(28)]
        b.strap(f'CoiledReins_{loop_i}', rein_pts, 1.95, 0.60, mat='LeatherDark', cyclic=True, up_hint=(0, 1, 0))

    # --- 3. Second Peg (-12 cm): True 3-Strand Helical Braided Hemp Lead Rope ---
    rx0 = -12.0
    for turn in range(3):
        coil = [(rx0 + (8.4 + turn * 0.6) * math.sin(k * math.tau / 28),
                 8.8 + turn * 2.3 + 0.6 * math.cos(k * math.tau * 3 / 28),
                 -21.0 + (22.5 - turn * 0.8) * math.cos(k * math.tau / 28))
                for k in range(28)]
        b.rope_braid(f'LeadRopeCoil_{turn}', coil, radius_cm=0.95, mat='Rope', cyclic=True, pitch_cm=6.0, sample_step_cm=2.2)
    tail_pts = sample_beziers((rx0 + 4.5, 14.0, -34.0), [((rx0 + 5.2, 14.6, -44.0), (rx0 + 3.8, 14.2, -51.0), (rx0 + 3.2, 13.8, -56.0))], 8)
    b.rope_braid('LeadRopeTail', tail_pts, radius_cm=0.95, mat='Rope', pitch_cm=6.0, sample_step_cm=2.0)
    b.lathe('BrassLeadSnap', (rx0 + 3.2, 13.8, -56.2),
            [(0.0, 1.18), (-1.8, 1.08), (-4.2, 0.74), (-5.8, 0.96), (-6.6, 0.0)], mat='Brass', axis='Z', sides=12)

    # --- 4. Iron Hook 0 (+5 cm): Cluster of 4 Forged Horseshoes on Braided Hemp Cord ---
    hx0 = 5.0
    b.ring_torus('ShoeCordHookLoop', (hx0, 11.4, -8.8), 1.6, 0.48, mat='Rope', axis='X', major_segs=14)
    cord_pts = sample_beziers((hx0, 11.4, -10.2), [((hx0 - 1.0, 12.2, -16.5), (hx0 - 0.5, 13.0, -22.5), (hx0, 13.6, -27.5))], 8)
    b.rope_braid('ShoeCord', cord_pts, radius_cm=0.55, mat='Rope', pitch_cm=4.5, sample_step_cm=1.8)
    for si, (pos, rot) in enumerate([
        ((hx0 - 1.5, 11.8, -28.0), (6, -12, 8)),
        ((hx0 + 1.8, 13.6, -30.5), (-8, 14, -10)),
        ((hx0 - 2.2, 15.2, -33.0), (10, -18, 14)),
        ((hx0 + 0.8, 16.8, -35.5), (-5, 8, -6)),
    ]):
        _add_horseshoe(b, f'Horseshoe_{si}', pos, rot_deg=rot, radius=7.5)

    # --- 5. Grooming Kit: Sculpted Oval Brush (+20), Hoof Pick (+34), Connected Curry Comb (+46) ---
    b.push_xform((20.0, 12.2, -21.5), (0, 5, 0))
    loop_pts = sample_beziers((0.0, 0.0, 9.0), [
        ((-1.8, -0.4, 16.5), (-2.2, 0.0, 22.8), (0.0, 0.0, 23.0)),
        ((2.2, 0.0, 22.8), (1.8, -0.4, 16.5), (0.0, 0.0, 9.0)),
    ], 8)
    b.tube('BrushLanyard', loop_pts, 0.36, mat='LeatherDark', sides=6)
    b.ring_torus('BrushTopEye', (0.0, 0.0, 9.5), 0.9, 0.28, mat='Brass', axis='Y', major_segs=12)
    oval_pts = [(0.0, -1.2, 0.0), (0.0, -0.6, 0.0), (0.0, 0.8, 0.0), (0.0, 1.4, 0.0)]
    oval_secs = [[(4.6 * sc_r * math.cos(k * math.tau / 24), 9.2 * sc_r * math.sin(k * math.tau / 24))
                  for k in range(24)] for sc_r in (0.82, 0.98, 1.0, 0.92)]
    b.sweep_section('BrushOvalBack', oval_pts, oval_secs, mat='OiledOak', up_hint=(0, 0, 1))
    bristle_pts = [(0.0, 1.3, 0.0), (0.0, 4.4, 0.0), (0.0, 4.9, 0.0)]
    bristle_secs = [[(4.1 * sc_r * math.cos(k * math.tau / 24), 8.6 * sc_r * math.sin(k * math.tau / 24))
                     for k in range(24)] for sc_r in (1.0, 1.02, 0.94)]
    b.sweep_section('BrushOvalBristles', bristle_pts, bristle_secs, mat='Linen', up_hint=(0, 0, 1))
    hand_strap = sample_beziers((-4.2, -0.8, 0), [((-3.0, -3.8, 0), (3.0, -3.8, 0), (4.2, -0.8, 0))], 8)
    b.strap('BrushHandStrap', hand_strap, 2.8, 0.55, mat='LeatherDark', up_hint=(0, 0, 1))
    b.rivet((-4.0, -0.9, 0), axis='Y', radius_cm=0.42, mat='Brass')
    b.rivet((4.0, -0.9, 0), axis='Y', radius_cm=0.42, mat='Brass')
    b.pop_xform()

    b.push_xform((34.0, 12.2, -9.2), (0, -3, 0))
    b.ring_torus('HoofPickRing', (0, 0, 0), 1.75, 0.36, mat='ScaleIron', axis='Y', major_segs=14)
    pick_pts = sample_beziers((0, 0, -1.7), [
        ((0, 0, -7.0), (0, 0.2, -13.0), (0, 0.5, -17.5)),
        ((0, 1.8, -20.5), (0, 4.8, -21.8), (0, 7.2, -20.4)),
    ], 9)
    pick_r = [0.55] * 10 + [0.55 - 0.32 * (k / 9.0) for k in range(1, 10)]
    b.tube('HoofPickBody', pick_pts, pick_r, mat='Steel', sides=8)
    b.pop_xform()

    b.push_xform((46.0, 12.4, -22.5), (0, -4, 0))
    curry_loop = sample_beziers((0.0, 0.0, 15.5), [
        ((-1.7, -0.3, 19.5), (-2.0, 0.0, 24.0), (0.0, 0.0, 24.2)),
        ((2.0, 0.0, 24.0), (1.7, -0.3, 19.5), (0.0, 0.0, 15.5)),
    ], 8)
    b.tube('CurryLanyard', curry_loop, 0.34, mat='LeatherDark', sides=6)
    b.ring_torus('CurryTopEye', (0.0, 0.0, 15.8), 0.85, 0.26, mat='Brass', axis='Y', major_segs=12)
    b.lathe('CurryHandle', (0, 0, 6.5),
            [(0.0, 1.25), (1.2, 1.55), (4.8, 1.82), (8.2, 1.38), (9.1, 0.0)], mat='OiledOak', axis='Z', sides=14)
    b.lathe('CurryFerrule', (0, 0, 5.2), [(0.0, 1.22), (1.6, 1.32)], mat='Brass', axis='Z', sides=14)
    b.beam('CurryTang', (0.0, 0.0, 5.6), (0.0, 0.0, -2.0), 1.4, 0.9, mat='ScaleIron', endgrain=False)
    b.block('CurryPlate', (0, 0.0, -5.2), (9.4, 0.95, 13.6), mat='ScaleIron', bevel_cm=0.35)
    for rib_z in (-10.0, -6.8, -3.6, -0.4):
        b.block(f'CurryRib_{rib_z}', (0, 1.35, rib_z), (8.4, 1.8, 0.50), mat='Iron', bevel_cm=0.10)
    b.pop_xform()

    _add_horseshoe(b, 'LedgeShoe', (-26.0, 9.2, 20.1), rot_deg=(90, 0, 18), radius=7.2)
    b.lathe('HoofOilTin', (36.0, 9.2, 19.4),
            [(0.0, 4.2), (0.6, 4.5), (9.4, 4.5), (10.0, 4.1), (10.3, 4.35), (11.6, 4.35), (11.9, 0.0)],
            mat='Brass', axis='Z', sides=20)
    b.lathe('OilTinLidKnob', (36.0, 9.2, 31.3),
            [(0.0, 1.3), (1.1, 1.5), (1.9, 0.9), (2.2, 0.0)], mat='Iron', axis='Z', sides=12)

    b.add_collider((0.0, 10.0, -14.0), (132.0, 20.0, 92.0))
    return b.finish(out_dir)
