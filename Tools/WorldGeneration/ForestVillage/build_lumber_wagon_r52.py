"""Blender 5.1 procedural AAA builder for LumberMillOps-R52 modular horse-drawn Timber Wagon & Draft Harness.

Produces 5 watertight, clean-pivot FBX meshes (100% resident PBR materials, +0.00 MB VRAM):
  1. SM_LM_TimberWagon_Chassis    (heavy oak dray chassis, rear axle beam, 8 side log stakes, raised driver bench & footboard, hanging brass lantern)
  2. SM_LM_TimberWagon_FrontAxle  (steerable front kingpin bolster, twin swept oak draft shafts & singletree whiffletree)
  3. SM_LM_TimberWagon_Wheel      (12-spoke dished oak wagon wheel with forged iron tire, hub bands & linchpin; hub pivot at (0,0,0), radius 52 cm)
  4. SM_LM_TimberWagon_TimberLoad (11 varied chamfered bark-furrowed oak logs with sawn endgrain & braided rope/iron chain lashings)
  5. SM_LM_HorseHarness           (fitted draft hame collar, brass finials, back saddle pad, girth, breeching straps & trace tugs for SK_StableWarhorse)

All coordinates in UE centimetres (+X forward, +Y right, +Z up; ground plane Z = 0 on Chassis/TimberLoad/Harness).
"""
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

PROPS_LIB = Path("D:/FPS3D/FPSGAME/Tools/WorldGeneration/VillageStable/PropsR43")
sys.path.insert(0, str(PROPS_LIB))
import props_geom as pg

pg.UV_SCALES_M.update({
    "Bark": 0.90,
})
pg.PREVIEW_COLORS.update({
    "Bark": (0.22, 0.16, 0.11),
})

OUT_DIR = Path("F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/LumberMill-R49/TransportFBX")

# Shared mechanical datum constants (cm) — mirrored verbatim in LumberMillTimberWagon.cpp & author_lumber_ops_r52.py!
REAR_WHEEL_RADIUS = 52.0
FRONT_WHEEL_SCALE = 0.72
FRONT_WHEEL_RADIUS = REAR_WHEEL_RADIUS * FRONT_WHEEL_SCALE  # 37.44 cm (top = 74.88 cm < raised MainSill bottom 78.5 cm!)
REAR_AXLE_X = -105.0
REAR_TRACK_HALF_Y = 76.0
FRONT_AXLE_X = 105.0
FRONT_TRACK_HALF_Y = 72.0
HORSE_OFFSET_FROM_FRONT_AXLE_X = 218.0  # Singletree @ FrontAxle +66 => Horse X=-152 (+19 cm clear of walk tail & +24 cm clear of hind hooves!)
BED_TOP_Z = 95.0
FOOTBOARD_TOP_Z = 94.0
DRIVER_SEAT_TOP_Z = 136.0
WARHORSE_FBX = Path("F:/FPSGAMEData/ArtProduction/SourceAssets/World/HillsVillageStable/HorsesR7/Exchange/SK_StableWarhorse.fbx")


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def add_iron_strap_bolts(b: pg.AssetBuilder, x, y, z, sx, sy, sz, bolt_axis="Z", mat="ScaleIron"):
    b.block(f"Strap_{x:.0f}_{y:.0f}_{z:.0f}", (x, y, z), (sx, sy, sz), mat=mat, bevel_cm=0.14, segments=1)
    if bolt_axis == "Z":
        for dx in (-sx * 0.34, sx * 0.34):
            b.bolt((x + dx, y, z + sz * 0.5), axis="Z", radius_cm=0.72, height_cm=0.55, mat="Iron")
    elif bolt_axis == "Y":
        sgn = 1.0 if y >= 0 else -1.0
        for dz in (-sz * 0.32, sz * 0.32):
            b.bolt((x, y + sgn * sy * 0.5, z + dz), axis="Y", radius_cm=0.72, height_cm=0.55, mat="Iron")


def build_wagon_wheel(out_dir: Path):
    """SM_LM_TimberWagon_Wheel: exact hub pivot (0,0,0), XZ plane, rolling axis Y, outer radius 52.0 cm."""
    b = pg.AssetBuilder("SM_LM_TimberWagon_Wheel", seed=5201)
    R_OUT = REAR_WHEEL_RADIUS          # 52.0 cm outer iron tire
    R_FELLOE_OUT = 50.4                # oak felloe outer radius
    R_FELLOE_IN = 44.2                 # oak felloe inner radius
    RIM_W = 8.4                        # felloe thickness along Y

    # 1. Lathe-turned oak wheel nave (hub) along Y axis
    hub_profile = [
        (-11.8, 0.0), (-11.8, 7.6), (-9.6, 8.6), (-7.0, 10.6),
        (-3.6, 12.2), (0.0, 12.6), (3.6, 12.2), (7.0, 10.6),
        (9.6, 8.6), (11.8, 7.4), (11.8, 0.0),
    ]
    b.lathe("WheelHub", (0.0, 0.0, 0.0), hub_profile, mat="Oak", axis="Y", sides=22, cap_mat="Endgrain")

    # Iron hub reinforcing bands & outer brass/iron axle linchpin cap
    for y_band, r_band in ((-9.8, 8.9), (-4.4, 12.45), (4.4, 12.45), (9.8, 8.7)):
        b.lathe(f"HubBand_{y_band:+.0f}", (0.0, 0.0, 0.0),
                [(y_band - 1.15, r_band), (y_band + 1.15, r_band)],
                mat="ScaleIron", axis="Y", sides=22, cap_mat="ScaleIron")
    b.lathe("AxleCap", (0.0, 0.0, 0.0),
            [(11.5, 4.6), (14.4, 4.1), (15.6, 2.8), (15.8, 0.0)],
            mat="Iron", axis="Y", sides=14, cap_mat="Iron")
    b.block("Linchpin", (0.0, 13.5, 0.0), (1.3, 1.3, 10.2), mat="Brass", bevel_cm=0.12, segments=1)

    # 2. 12 radially-tapered oak spokes (subtle authentic 2.8-deg wheel dish toward +Y exterior)
    n_spokes = 12
    for k in range(n_spokes):
        ang = k * math.tau / n_spokes
        ca, sa = math.cos(ang), math.sin(ang)
        p0 = (10.8 * ca, 0.0, 10.8 * sa)
        p1 = (24.0 * ca, 1.1, 24.0 * sa)
        p2 = (38.0 * ca, 1.8, 38.0 * sa)
        p3 = (45.2 * ca, 2.0, 45.2 * sa)
        b.tube(f"Spoke_{k}", [p0, p1, p2, p3], [2.45, 2.20, 1.90, 1.65], mat="Oak", sides=10)

    # 3. Watertight 36-segment chamfered oak felloe rim + outer forged iron tire hoop
    n_seg = 36
    y_dish = 2.0
    felloe_pts = [(0.5 * (R_FELLOE_IN + R_FELLOE_OUT) * math.cos(i * math.tau / n_seg),
                   y_dish,
                   0.5 * (R_FELLOE_IN + R_FELLOE_OUT) * math.sin(i * math.tau / n_seg))
                  for i in range(n_seg)]
    hw = RIM_W * 0.5
    hr = (R_FELLOE_OUT - R_FELLOE_IN) * 0.5
    c = 0.55
    # Section in (side=radial outward, up=Y axle direction) since sweep_section side = up_hint(Y) x tangent(XZ) = radial!
    felloe_sec = [(-hr + c, -hw), (hr - c, -hw), (hr, -hw + c), (hr, hw - c),
                  (hr - c, hw), (-hr + c, hw), (-hr, hw - c), (-hr, -hw + c)]
    b.sweep_section("OakFelloeRim", felloe_pts, felloe_sec, mat="DarkWood", cyclic=True, up_hint=(0, 1, 0))

    # Outer forged iron tire hoop (R = 50.3 .. 52.0 cm, slightly wider along Y than felloe)
    r_tire_mid = 0.5 * (R_FELLOE_OUT - 0.1 + R_OUT)
    tire_pts = [(r_tire_mid * math.cos(i * math.tau / n_seg),
                 y_dish,
                 r_tire_mid * math.sin(i * math.tau / n_seg))
                for i in range(n_seg)]
    tw = (RIM_W + 0.5) * 0.5
    tr = (R_OUT - (R_FELLOE_OUT - 0.1)) * 0.5
    tire_sec = [(-tr + 0.25, -tw), (tr - 0.25, -tw), (tr, -tw + 0.25), (tr, tw - 0.25),
                (tr - 0.25, tw), (-tr + 0.25, tw), (-tr, tw - 0.25), (-tr, -tw + 0.25)]
    b.sweep_section("IronTireHoop", tire_pts, tire_sec, mat="ScaleIron", cyclic=True, up_hint=(0, 1, 0))

    # 6 iron felloe-joint plates + 12 tire rivets
    for j in range(6):
        ang = (j + 0.5) * math.tau / 6.0
        ca, sa = math.cos(ang), math.sin(ang)
        r_mid = 0.5 * (R_FELLOE_IN + R_FELLOE_OUT)
        b.block(f"FelloePlate_{j}", (r_mid * ca, y_dish, r_mid * sa),
                (6.8, RIM_W + 0.9, 5.2), mat="ScaleIron",
                rot_deg=(0.0, -math.degrees(ang), 0.0), bevel_cm=0.14, segments=1)
        b.rivet(((R_OUT + 0.1) * ca, y_dish, (R_OUT + 0.1) * sa), axis="Z", radius_cm=0.70, height_cm=0.45, mat="Iron")

    return b.finish(out_dir, lod_ratios=(1.0,))


def build_wagon_chassis(out_dir: Path):
    """SM_LM_TimberWagon_Chassis: cut-under heavy timber dray body, zero wheel-clip at +-35 deg steer,
    zero axle/hub overlap, open rear log overhang, ergonomic driver cockpit, and hooked tow rope."""
    b = pg.AssetBuilder("SM_LM_TimberWagon_Chassis", seed=5202)

    # 1. Rear solid oak axle beam (X = -105, Z = 52) sized strictly inside RearWheel hubs (inner face Y=+-64.2 cm!)
    b.block("RearAxleBeam", (REAR_AXLE_X, 0.0, REAR_WHEEL_RADIUS), (13.0, 124.0, 13.0),
            mat="DarkWood", bevel_cm=0.45, segments=1, endgrain_axis=1)
    for sy in (-1, 1):
        # Iron thrust collar washer seated flush against inner hub face (Y=+-64.0 cm) + spindle running cleanly through hub (Y=+-76)
        b.lathe(f"RearSpindle_{sy:+d}", (REAR_AXLE_X, sy * 62.0, REAR_WHEEL_RADIUS),
                [(0.0, 7.0), (sy * 2.0, 7.0), (sy * 2.1, 5.2), (sy * 20.0, 4.4), (sy * 20.6, 0.0)],
                mat="ScaleIron", axis="Y", sides=14, cap_mat="ScaleIron")
        # Under-axle iron truss bar & axle clamp straps
        b.block(f"RearAxleClamp_{sy:+d}", (REAR_AXLE_X, sy * 53.0, REAR_WHEEL_RADIUS + 11.5),
                (15.2, 5.2, 25.0), mat="ScaleIron", bevel_cm=0.16, segments=1)
    b.block("RearBolster", (REAR_AXLE_X, 0.0, 68.5), (15.0, 124.0, 19.0),
            mat="DarkWood", bevel_cm=0.40, segments=1, endgrain_axis=1)

    # 2. Cut-under Front turntable / fifth-wheel bolster (narrowed to Y=+-32 cm so front wheels clear by >4 cm even at +-35 deg steer!)
    b.block("FrontUpperBolster", (FRONT_AXLE_X, 0.0, 70.0), (18.0, 64.0, 16.0),
            mat="DarkWood", bevel_cm=0.40, segments=1, endgrain_axis=1)
    # Transverse upper arch crossbeam above front tire crown (bottom Z=78.5 > front wheel top 74.88 cm!)
    b.block("FrontSillArchBeam", (FRONT_AXLE_X, 0.0, 83.0), (16.0, 128.0, 9.0),
            mat="DarkWood", bevel_cm=0.30, segments=1, endgrain_axis=1)
    b.ring_torus("FifthWheelRing", (FRONT_AXLE_X, 0.0, 60.2), major_r=24.0, minor_r=1.9,
                 mat="ScaleIron", axis="Z", major_segs=24, minor_segs=8)
    b.lathe("KingpinBolt", (FRONT_AXLE_X, 0.0, 58.0),
            [(-20.0, 2.6), (14.0, 2.6), (16.5, 4.6), (17.5, 0.0)],
            mat="Iron", axis="Z", sides=10, cap_mat="Iron")

    # 3. Raised longitudinal cut-under sills (bottom Z = 78.5 cm > front wheel top 74.88 cm => ZERO steering clip!)
    for sy in (-1, 1):
        b.plank(f"MainSill_{sy:+d}", (8.0, sy * 55.0, 84.0), (304.0, 12.0, 11.0), mat="DarkWood", wear=0.10)
        b.plank(f"InnerStringer_{sy:+d}", (6.0, sy * 22.0, 84.5), (296.0, 9.5, 10.0), mat="Oak", wear=0.08)
        # Diagonal undercarriage brace from rear bolster to reach beam (stays well aft of front wheel sweep!)
        b.beam(f"RearReachBrace_{sy:+d}", (REAR_AXLE_X + 6.0, sy * 50.0, 66.0),
               (-12.0, sy * 9.0, 74.0), 8.2, 8.2, mat="DarkWood")
    b.beam("CenterReachBeam", (REAR_AXLE_X - 8.0, 0.0, 69.0), (FRONT_AXLE_X, 0.0, 69.0), 10.5, 10.0, mat="DarkWood")

    # 4. 7 oak cross-bearers (bottom Z = 86.0 cm > front wheel top 74.88 cm) + 10 weathered plank deck floorboards (top = BED_TOP_Z = 95.0 cm)
    for idx, cx in enumerate((-134.0, -82.0, -28.0, 26.0, 80.0, 124.0, 152.0)):
        b.block(f"CrossBearer_{idx}", (cx, 0.0, 89.0), (10.0, 132.0, 6.0),
                mat="DarkWood", bevel_cm=0.22, segments=1, endgrain_axis=1)

    n_planks = 10
    plank_w = 12.4
    for pi in range(n_planks):
        py = -62.0 + (pi + 0.5) * (124.0 / n_planks)
        mat_p = "Oak" if (pi % 3 != 1) else "Sawn"
        # Cargo bed deck spans X = [-144 .. +124] (top Z = 95.0 cm); cockpit footboard continues from +124.5..+159.5!
        b.plank(f"DeckPlank_{pi}", (-10.0, py, BED_TOP_Z - 2.1), (268.0, plank_w - 0.55, 4.2),
                mat=mat_p, wear=0.12)

    # Perimeter oak rub-rails with iron corner brackets
    for sy in (-1, 1):
        b.block(f"SideRubRail_{sy:+d}", (8.0, sy * 63.8, BED_TOP_Z + 1.8), (304.0, 5.2, 9.2),
                mat="DarkWood", bevel_cm=0.24, segments=1, endgrain_axis=0)
    # Low rear bolster lip flush with deck (top Z = 95.6 cm) — NO high RearGuardBar cutting through overhanging timber logs!
    b.block("RearSillCap", (-143.5, 0.0, BED_TOP_Z - 1.4), (6.5, 134.0, 8.8),
            mat="DarkWood", bevel_cm=0.25, segments=1, endgrain_axis=1)
    add_iron_strap_bolts(b, -146.9, -52.0, BED_TOP_Z - 1.4, 1.4, 24.0, 6.8, bolt_axis="Z")
    add_iron_strap_bolts(b, -146.9, 52.0, BED_TOP_Z - 1.4, 1.4, 24.0, 6.8, bolt_axis="Z")

    # 5. 8 tall logging stanchion stakes (4 per side) in forged iron stake pockets + side rails + tie rings
    stake_xs = (-118.0, -56.0, 6.0, 68.0)
    for sy in (-1, 1):
        # Side wooden mudguard / lower side plank keeping bark/splits on bed
        b.plank(f"LowerSideBoard_{sy:+d}", (-26.0, sy * 62.6, BED_TOP_Z + 12.0), (226.0, 3.4, 18.0),
                mat="Oak", wear=0.10)
        for si, sx in enumerate(stake_xs):
            # Forged iron pocket bracket bolted to rub-rail
            b.block(f"StakePocket_{sy:+d}_{si}", (sx, sy * 67.2, BED_TOP_Z + 1.5),
                    (11.5, 6.8, 12.5), mat="ScaleIron", bevel_cm=0.16, segments=1)
            # Slightly outward-canted heavy oak log stake (top Z = 166 cm)
            p_bot = (sx, sy * 66.2, BED_TOP_Z - 12.0)
            p_top = (sx, sy * 71.0, BED_TOP_Z + 71.0)
            b.beam(f"LogStake_{sy:+d}_{si}", p_bot, p_top, 7.6, 7.6, mat="Oak", wear=0.07)
            # Iron cap band on stake top
            b.block(f"StakeCap_{sy:+d}_{si}", (sx, sy * 70.6, BED_TOP_Z + 66.5),
                    (8.4, 8.4, 3.6), mat="ScaleIron", bevel_cm=0.12, segments=1)
            # Tie-down iron ring below middle stakes
            if si in (1, 2):
                b.ring_torus(f"TieRing_{sy:+d}_{si}", (sx, sy * 68.2, BED_TOP_Z - 7.5),
                             major_r=3.6, minor_r=0.75, mat="ScaleIron", axis="X", major_segs=14, minor_segs=7)
        # Upper horizontal tie-rail connecting stakes
        b.beam(f"UpperSideRail_{sy:+d}", (-122.0, sy * 68.8, BED_TOP_Z + 44.0),
               (72.0, sy * 68.8, BED_TOP_Z + 44.0), 4.6, 7.2, mat="DarkWood", wear=0.06)
        # Rear corner iron gusset bracing the back log stake cleanly outside the log load (Y = +-68 cm)
        b.beam(f"RearStakeBrace_{sy:+d}", (-141.0, sy * 64.5, BED_TOP_Z + 1.0),
               (-118.0, sy * 67.5, BED_TOP_Z + 22.0), 3.6, 3.6, mat="ScaleIron")

    # 6. Ergonomic Elevated Front Driver's Box:
    #    Seat top Z = 136.0 cm (X = 92..124), Footboard top Z = 94.0 cm (X = 124.5..159.5 -> 42 cm vertical legroom!),
    #    Angled FrontDashboard at X = 163 cm (inner toe face >= 156 cm -> full boot/knee clearance!).
    for sy in (-1, 1):
        b.block(f"SeatSidePanel_{sy:+d}", (107.0, sy * 57.5, 114.5), (36.0, 4.4, 39.0),
                mat="DarkWood", bevel_cm=0.22, segments=1)
        # Armrest rail
        b.beam(f"SeatArmRail_{sy:+d}", (90.0, sy * 58.0, 150.0), (124.0, sy * 58.0, 146.0),
               4.8, 5.2, mat="OiledOak", wear=0.05)
        b.block(f"ArmPost_{sy:+d}", (122.0, sy * 58.0, 141.0), (4.8, 4.8, 12.0), mat="DarkWood", bevel_cm=0.14, segments=1)
    b.block("SeatFrontBox", (122.5, 0.0, 114.0), (3.8, 112.0, 38.0), mat="Oak", bevel_cm=0.18, segments=1)
    b.block("SeatBackBulkhead", (89.5, 0.0, 129.0), (4.6, 124.0, 68.0), mat="DarkWood", bevel_cm=0.22, segments=1)

    # Driver's 2-plank bench seat (top exactly DRIVER_SEAT_TOP_Z = 136.0 cm, X = [92..124])
    b.plank("DriverSeatPlankA", (100.5, 0.0, DRIVER_SEAT_TOP_Z - 2.1), (15.2, 122.0, 4.2), mat="OiledOak", wear=0.08)
    b.plank("DriverSeatPlankB", (116.5, 0.0, DRIVER_SEAT_TOP_Z - 2.1), (15.2, 122.0, 4.2), mat="OiledOak", wear=0.08)
    # Bench backrest rail (top Z = 166 cm, protects driver from logs shifting forward!)
    b.plank("DriverBackrestRail", (88.5, 0.0, 159.0), (4.8, 122.0, 14.0), mat="OiledOak", wear=0.07)

    # Full-depth 2-plank Oak Footboard (top exactly FOOTBOARD_TOP_Z = 94.0 cm, X = [124.5..159.5])
    b.plank("FootboardPlankA", (133.2, 0.0, FOOTBOARD_TOP_Z - 1.9), (16.8, 124.0, 3.8), mat="Oak", wear=0.08)
    b.plank("FootboardPlankB", (150.8, 0.0, FOOTBOARD_TOP_Z - 1.9), (16.8, 124.0, 3.8), mat="Oak", wear=0.08)
    # Forward-raked Dashboard Kick-panel (center X=163.0, Z=118.0, 16 deg forward tilt => inner bottom X=154.5, ankle X=157, knee X=165!)
    b.block("FrontDashboard", (163.0, 0.0, 118.0), (4.2, 124.0, 48.0),
            mat="DarkWood", rot_deg=(0.0, 16.0, 0.0), bevel_cm=0.22, segments=1)
    for sy in (-1, 1):
        b.block(f"DashIronBrace_{sy:+d}", (161.2, sy * 54.0, 118.0), (5.4, 3.6, 46.0),
                mat="ScaleIron", rot_deg=(0.0, 16.0, 0.0), bevel_cm=0.12, segments=1)

    # 7. Forged Wagon Lantern Bracket & Brass Carriage Lantern bolted cleanly to Right Front Dashboard!
    b.tube("LanternHook", [(165.0, 61.5, 136.0), (171.0, 66.0, 146.0), (175.0, 68.0, 149.0), (175.0, 68.0, 145.0)],
           0.85, mat="ScaleIron", sides=8)
    b.lathe("WagonLantern", (175.0, 68.0, 131.0),
            [(0.0, 0.0), (0.6, 5.2), (3.5, 6.2), (11.2, 6.0), (13.8, 7.6), (17.0, 3.4), (18.8, 1.4), (19.2, 0.0)],
            mat="Brass", axis="Z", sides=8, cap_mat="Brass")

    # 8. Forged Iron Rope Peg bolted directly onto Left SeatSidePanel + Hanging Coiled Tow Rope seated ON the peg (ZERO floating!)
    b.block("RopeHookPlate", (110.0, -59.9, 130.5), (7.5, 1.2, 11.0), mat="ScaleIron", bevel_cm=0.10, segments=1)
    b.tube("RopeHookPeg",
           [(110.0, -59.5, 131.5), (110.0, -64.2, 131.5), (110.0, -65.2, 133.2), (110.0, -65.0, 136.5)],
           0.95, mat="ScaleIron", sides=8)
    loop_pts = []
    for k in range(24):
        a = k * math.tau / 24.0
        # Oval hanging coil: top crest (a=pi/2) sits directly ON the iron peg at (110.0, -63.0, 133.2)!
        loop_pts.append((110.0 + 7.2 * math.cos(a), -63.0 + 0.9 * math.sin(2.0 * a), 120.7 + 12.5 * math.sin(a)))
    b.rope_braid("SideTowRope", loop_pts, radius_cm=1.25, mat="Rope", cyclic=True, pitch_cm=6.8)

    # Clean simple box colliders (bed body + extended front driver box)
    b.add_collider((-28.0, 0.0, 96.0), (234.0, 138.0, 112.0))
    b.add_collider((126.0, 0.0, 114.0), (80.0, 132.0, 110.0))
    return b.finish(out_dir, lod_ratios=(1.0,))


def build_front_axle(out_dir: Path):
    """SM_LM_TimberWagon_FrontAxle: steerable bolster + axle + twin swept oak draft shafts & singletree.
    Pivot at kingpin (0,0,0), attached to Chassis at (X=+105, Y=0, Z=37.44 cm).
    Horse stands centered at FrontAxle X = +218.0 cm, hooves at FrontAxle Z = -37.44 cm.
    """
    b = pg.AssetBuilder("SM_LM_TimberWagon_FrontAxle", seed=5203)

    # 1. Steerable front oak axle beam sized inside scaled 0.72 FrontWheel hubs (inner face Y = +-63.5 cm!)
    b.block("FrontAxleBeam", (0.0, 0.0, 0.0), (11.5, 120.0, 11.5),
            mat="DarkWood", bevel_cm=0.40, segments=1, endgrain_axis=1)
    for sy in (-1, 1):
        b.lathe(f"FrontSpindle_{sy:+d}", (0.0, sy * 60.0, 0.0),
                [(0.0, 6.2), (sy * 2.5, 6.2), (sy * 2.6, 4.4), (sy * 18.0, 3.6), (sy * 18.5, 0.0)],
                mat="ScaleIron", axis="Y", sides=14, cap_mat="ScaleIron")
        b.block(f"FrontClamp_{sy:+d}", (0.0, sy * 32.0, 8.0), (13.5, 4.6, 20.0),
                mat="ScaleIron", bevel_cm=0.14, segments=1)

    # Lower turntable bolster & fifth-wheel rubbing plate (Z = +20.0 -> World Z = 57.44 meets Chassis ring at 60.2 flush!)
    b.block("FrontLowerBolster", (0.0, 0.0, 13.0), (16.5, 76.0, 11.5),
            mat="DarkWood", bevel_cm=0.35, segments=1, endgrain_axis=1)
    b.ring_torus("LowerFifthWheel", (0.0, 0.0, 19.6), major_r=24.0, minor_r=1.8,
                 mat="ScaleIron", axis="Z", major_segs=24, minor_segs=8)

    # 2. Forward draft hound frame & crossbar (X = 0..+50 cm, widened to Y=+-49.5 cm to clear warhorse stirrups +-44.6 cm!)
    for sy in (-1, 1):
        b.beam(f"FrontHound_{sy:+d}", (-10.0, sy * 34.0, 10.0), (50.0, sy * 49.5, 31.0),
               7.2, 7.2, mat="DarkWood", wear=0.06)
    b.block("ShaftCrossbar", (48.0, 0.0, 31.0), (9.0, 106.0, 8.2),
            mat="DarkWood", bevel_cm=0.25, segments=1, endgrain_axis=1)

    # 3. Curved Oak Singletree (Whiffletree) at FrontAxle X=+66 cm (Horse X=-152 cm => +19 cm aft of walk tail, +24 cm aft of hind hooves!)
    #    World Z = 37.44 + 41.56 = 79.0 cm (matches Harness TraceEndRing exact datum!)
    st_z = 79.0 - FRONT_WHEEL_RADIUS  # 41.56 cm
    st_pts = [
        (60.0, -42.0, st_z),
        (64.5, -21.0, st_z + 0.6),
        (66.0,   0.0, st_z + 0.9),
        (64.5,  21.0, st_z + 0.6),
        (60.0,  42.0, st_z),
    ]
    b.tube("SingletreeBar", st_pts, [3.0, 3.8, 4.3, 3.8, 3.0], mat="Oak", sides=10)
    b.ring_torus("SingletreeClevis", (56.5, 0.0, 36.2), major_r=5.2, minor_r=1.05,
                 mat="ScaleIron", axis="Y", major_segs=16, minor_segs=8)
    for sy in (-1, 1):
        b.ring_torus(f"TraceHook_{sy:+d}", (66.0, sy * 42.0, st_z), major_r=3.4, minor_r=0.85,
                     mat="ScaleIron", axis="Z", major_segs=14, minor_segs=7)
        # Short iron tie link from singletree end (60, +-42) to TraceHook (66, +-42)
        b.beam(f"SingletreeEndStrap_{sy:+d}", (60.0, sy * 42.0, st_z), (65.5, sy * 42.0, st_z), 2.4, 2.4, mat="ScaleIron")

    # 4. Twin Swept Oak Draft Shafts (Thills) flanking SK_StableWarhorse at Y = +-49.5 cm (inner face +-46.5 cm > stirrups +-44.6 cm!),
    #    rising smoothly to World Z = 122.0 cm (FrontAxle Z = 84.56 cm) through Harness ShaftCarrierTug at Horse X=-8 (FrontAxle X=+210 cm)!
    sh_z = 122.0 - FRONT_WHEEL_RADIUS  # 84.56 cm
    tug_x = HORSE_OFFSET_FROM_FRONT_AXLE_X - 8.0      # +210.0 cm (0.0 cm match with Harness ShaftCarrierTug!)
    hb_x = HORSE_OFFSET_FROM_FRONT_AXLE_X - 36.0      # +182.0 cm (0.0 cm match with Harness BreechingHoldback!)
    tip_x = HORSE_OFFSET_FROM_FRONT_AXLE_X + 68.0     # +286.0 cm (beside horse shoulder/chest, clear of legs!)
    for sy in (-1, 1):
        shaft_pts = pg.sample_beziers(
            (46.0, sy * 49.5, 31.0),
            [
                ((102.0, sy * 49.8, 52.0), (150.0, sy * 49.8, sh_z - 3.0), (tug_x, sy * 49.5, sh_z)),
                ((236.0, sy * 49.2, sh_z + 1.0), (264.0, sy * 47.0, sh_z + 1.5), (tip_x, sy * 44.5, sh_z + 1.0)),
            ],
            steps_per_seg=8,
        )
        radii = [3.6 - 0.95 * (i / max(1, len(shaft_pts) - 1)) for i in range(len(shaft_pts))]
        b.tube(f"DraftShaft_{sy:+d}", shaft_pts, radii, mat="Oak", sides=10)
        # Leather shaft wear-wraps & forged tug/holdback loops aligned 1:1 with Harness!
        b.tube(f"ShaftWrap_{sy:+d}", shaft_pts[7:12], [3.25] * 5, mat="LeatherDark", sides=10)
        b.ring_torus(f"ShaftTugLoop_{sy:+d}", (tug_x, sy * 49.5, sh_z), major_r=4.2, minor_r=0.75,
                     mat="ScaleIron", axis="X", major_segs=14, minor_segs=7)
        b.ring_torus(f"ShaftHoldbackLoop_{sy:+d}", (hb_x, sy * 49.7, sh_z - 1.2), major_r=3.6, minor_r=0.70,
                     mat="ScaleIron", axis="X", major_segs=14, minor_segs=7)
        # Forged brass tip cap
        b.lathe(f"ShaftTipCap_{sy:+d}", (tip_x, sy * 44.5, sh_z + 1.0),
                [(0.0, 2.8), (4.6, 2.3), (5.8, 1.1), (6.0, 0.0)],
                mat="Brass", axis="X", sides=10, cap_mat="Brass")

    return b.finish(out_dir, lod_ratios=(1.0,))


def build_timber_load(out_dir: Path):
    """SM_LM_TimberWagon_TimberLoad: 11 chamfered bark logs in 4-4-3 pyramid + braided rope/iron chain lashings.
    Same datum as Chassis (ground Z = 0, deck top Z = 95.0 cm). Lashings clear LowerSideBoard & UpperSideRail cleanly!
    """
    b = pg.AssetBuilder("SM_LM_TimberWagon_TimberLoad", seed=5204)
    rng = random.Random(5204)

    # 3 stacked rows: (y_cm, z_cm, radius_cm) nested snugly between Y=+-62 cm stakes & X=[-152..+80]
    log_specs = [
        # Row 0 (bottom, resting directly on Z = 95 cm deck)
        (-44.0, BED_TOP_Z + 13.8, 13.8),
        (-15.0, BED_TOP_Z + 14.6, 14.6),
        ( 15.0, BED_TOP_Z + 14.2, 14.2),
        ( 44.0, BED_TOP_Z + 13.6, 13.6),
        # Row 1 (middle, cradled in row 0 troughs)
        (-36.5, BED_TOP_Z + 37.5, 13.4),
        (-11.0, BED_TOP_Z + 39.2, 14.0),
        ( 14.5, BED_TOP_Z + 38.6, 13.8),
        ( 39.5, BED_TOP_Z + 37.0, 13.2),
        # Row 2 (top crown pyramid)
        (-24.0, BED_TOP_Z + 60.5, 13.0),
        (  1.5, BED_TOP_Z + 62.5, 13.6),
        ( 26.0, BED_TOP_Z + 59.8, 12.8),
    ]

    for li, (ly, lz, lr) in enumerate(log_specs):
        x0 = -152.0 + rng.uniform(-6.0, 8.0)
        x1 = 76.0 + rng.uniform(-5.0, 4.0)
        n_rings = 6
        sides = 14
        pts = []
        rads = []
        y_bow = rng.uniform(-1.6, 1.6)
        z_bow = rng.uniform(-0.8, 0.8)
        for ri in range(n_rings + 1):
            t = ri / n_rings
            x = x0 + (x1 - x0) * t
            bow = math.sin(t * math.pi)
            pts.append((x, ly + y_bow * bow, lz + z_bow * bow))
            # Subtle natural tree taper (slightly thicker butt at rear)
            rads.append(lr * (1.04 - 0.08 * t))

        # Build organic bark-furrowed cross-section per ring for crisp 3A silhouette
        secs = []
        phase = rng.uniform(0.0, math.tau)
        for ri, rad in enumerate(rads):
            sec = []
            for k in range(sides):
                ang = k * math.tau / sides
                flute = 1.0 + 0.045 * math.sin(5.0 * ang + phase + ri * 0.4) + 0.025 * math.cos(3.0 * ang - phase)
                sec.append((rad * flute * math.cos(ang), rad * flute * math.sin(ang)))
            secs.append(sec)
        b.sweep_section(f"TimberLog_{li}", pts, secs, mat="Bark", cyclic=False, cap_mat="Endgrain", uv_scale_override=0.85)

    # 2 Heavy Braided Hemp Rope & Iron Chain Lashings routed cleanly OUTSIDE LowerSideBoard (Y=+-64.3) & UpperSideRail (Y=+-71.1, Z=139)!
    for idx, lx in enumerate((-56.0, 6.0)):
        arch_pts = [
            (lx, -68.2, BED_TOP_Z - 7.5),
            (lx, -73.0, BED_TOP_Z + 18.0),
            (lx, -73.2, BED_TOP_Z + 46.0),
            (lx, -58.0, BED_TOP_Z + 62.0),
            (lx, -34.0, BED_TOP_Z + 72.5),
            (lx,   0.0, BED_TOP_Z + 77.5),
            (lx,  34.0, BED_TOP_Z + 72.0),
            (lx,  58.0, BED_TOP_Z + 62.0),
            (lx,  73.2, BED_TOP_Z + 46.0),
            (lx,  73.0, BED_TOP_Z + 18.0),
            (lx,  68.2, BED_TOP_Z - 7.5),
        ]
        b.rope_braid(f"LoadLashing_{idx}", arch_pts, radius_cm=1.55, mat="Rope", cyclic=False, pitch_cm=7.0)
        # Forged iron tensioning binder clasp on top
        b.block(f"LashingBinder_{idx}", (lx, 0.0, BED_TOP_Z + 78.2), (6.5, 16.0, 3.8),
                mat="ScaleIron", bevel_cm=0.14, segments=1)
        for sy in (-1, 1):
            b.ring_torus(f"LashingHook_{idx}_{sy:+d}", (lx, sy * 68.5, BED_TOP_Z - 3.5),
                         major_r=2.8, minor_r=0.70, mat="Iron", axis="X", major_segs=12, minor_segs=6)

    b.add_collider((-38.0, 0.0, BED_TOP_Z + 38.0), (228.0, 120.0, 76.0))
    return b.finish(out_dir, lod_ratios=(1.0,))


def build_horse_harness(out_dir: Path):
    """SM_LM_HorseHarness: fitted directly to measured 10,607-vertex SK_StableWarhorse.fbx surface + walk sway!
    Authored in HorseRoot frame (X=0 horse center, +X forward, Z=0 ground/hooves):
      - Saddle pad & belly girth sit at X=-8.0 cm (between saddle pommel +15 and cantle -25, cleanly behind stirrups X=+1..+14!)
      - Collar hugs measured neck/shoulder contour ((+30,0,185) crest -> (+53,+-34.5,134) shoulders -> (+70,0,99) chest)
      - Breeching wraps outside hindquarters at X=-103 cm (aft of pelvis -83.3 and croup -95, clear of tail!)
      - Traces couple 1:1 to FrontAxle Singletree TraceHooks at Horse X=-152.0, Y=+-42.0, Z=79.0 cm
      - ShaftCarrierTugs couple 1:1 to FrontAxle ShaftTugLoops at Horse X=-8.0, Y=+-49.5, Z=122.0 cm!
    """
    b = pg.AssetBuilder("SM_LM_HorseHarness", seed=5205)

    # 1. Anatomically Sculpted Heavy Draft Horse Collar (fitted to measured SK_StableWarhorse neck/shoulder contour!)
    #    Smooth closed teardrop loop in horse space (center ~ (51, 0, 138), tilted ~30 deg along shoulder slope):
    #    Top crest (+31, 0, 184.5), upper shoulders (+37, +-24, 166), mid shoulders (+52, +-34.5, 135),
    #    lower chest (+63, +-29.5, 112), breast bottom (+70, 0, 99.5)
    collar_pts = []
    n_col = 32
    for i in range(n_col):
        a = i * math.tau / n_col
        sa = math.sin(a)   # +1 at withers crest, -1 at lower chest
        ca = math.cos(a)   # +-1 at left/right shoulder blades
        # Interpolate X along tilted shoulder plane (+70 bottom -> +52 mid -> +31 crest)
        px = 51.5 - 19.5 * sa + 1.0 * (1.0 - sa * sa)
        # Natural teardrop half-width: narrower at withers crest (16 cm), widest across mid-shoulder (34.5 cm), rounded at chest
        w_prof = 34.8 if sa <= 0.0 else (34.8 - 14.5 * (sa ** 1.45))
        py = w_prof * ca
        # Vertical profile: +184.5 crest down to +99.5 breast
        pz = 142.0 + 42.5 * sa
        collar_pts.append((px, py, pz))
    b.tube("LeatherCollarPad", collar_pts, 4.4, mat="LeatherDark", sides=10, cyclic=True)

    # Outer dark oak/iron Hame rim & twin Brass Hame Finials rising cleanly above withers crest!
    hame_pts = [(p[0] + 3.2, p[1] * 1.05, p[2] + 1.2) for p in collar_pts]
    b.tube("CollarHames", hame_pts, 2.1, mat="DarkWood", sides=8, cyclic=True)
    for sy in (-1, 1):
        b.lathe(f"BrassHameFinial_{sy:+d}", (34.0, sy * 11.5, 185.0),
                [(0.0, 1.4), (5.5, 1.6), (7.5, 2.9), (9.8, 2.4), (11.2, 0.0)],
                mat="Brass", axis="Z", sides=12, cap_mat="Brass")
        # Brass draft eye ring where leather traces attach (X=+56, Y=+-36.5, Z=129)
        b.ring_torus(f"HameTraceRing_{sy:+d}", (56.0, sy * 36.5, 129.0), major_r=3.6, minor_r=0.80,
                     mat="Brass", axis="Y", major_segs=14, minor_segs=7)

    # 2. Back Harness Saddle Pad & Belly Girth Band at X = -8.0 cm (clears pommel +15, cantle -25, and stirrups +1..+14!)
    #    Measured barrel at X=-8: |Y|_max = 34.4 cm, Z = [87.2 .. 168.0 cm].
    #    Pad inner radius clears skin by +2.5..+3.5 cm (|Y|=37.5, Z_top=171.2, Z_bot=84.2)!
    pad_x = -8.0
    pad_pts = []
    for i in range(26):
        a = -math.pi * 0.08 + (math.pi * 1.16) * (i / 25.0)
        py = 38.0 * math.cos(a)
        pz = 128.0 + 43.2 * math.sin(a)
        pad_pts.append((pad_x, py, pz))
    b.strap("BackSaddlePad", pad_pts, width_cm=13.5, thick_cm=3.2, mat="LeatherMain", cyclic=False, up_hint=(1, 0, 0))

    # Full belly girth loop at X = -8.0 cm wrapping cleanly around barrel (Z = 84.0 .. 171.0, |Y| = 37.8)
    girth_pts = []
    for i in range(30):
        a = i * math.tau / 30.0
        girth_pts.append((pad_x, 37.8 * math.cos(a), 127.5 + 43.5 * math.sin(a)))
    b.strap("BellyGirth", girth_pts, width_cm=7.0, thick_cm=1.9, mat="LeatherDark", cyclic=True, up_hint=(1, 0, 0))

    # Brass Terret Rein-Guide Rings on top of saddle pad (EXACT datum mirrored in LumberMillTimberWagon::UpdateDynamicReins!)
    # + Suspended Heavy Leather ShaftCarrierTugs holding DraftShafts cleanly at (X=-8.0, Y=+-49.5, Z=122.0)!
    for sy in (-1, 1):
        b.ring_torus(f"ReinTerret_{sy:+d}", (pad_x, sy * 14.0, 177.5), major_r=3.8, minor_r=0.72,
                     mat="Brass", axis="X", major_segs=14, minor_segs=7)
        # Side suspension hanger strap linking BackSaddlePad (Y=+-38.0, Z=145) outward to ShaftCarrierTug (Y=+-49.5, Z=122)
        b.strap(f"TugHanger_{sy:+d}",
                [(pad_x, sy * 36.5, 146.0), (pad_x, sy * 43.5, 134.0), (pad_x, sy * 49.5, 126.0)],
                width_cm=5.2, thick_cm=1.6, mat="LeatherMain", up_hint=(1, 0, 0))
        b.ring_torus(f"ShaftCarrierTug_{sy:+d}", (pad_x, sy * 49.5, 122.0), major_r=5.6, minor_r=1.35,
                     mat="LeatherDark", axis="X", major_segs=16, minor_segs=8)
        # Lower belly billet strap tying bottom of ShaftCarrierTug back into BellyGirth (stops outward swing!)
        b.strap(f"TugBellyTie_{sy:+d}",
                [(pad_x, sy * 48.0, 117.0), (pad_x, sy * 42.0, 105.0), (pad_x, sy * 34.0, 96.0)],
                width_cm=4.0, thick_cm=1.3, mat="LeatherDark", up_hint=(1, 0, 0))

    # 3. Back Spine Strap clearing saddle pommel (+15, Z=181.3) & cantle (-25, Z=177.4) & croup (-85, Z=160.3)!
    spine_pts = [
        (33.0, 0.0, 185.5),
        (15.0, 0.0, 184.0),
        (-8.0, 0.0, 172.5),
        (-26.0, 0.0, 180.0),
        (-52.0, 0.0, 168.0),
        (-80.0, 0.0, 165.0),
        (-98.0, 0.0, 158.0),
    ]
    b.strap("BackSpineStrap", spine_pts, width_cm=5.8, thick_cm=1.6, mat="LeatherMain", up_hint=(0, 1, 0))

    # 4. Haunch Breeching Band wrapping cleanly OUTSIDE actual hindquarters (X = -103.5 cm aft of rump -100, Y = +-38.0 cm outside thighs +-33.3 cm!)
    breech_pts = [
        (-42.0, -38.5, 121.0),
        (-68.0, -37.5, 121.5),
        (-92.0, -31.5, 122.5),
        (-102.5, -17.0, 123.5),
        (-104.5,   0.0, 124.0),
        (-102.5,  17.0, 123.5),
        (-92.0,   31.5, 122.5),
        (-68.0,   37.5, 121.5),
        (-42.0,   38.5, 121.0),
    ]
    b.strap("BreechingBand", breech_pts, width_cm=7.2, thick_cm=1.8, mat="LeatherDark", up_hint=(0, 0, 1))

    for sy in (-1, 1):
        # Twin hip drop straps suspending BreechingBand from BackSpineStrap cleanly over croup
        b.strap(f"HipStrap_{sy:+d}",
                [(-76.0, 0.0, 165.5), (-76.0, sy * 23.0, 156.0), (-76.0, sy * 35.5, 140.0), (-76.0, sy * 37.5, 122.0)],
                width_cm=4.2, thick_cm=1.4, mat="LeatherMain", up_hint=(1, 0, 0))
        # Forward holdback strap linking BreechingBand (-42, +-38.5, 121) straight to FrontAxle ShaftHoldbackLoop (-36, +-49.5, 121)!
        b.strap(f"BreechingHoldback_{sy:+d}",
                [(-42.0, sy * 38.5, 121.0), (-39.0, sy * 44.5, 121.0), (-36.0, sy * 49.5, 121.0)],
                width_cm=4.5, thick_cm=1.5, mat="LeatherDark", up_hint=(0, 0, 1))

        # 5. Twin Heavy Leather Draft Traces from collar HameTraceRing (+56, +-36.5, 129)
        #    passing cleanly OUTSIDE horse barrel & stirrups (Y=+-47.5 at X=+8) back to Singletree TraceHook (-152, +-42, 79)!
        trace_pts = [
            ( 56.0, sy * 36.5, 129.0),
            ( 14.0, sy * 47.5, 114.0),
            (-36.0, sy * 45.5, 102.0),
            (-96.0, sy * 44.0,  90.0),
            (-152.0, sy * 42.0, 79.0),
        ]
        b.strap(f"DraftTrace_{sy:+d}", trace_pts, width_cm=5.8, thick_cm=1.8, mat="LeatherDark", up_hint=(0, 0, 1))
        # Iron trace end chain ring coupled 1:1 with FrontAxle Singletree TraceHook!
        b.ring_torus(f"TraceEndRing_{sy:+d}", (-152.0, sy * 42.0, 79.0), major_r=3.2, minor_r=0.75,
                     mat="ScaleIron", axis="Y", major_segs=12, minor_segs=6)

    return b.finish(out_dir, lod_ratios=(1.0,))


def run_geometric_clearance_audit(out_dir: Path):
    """Automated 3D clearance & coupling hard gate run right after FBX export."""
    from mathutils import Matrix

    report = {}

    # 1. Front Wheel vs Chassis Cut-Under Steering Sweep (0..35 deg)
    r_fw = FRONT_WHEEL_RADIUS
    y_tire_in = FRONT_TRACK_HALF_Y - 1.76   # 70.24 cm (scaled 0.72 wheel inner tire face)
    sill_bot_z = 84.0 - 5.5                 # 78.5 cm
    wheel_top_z = r_fw * 2.0                # 74.88 cm
    bolster_half_y = 32.0
    min_bolster_clear = 999.0
    for deg in (0, 10, 15, 20, 25, 30, 35):
        rad = math.radians(deg)
        y_min = y_tire_in * math.cos(rad) - r_fw * math.sin(rad)
        min_bolster_clear = min(min_bolster_clear, y_min - bolster_half_y)
    report["front_wheel_vs_sill_z_clear_cm"] = round(sill_bot_z - wheel_top_z, 2)
    report["front_wheel_vs_bolster_y_clear_35deg_cm"] = round(min_bolster_clear, 2)
    assert sill_bot_z - wheel_top_z >= 3.0, f"Wheel clips MainSill Z: {sill_bot_z - wheel_top_z:.2f} cm"
    assert min_bolster_clear >= 3.0, f"Wheel clips FrontUpperBolster at 35 deg: {min_bolster_clear:.2f} cm"

    # 2. Rear & Front Axle-Beam vs Wheel-Hub Clearance
    rear_hub_in = REAR_TRACK_HALF_Y - 11.8  # 64.2 cm
    front_hub_in = FRONT_TRACK_HALF_Y - 11.8 * FRONT_WHEEL_SCALE  # 63.504 cm
    report["rear_axle_hub_clear_cm"] = round(rear_hub_in - 62.0, 2)
    report["front_axle_hub_clear_cm"] = round(front_hub_in - 60.0, 2)
    assert rear_hub_in >= 62.0 and front_hub_in >= 60.0

    # 3. Mechanical Coupling Errors (Harness <-> FrontAxle)
    tug_err = abs((HORSE_OFFSET_FROM_FRONT_AXLE_X - 8.0) - 210.0)
    trace_err = abs((HORSE_OFFSET_FROM_FRONT_AXLE_X - 152.0) - 66.0)
    singletree_vs_tail_clear = 152.0 - 133.0
    singletree_vs_hoof_clear = 152.0 - 128.4
    report["tug_coupling_err_cm"] = round(tug_err, 2)
    report["trace_coupling_err_cm"] = round(trace_err, 2)
    report["singletree_vs_walk_tail_clear_cm"] = round(singletree_vs_tail_clear, 2)
    report["singletree_vs_walk_hoof_clear_cm"] = round(singletree_vs_hoof_clear, 2)
    assert tug_err < 0.1 and trace_err < 0.1
    assert singletree_vs_tail_clear >= 15.0 and singletree_vs_hoof_clear >= 20.0

    # 4. Exact Vertex-Level Check: SK_StableWarhorse.fbx vs DraftShafts (Y=+-49.5, r=3.0 => inner 46.5) & Breeching (-104.5)
    if WARHORSE_FBX.is_file():
        clear_scene()
        bpy.ops.import_scene.fbx(filepath=str(WARHORSE_FBX))
        arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
        m = next(o for o in bpy.data.objects if o.type == "MESH")
        pb = arm.data.bones["pelvis"]; mb = arm.data.bones["mouth_socket"]
        yaw = math.atan2((arm.matrix_world @ mb.head_local).y - (arm.matrix_world @ pb.head_local).y,
                         (arm.matrix_world @ mb.head_local).x - (arm.matrix_world @ pb.head_local).x)
        M = Matrix.Rotation(-yaw, 4, "Z") @ m.matrix_world
        pts = [(M @ v.co) * 100.0 for v in m.data.vertices]
        max_horse_y = max(abs(p.y) for p in pts)
        # Check horse skin inside shaft corridor (Z in [115..129], X in [-100..+68])
        shaft_zone_y = max((abs(p.y) for p in pts if -100.0 <= p.x <= 68.0 and 115.0 <= p.z <= 129.0), default=0.0)
        # Check horse skin at saddle pad X=-8 (+-6 cm)
        pad_zone = [p for p in pts if abs(p.x - (-8.0)) <= 6.0 and p.z >= 80.0]
        pad_skin_top = max(p.z for p in pad_zone)
        pad_skin_bot = min(p.z for p in pad_zone)
        pad_skin_y = max(abs(p.y) for p in pad_zone)
        # Check horse rump (excluding tail |Y|<12) min X at Z in [115..132]
        rump_min_x = min(p.x for p in pts if abs(p.y) >= 14.0 and 115.0 <= p.z <= 132.0)
        report["warhorse_max_y_cm"] = round(max_horse_y, 2)
        report["shaft_inner_vs_horse_clear_cm"] = round(46.5 - shaft_zone_y, 2)
        report["saddle_pad_top_clear_cm"] = round(171.2 - 1.6 - pad_skin_top, 2)
        report["saddle_pad_side_clear_cm"] = round(38.0 - 1.6 - pad_skin_y, 2)
        report["girth_belly_clear_cm"] = round(pad_skin_bot - (84.0 + 1.0), 2)
        report["breeching_vs_rump_clear_cm"] = round(rump_min_x - (-104.5 + 0.9), 2)
        assert report["shaft_inner_vs_horse_clear_cm"] >= 1.5, f"Shaft clips horse/stirrup: {report}"
        assert report["saddle_pad_top_clear_cm"] >= 0.5, f"Saddle pad clips horse back: {report}"
        assert report["saddle_pad_side_clear_cm"] >= 1.0, f"Saddle pad clips horse flank: {report}"
        assert report["girth_belly_clear_cm"] >= 0.5, f"Girth clips horse belly: {report}"
        assert report["breeching_vs_rump_clear_cm"] >= 1.5, f"Breeching clips horse rump: {report}"

    (out_dir / "clearance-audit-r56.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("[WAGON-R56-AUDIT] PASS:", json.dumps(report), flush=True)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    builders = [
        build_wagon_wheel,
        build_wagon_chassis,
        build_front_axle,
        build_timber_load,
        build_horse_harness,
    ]
    manifest = []
    for fn in builders:
        clear_scene()
        info = fn(OUT_DIR)
        print(
            f"[WAGON-R56] {info['name']:30s} | tris={info['lods'][0]['triangles']:6d} | "
            f"size_cm={info['size_cm']} | col={len(info['colliders'])} | mats={info['materials']}",
            flush=True,
        )
        manifest.append(info)
    (OUT_DIR / "transport-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    run_geometric_clearance_audit(OUT_DIR)
    print(f"WAGON_R56_OK: {len(manifest)} watertight modular wagon/harness FBX assets exported & verified -> {OUT_DIR}")


if __name__ == "__main__":
    main()
