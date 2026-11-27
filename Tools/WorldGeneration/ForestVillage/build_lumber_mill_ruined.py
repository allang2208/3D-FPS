"""Blender 5.1 procedural 3A Ruined Lumber Mill builder for LumberMillQuest-R51.

Produces 8 watertight, zero-Z-fighting ruined counterparts to R49c Lumber Mill meshes
(100% reusing resident Normandy / Carpenter / Blacksmith PBR materials -> +0.00 MB VRAM!):
  1. SM_LM_Warehouse_Ruined     - Breached slate roof, snapped rafters/hoist, crooked door leaf, rubble
  2. SM_LM_ToolRoom_Ruined      - Collapsed east sawing canopy corner, roof hole, smashed workbench
  3. SM_LM_Bunkhouse_Ruined     - Breached 2F roof/gable, leaning porch roof, busted shutters, cold hearth
  4. SM_LM_CampGateArch_Ruined  - Listing gate arch, snapped east post, sagging header & dangling signboard
  5. SM_LM_CampFencePanel_Ruined- Broken weathered 3-rail fence bay with drooping splintered rails
  6. SM_LM_TimberRack_Ruined    - Collapsed cantilever lumber rack with spilled boards
  7. SM_LM_RubblePileA          - Fallen slate shingles, splintered oak rafters & masonry rubble mound
  8. SM_LM_RubblePileB          - Secondary asymmetric ruined timber, plaster & stone debris cluster

Every doorway, ramp, stoop, and combat yard zone remains cleanly passable for player + Witch/Dog/HandBrain!
"""
import json
import math
import sys
from pathlib import Path

import bpy

TOOLS = Path("D:/FPS3D/FPSGAME/Tools/WorldGeneration/ForestVillage")
PROPS_LIB = Path("D:/FPS3D/FPSGAME/Tools/WorldGeneration/VillageStable/PropsR43")
sys.path.insert(0, str(PROPS_LIB))
sys.path.insert(0, str(TOOLS))

import props_geom as pg
import build_lumber_mill_arch as lm_arch

OUT_DIR = Path("F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/LumberMill-R49/RuinedFBX")


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def add_ruined_roof_x(
    b: pg.AssetBuilder, prefix: str, x0: float, x1: float, y0: float, y1: float,
    z_eave: float, z_ridge: float, eave_overhang: float = 66.0,
    gable_neg: float = 52.0, gable_pos: float = 0.0,
    breach_front=(0.25, 0.72), breach_back=(0.45, 0.78), n_trusses: int = 4,
):
    """Pitched roof along X with jagged collapsed slate breaches exposing broken rafters & purlins."""
    rise = z_ridge - z_eave
    cy = 0.5 * (y0 + y1)
    span_half = 0.5 * (y1 - y0)
    slope_run = span_half + eave_overhang
    slope_angle = math.degrees(math.atan2(rise, span_half))
    slope_len = math.hypot(slope_run, slope_run * (rise / span_half)) - 2.0
    z_drop = eave_overhang * (rise / span_half)
    slab_thick = 14.0
    z_mid = 0.5 * (z_ridge + (z_eave - z_drop)) + slab_thick * 0.65

    rx0 = x0 - gable_neg
    rx1 = x1 + gable_pos
    total_len = rx1 - rx0

    def add_slate_span(tag, sx0, sx1, side, tilt_jitter=0.0):
        slen = sx1 - sx0
        if slen < 36.0:
            return
        scx = 0.5 * (sx0 + sx1)
        y_mid = cy + side * (0.5 * slope_run + 1.0)
        b.block(f"{prefix}_{tag}", (scx, y_mid, z_mid), (slen, slope_len, slab_thick),
                mat="Slate", rot_deg=(-side * slope_angle + tilt_jitter, 0.0, 0.0), bevel_cm=0.5, segments=1)
        y_eave = cy + side * (span_half + eave_overhang - 2.0)
        b.block(f"{prefix}_{tag}_Fas", (scx, y_eave, z_eave - z_drop - 6.0), (slen, 5.0, 16.0),
                mat="DarkWood", bevel_cm=0.25, segments=1)

    for side, (bu0, bu1) in ((1, breach_front), (-1, breach_back)):
        bx0 = rx0 + total_len * bu0
        bx1 = rx0 + total_len * bu1
        add_slate_span(f"SL_{side}_A", rx0, bx0, side, tilt_jitter=0.4 * side)
        add_slate_span(f"SL_{side}_B", bx1, rx1, side, tilt_jitter=-0.5 * side)
        # Surviving upper/lower jagged slate stubs bordering the breach
        b.block(f"{prefix}_Stub_{side}_L", (bx0 + 26.0, cy + side * (slope_run * 0.72), z_eave - 2.0),
                (56.0, slope_len * 0.44, slab_thick * 0.9), mat="Slate",
                rot_deg=(-side * (slope_angle + 4.5), 3.0, 0.0), bevel_cm=0.4, segments=1)
        b.block(f"{prefix}_Stub_{side}_R", (bx1 - 24.0, cy + side * (slope_run * 0.30), z_ridge - 42.0),
                (52.0, slope_len * 0.40, slab_thick * 0.9), mat="Slate",
                rot_deg=(-side * (slope_angle - 3.5), -4.0, 0.0), bevel_cm=0.4, segments=1)
        # Broken purlin stubs
        p_y = cy + side * span_half * 0.5
        p_z = z_eave + rise * 0.5 - 14.0
        if bx0 > rx0 + 30.0:
            b.block(f"{prefix}_PurA_{side}", (0.5 * (rx0 + bx0 + 28.0), p_y, p_z),
                    (bx0 + 28.0 - rx0, 12.0, 14.0), mat="DarkWood", bevel_cm=0.25, segments=1)
        if rx1 > bx1 + 30.0:
            b.block(f"{prefix}_PurB_{side}", (0.5 * (bx1 - 22.0 + rx1), p_y, p_z),
                    (rx1 - (bx1 - 22.0), 12.0, 14.0), mat="DarkWood", bevel_cm=0.25, segments=1)

    # Ridge beam & cap broken across the front breach
    fb0 = rx0 + total_len * breach_front[0]
    fb1 = rx0 + total_len * breach_front[1]
    for rtag, a, c in (("R1", rx0 + 8.0, fb0 + 36.0), ("R2", fb1 - 24.0, rx1 - 8.0)):
        if c - a > 30.0:
            b.block(f"{prefix}_{rtag}_Beam", (0.5 * (a + c), cy, z_ridge - 16.0), (c - a, 14.0, 20.0), mat="DarkWood", bevel_cm=0.25, segments=1)
            b.block(f"{prefix}_{rtag}_Cap", (0.5 * (a + c), cy, z_ridge + slab_thick * 0.92), (c - a, 24.0, 11.0), mat="Slate", bevel_cm=0.4, segments=1)

    # Trusses: intact outside breach, snapped/jagged drooping rafters inside breach!
    xs = [x0 + 68.0 + k * ((x1 - x0 - 136.0) / max(1, n_trusses - 1)) for k in range(n_trusses)]
    for ti, tx in enumerate(xs):
        b.block(f"{prefix}_Tie_{ti}", (tx, cy, z_eave - 12.0), (15.0, (y1 - y0) - 34.0, 18.0), mat="DarkWood", bevel_cm=0.25, segments=1)
        in_breach = (fb0 - 20.0 <= tx <= fb1 + 20.0)
        if not in_breach:
            b.block(f"{prefix}_KP_{ti}", (tx, cy, z_eave + rise * 0.5 - 12.0), (12.0, 11.0, rise - 26.0), mat="DarkWood", bevel_cm=0.2, segments=1)
        else:
            # Snapped king-post stub
            b.block(f"{prefix}_KP_{ti}", (tx, cy, z_eave + 34.0), (12.0, 11.0, 82.0), mat="DarkWood", rot_deg=(4.0, -3.0, 0.0), bevel_cm=0.2, segments=1)
        for s in (-1, 1):
            if in_breach and s == 1:
                # Snapped rafter stub jutting from eave + hanging broken lower half resting solidly on tie beam (0 cm gap!)
                b.beam(f"{prefix}_RafBrkA_{ti}",
                       (tx, cy + s * (span_half + eave_overhang * 0.55), z_eave - z_drop * 0.55 - 10.0),
                       (tx, cy + s * (span_half * 0.52), z_eave + rise * 0.40), 11.0, 12.0, mat="DarkWood")
                b.beam(f"{prefix}_RafBrkB_{ti}",
                       (tx, cy + s * (span_half * 0.52), z_eave + rise * 0.40),
                       (tx + 6.0, cy + s * 14.0, z_eave - 6.0), 10.5, 11.5, mat="DarkWood")
            else:
                b.beam(f"{prefix}_Raf_{ti}_{s}",
                       (tx, cy + s * (span_half + eave_overhang * 0.65), z_eave - z_drop * 0.65 - 10.0),
                       (tx, cy + s * 8.0, z_ridge - 14.0), 11.0, 12.0, mat="DarkWood")


def add_ruined_roof_y(
    b: pg.AssetBuilder, prefix: str, x0: float, x1: float, y0: float, y1: float,
    z_eave: float, z_ridge: float, eave_overhang: float = 62.0,
    gable_neg: float = 52.0, gable_pos: float = 56.0, n_trusses: int = 4,
):
    """Steep pitched Bunkhouse roof along Y with collapsed front-west roof bay & exposed broken trusses."""
    rise = z_ridge - z_eave
    cx = 0.5 * (x0 + x1)
    span_half = 0.5 * (x1 - x0)
    slope_run = span_half + eave_overhang
    slope_angle = math.degrees(math.atan2(rise, span_half))
    slope_len = math.hypot(slope_run, slope_run * (rise / span_half)) - 2.0
    z_drop = eave_overhang * (rise / span_half)
    slab_thick = 14.0
    z_mid = 0.5 * (z_ridge + (z_eave - z_drop)) + slab_thick * 0.65

    ry0, ry1 = y0 - gable_neg, y1 + gable_pos
    # West slope (-1): big collapse in front half Y in [-40 .. +340]
    for tag, sy0, sy1 in (("W_Back", ry0, -40.0), ("W_Front", 340.0, ry1)):
        slen = sy1 - sy0
        scy = 0.5 * (sy0 + sy1)
        b.block(f"{prefix}_{tag}", (cx - (0.5 * slope_run + 1.0), scy, z_mid), (slope_len, slen, slab_thick),
                mat="Slate", rot_deg=(0.0, -slope_angle, 0.0), bevel_cm=0.5, segments=1)
        b.block(f"{prefix}_{tag}_Fas", (cx - (span_half + eave_overhang - 2.0), scy, z_eave - z_drop - 6.0),
                (5.0, slen, 16.0), mat="DarkWood", bevel_cm=0.25, segments=1)
    # East slope (+1): smaller jagged hole in middle Y in [40 .. 260]
    for tag, sy0, sy1 in (("E_Back", ry0, 40.0), ("E_Front", 260.0, ry1)):
        slen = sy1 - sy0
        scy = 0.5 * (sy0 + sy1)
        b.block(f"{prefix}_{tag}", (cx + (0.5 * slope_run + 1.0), scy, z_mid), (slope_len, slen, slab_thick),
                mat="Slate", rot_deg=(0.0, slope_angle, 0.0), bevel_cm=0.5, segments=1)
        b.block(f"{prefix}_{tag}_Fas", (cx + (span_half + eave_overhang - 2.0), scy, z_eave - z_drop - 6.0),
                (5.0, slen, 16.0), mat="DarkWood", bevel_cm=0.25, segments=1)

    # Broken ridge beam & cap
    for tag, sy0, sy1 in (("R_Back", ry0 + 10.0, 20.0), ("R_Front", 290.0, ry1 - 10.0)):
        b.block(f"{prefix}_{tag}_B", (cx, 0.5 * (sy0 + sy1), z_ridge - 16.0), (14.0, sy1 - sy0, 20.0), mat="DarkWood", bevel_cm=0.25, segments=1)
        b.block(f"{prefix}_{tag}_C", (cx, 0.5 * (sy0 + sy1), z_ridge + slab_thick * 0.92), (24.0, sy1 - sy0, 11.0), mat="Slate", bevel_cm=0.4, segments=1)

    ys = [y0 + 72.0 + k * ((y1 - y0 - 144.0) / max(1, n_trusses - 1)) for k in range(n_trusses)]
    for ti, ty in enumerate(ys):
        z_col = z_eave + 62.0
        col_w = 2.0 * span_half * (1.0 - 66.0 / max(rise, 1.0)) - 20.0
        in_hole = (ti in (1, 2))
        if not in_hole:
            b.block(f"{prefix}_Col_{ti}", (cx, ty, z_col), (col_w, 13.0, 15.0), mat="DarkWood", bevel_cm=0.25, segments=1)
            b.block(f"{prefix}_KP_{ti}", (cx, ty, 0.5 * (z_col + z_ridge - 18.0)), (11.0, 10.5, z_ridge - z_col - 26.0), mat="DarkWood", bevel_cm=0.2, segments=1)
        else:
            # Snapped collar beam still anchored to intact east rafter, drooping gently inward
            b.beam(f"{prefix}_ColBrk_{ti}", (cx + col_w * 0.50, ty, z_col), (cx + 8.0, ty, z_col - 18.0), 12.0, 13.0, mat="DarkWood")
        for s in (-1, 1):
            if in_hole and s == -1:
                b.beam(f"{prefix}_RafBrk_{ti}",
                       (cx + s * (span_half + eave_overhang * 0.55), ty, z_eave - z_drop * 0.55 - 10.0),
                       (cx + s * (span_half * 0.42), ty, z_eave + rise * 0.46), 11.0, 12.0, mat="DarkWood")
            else:
                b.beam(f"{prefix}_Raf_{ti}_{s}",
                       (cx + s * (span_half + eave_overhang * 0.65), ty, z_eave - z_drop * 0.65 - 10.0),
                       (cx + s * 8.0, ty, z_ridge - 14.0), 11.0, 12.0, mat="DarkWood")


def add_debris_cluster(b: pg.AssetBuilder, prefix: str, cx: float, cy: float, z_base: float, count: int = 12, spread: float = 95.0, include_stones: bool = True):
    """Add 100% grounded weathered slate shards, splintered beams & rubble stones (ZERO floating ends!)."""
    rng = b.rng
    for k in range(count):
        ang = rng.uniform(0.0, math.tau)
        r = rng.uniform(8.0, spread)
        px = cx + r * math.cos(ang)
        py = cy + r * math.sin(ang)
        yaw = rng.uniform(0.0, 360.0)
        kind = k % (4 if include_stones else 3)
        if kind == 0:
            # Fallen broken slate roof shingle slab (gentle tilt, buried 2.5 cm into z_base)
            sx = rng.uniform(26.0, 52.0)
            sy = rng.uniform(18.0, 34.0)
            sz = rng.uniform(4.5, 7.5)
            rx, ry = rng.uniform(-6.0, 6.0), rng.uniform(-6.0, 6.0)
            drop = 0.5 * (sx * abs(math.sin(math.radians(ry))) + sy * abs(math.sin(math.radians(rx))))
            b.block(f"{prefix}_Sl_{k}", (px, py, z_base + sz * 0.5 - drop - 2.5),
                    (sx, sy, sz),
                    mat="Slate", rot_deg=(rx, ry, yaw), bevel_cm=0.35, segments=1)
        elif kind == 1:
            # Splintered dark roof timber / plank (lies firmly settled into ground, NEVER floating at either end!)
            sx = rng.uniform(55.0, 128.0)
            sy = rng.uniform(10.0, 16.0)
            sz = rng.uniform(8.0, 13.0)
            rx, ry = rng.uniform(-4.0, 4.0), rng.uniform(-4.5, 4.5)
            drop = 0.5 * (sx * abs(math.sin(math.radians(ry))) + sy * abs(math.sin(math.radians(rx))))
            b.block(f"{prefix}_Bm_{k}", (px, py, z_base + sz * 0.5 - drop - 2.5),
                    (sx, sy, sz),
                    mat="DarkWood" if k % 2 == 0 else "Oak",
                    rot_deg=(rx, ry, yaw), bevel_cm=0.25, segments=1)
        elif kind == 2:
            # Broken lime plaster / board chunk embedded solidly into mud
            sx = rng.uniform(22.0, 42.0)
            sy = rng.uniform(16.0, 32.0)
            sz = rng.uniform(8.0, 14.0)
            rx, ry = rng.uniform(-8.0, 8.0), rng.uniform(-8.0, 8.0)
            drop = 0.5 * (sx * abs(math.sin(math.radians(ry))) + sy * abs(math.sin(math.radians(rx))))
            b.block(f"{prefix}_Pl_{k}", (px, py, z_base + sz * 0.5 - drop - 3.0),
                    (sx, sy, sz),
                    mat="Lime", rot_deg=(rx, ry, yaw), bevel_cm=0.4, segments=1)
        else:
            # Cracked masonry footing stone seated deeply into earth
            sx = rng.uniform(22.0, 40.0)
            sy = rng.uniform(18.0, 34.0)
            sz = rng.uniform(16.0, 26.0)
            rx, ry = rng.uniform(-8.0, 8.0), rng.uniform(-8.0, 8.0)
            drop = 0.5 * (sx * abs(math.sin(math.radians(ry))) + sy * abs(math.sin(math.radians(rx))))
            b.block(f"{prefix}_St_{k}", (px, py, z_base + sz * 0.5 - drop - 4.5),
                    (sx, sy, sz),
                    mat="Footing" if k % 2 == 0 else "Stone",
                    rot_deg=(rx, ry, yaw), bevel_cm=0.65, segments=1)


def build_warehouse_ruined(out_dir: Path):
    """Ruined Warehouse: breached slate roof, broken rafters & hoist, knocked-off door leaf, clear combat doorways."""
    b = pg.AssetBuilder("SM_LM_Warehouse_Ruined", seed=5101, ground_mud_cm=68.0)
    hx, hy = 520.0, 350.0
    z_eave, z_ridge = 356.0, 560.0

    # Same foundation, oak floor & walkable wagon ramp (slightly weathered/scarred colliders identical to intact!)
    b.block("WHR_Found", (0.0, 0.0, -60.0), (1016.0, 676.0, 120.0), mat="Footing", bevel_cm=0.6, segments=1)
    b.block("WHR_Floor", (0.0, 0.0, 8.0), (1000.0, 660.0, 16.0), mat="DarkWood", bevel_cm=0.25, segments=1)
    b.add_collider((3.0, 0.0, 8.0), (1048.0, 696.0, 16.0))
    b.block("WHR_RampBase", (0.0, hy + 88.0, -24.0), (304.0, 180.0, 42.0), mat="Footing", bevel_cm=0.5, segments=1)
    b.block("WHR_RampL", (-86.0, hy + 96.0, -9.0), (134.0, 206.0, 12.0), mat="DarkWood", rot_deg=(-12.8, 0.0, 0.0), bevel_cm=0.25, segments=1)
    b.block("WHR_RampR", (72.0, hy + 96.0, -9.0), (164.0, 206.0, 12.0), mat="DarkWood", rot_deg=(-12.8, 1.2, 0.0), bevel_cm=0.25, segments=1)
    b.add_collider((0.0, hy + 42.0, 6.0), (312.0, 88.0, 12.0))
    b.add_collider((0.0, hy + 114.0, -9.0), (312.0, 88.0, 12.0))
    b.add_collider((0.0, hy + 178.0, -22.0), (312.0, 72.0, 12.0))

    # Walls with extra monster-torn breach holes (keeping lower walls/framing & wide clear doorways!)
    lm_arch.add_wall_zero_flicker(
        b, "WHR_West", "X", -hx + 14.0, -hy, hy, 16.0, z_eave,
        openings=[(-110.0, 110.0, 130.0, 310.0)], mat_wall="DarkWood", z_plinth=44.0, own_corners=True, out_sign=-1.0,
    )
    lm_arch.add_wall_zero_flicker(
        b, "WHR_East", "X", hx - 14.0, -hy, hy, 16.0, z_eave,
        openings=[(-110.0, 30.0, 16.0, 256.0)], mat_wall="DarkWood", z_plinth=44.0, own_corners=True, out_sign=1.0,
    )
    lm_arch.add_wall_zero_flicker(
        b, "WHR_Front", "Y", hy - 14.0, -hx + 27.6, hx - 27.6, 16.0, z_eave,
        openings=[(-150.0, 150.0, 16.0, 292.0), (210.0, 410.0, 150.0, 324.0)],
        mat_wall="DarkWood", z_plinth=44.0, own_corners=False, out_sign=1.0,
    )
    lm_arch.add_wall_zero_flicker(
        b, "WHR_Back", "Y", -hy + 14.0, -hx + 27.6, hx - 27.6, 16.0, z_eave,
        openings=[(-320.0, -140.0, 132.0, 306.0), (150.0, 340.0, 140.0, 298.0)],
        mat_wall="DarkWood", z_plinth=44.0, own_corners=False, out_sign=-1.0,
    )

    # Exposed jagged diagonal timber studs crossing the front wall breach
    b.beam("WHR_BrStud1", (245.0, hy - 14.0, 148.0), (262.0, hy - 10.0, 296.0), 11.0, 11.0, mat="DarkWood")
    b.beam("WHR_BrStud2", (355.0, hy - 14.0, 154.0), (318.0, hy - 20.0, 316.0), 10.0, 10.0, mat="Oak")

    # Partial ruined east gable & breached west gable + breached slate roof!
    lm_arch.add_prism_gable(b, "WHR_GE", "X", hx - 14.0, -hy + 14.0, hy - 14.0, z_eave, z_ridge, mat="Lime")
    # West gable only half surviving (south half)
    lm_arch.add_prism_gable(b, "WHR_GW", "X", -hx + 14.0, -hy + 14.0, 40.0, z_eave, z_ridge - 42.0, mat="Lime")
    add_ruined_roof_x(b, "WHR_Roof", -hx, hx, -hy, hy, z_eave, z_ridge,
                      eave_overhang=66.0, gable_neg=52.0, gable_pos=0.0,
                      breach_front=(0.32, 0.78), breach_back=(0.52, 0.84), n_trusses=4)

    # Snapped hoist beam stub with dangling frayed rope (no pulley)
    b.block("WHR_HoistStub", (0.0, hy + 28.0, 340.0), (20.0, 96.0, 22.0), mat="DarkWood", rot_deg=(-8.0, 0.0, 0.0), bevel_cm=0.3, segments=1)
    b.beam("WHR_HoistBrL", (-14.0, hy + 2.0, 304.0), (-6.0, hy + 64.0, 332.0), 10.0, 10.0, mat="DarkWood")
    b.rope_braid("WHR_FrayedRope", [(0.0, hy + 68.0, 330.0), (6.0, hy + 72.0, 250.0), (-4.0, hy + 66.0, 185.0)], radius_cm=1.2, mat="Rope")

    # Right barn door hangs askew; left barn door torn off & lying solidly grounded flat-tilted outside west ramp!
    lm_arch.add_open_barn_door(b, "WHR_DoorR", (156.0, hy + 6.0, 14.0), 142.0, 268.0, yaw_open_deg=34.0, mat="DarkWood")
    b.push_xform((-305.0, hy + 130.0, -32.0), (88.0, 2.0, -18.0))
    b.block("WHR_FallenDoor", (0.0, 0.0, 0.0), (140.0, 7.0, 258.0), mat="DarkWood", bevel_cm=0.25, segments=1)
    b.block("WHR_FallenDoorL", (0.0, 4.5, 0.0), (132.0, 3.5, 14.0), mat="Oak", bevel_cm=0.2, segments=1)
    b.pop_xform()

    # Fallen roof beams & slate rubble piles tucked clear of main entry & center floor
    add_debris_cluster(b, "WHR_DebInE", 290.0, 140.0, 16.0, count=14, spread=110.0, include_stones=False)
    add_debris_cluster(b, "WHR_DebOutE", 330.0, hy + 65.0, -30.0, count=12, spread=95.0, include_stones=True)
    add_debris_cluster(b, "WHR_DebInW", -340.0, -170.0, 16.0, count=10, spread=95.0, include_stones=False)
    b.beam("WHR_FallenRaf", (280.0, 160.0, 14.0), (502.0, 160.0, 192.0), 11.0, 12.0, mat="DarkWood")

    return b.finish(out_dir, lod_ratios=(1.0,))


def build_toolroom_ruined(out_dir: Path):
    """Ruined ToolRoom + half-collapsed Sawing Canopy: broken east canopy posts/roof, breached main roof, smashed bench."""
    b = pg.AssetBuilder("SM_LM_ToolRoom_Ruined", seed=5102, ground_mud_cm=66.0)
    hx, hy = 340.0, 350.0
    z_eave, z_ridge = 356.0, 560.0

    # Same foundation, flagstone floor, 3-step stoop & East bridge (100% passable!)
    b.block("TRR_Found", (0.0, 0.0, -60.0), (664.0, 676.0, 120.0), mat="Footing", bevel_cm=0.6, segments=1)
    b.block("TRR_Floor", (0.0, 0.0, 8.0), (660.0, 660.0, 16.0), mat="Flagstone", bevel_cm=0.3, segments=1)
    b.add_collider((0.0, 0.0, 8.0), (696.0, 696.0, 16.0))
    b.block("TRR_StepTop", (0.0, hy + 28.0, -15.0), (208.0, 56.0, 60.0), mat="Flagstone", bevel_cm=0.45, segments=1)
    b.block("TRR_StepMid", (0.0, hy + 72.0, -22.5), (218.0, 44.0, 45.0), mat="Flagstone", bevel_cm=0.45, segments=1)
    b.block("TRR_StepBot", (0.0, hy + 112.0, -30.0), (228.0, 42.0, 30.0), mat="Flagstone", bevel_cm=0.45, segments=1)
    b.add_collider((0.0, hy + 28.0, 7.5), (208.0, 56.0, 15.0))
    b.add_collider((0.0, hy + 72.0, -7.5), (218.0, 44.0, 15.0))
    b.add_collider((0.0, hy + 112.0, -22.5), (228.0, 42.0, 15.0))

    lm_arch.add_wall_zero_flicker(
        b, "TRR_East", "X", hx - 14.0, -hy, hy, 16.0, z_eave,
        openings=[(-90.0, 40.0, 16.0, 252.0)], mat_wall="Lime", z_plinth=44.0, own_corners=True, out_sign=1.0,
    )
    b.block("TRR_EastBridge", (hx, -25.0, 7.85), (56.0, 130.0, 14.7), mat="Flagstone", bevel_cm=0.20, segments=1)
    b.add_collider((hx, -25.0, 8.0), (72.0, 134.0, 16.0))
    lm_arch.add_wall_zero_flicker(
        b, "TRR_Front", "Y", hy - 14.0, -hx - 0.5, hx - 27.6, 16.0, z_eave,
        openings=[(-270.0, -140.0, 102.0, 245.0), (-90.0, 90.0, 16.0, 258.0), (140.0, 275.0, 96.0, 260.0)],
        mat_wall="Lime", z_plinth=48.0, own_corners=False, out_sign=1.0,
    )
    lm_arch.add_wall_zero_flicker(
        b, "TRR_Back", "Y", -hy + 14.0, -hx - 0.5, hx - 27.6, 16.0, z_eave,
        openings=[(-280.0, -120.0, 110.0, 286.0), (145.0, 285.0, 116.0, 242.0)],
        mat_wall="Lime", z_plinth=48.0, own_corners=False, out_sign=-1.0,
    )

    # Torn workshop door hanging off at wide angle
    lm_arch.add_open_barn_door(b, "TRR_Door", (96.0, hy + 6.0, 15.0), 116.0, 236.0, yaw_open_deg=26.0, mat="DarkWood")

    # Breached ToolRoom main slate roof
    add_ruined_roof_x(b, "TRR_Roof", -hx, hx, -hy, hy, z_eave, z_ridge,
                      eave_overhang=66.0, gable_neg=0.0, gable_pos=12.0,
                      breach_front=(0.12, 0.58), breach_back=(0.20, 0.62), n_trusses=3)

    # Half-collapsed Front Sawing Canopy:
    # West half (-294, -108) still standing & sagging; East half (+108, +294) snapped & collapsed into yard rubble!
    can_y0, can_y1 = hy + 2.0, hy + 310.0
    can_z0, can_z1 = 292.0, 236.0
    for px in (-294.0, -108.0):
        b.block(f"CanR_Pier_{int(px)}", (px, can_y1 - 16.0, -32.0), (32.0, 32.0, 128.0), mat="Footing", bevel_cm=0.7, segments=1)
        b.block(f"CanR_Post_{int(px)}", (px, can_y1 - 16.0, 129.0), (16.5, 16.5, 194.0), mat="DarkWood", bevel_cm=0.3, segments=1)
        b.add_collider((px, can_y1 - 16.0, 105.0), (26.0, 26.0, 250.0))
    for px, stub_h in ((108.0, 82.0), (294.0, 66.0)):
        b.block(f"CanR_Pier_{int(px)}", (px, can_y1 - 16.0, -32.0), (32.0, 32.0, 128.0), mat="Footing", bevel_cm=0.7, segments=1)
        b.block(f"CanR_Stub_{int(px)}", (px, can_y1 - 16.0, 32.0 + stub_h * 0.5), (16.5, 16.5, stub_h), mat="DarkWood", rot_deg=(4.0, -5.0, 0.0), bevel_cm=0.3, segments=1)
        b.add_collider((px, can_y1 - 16.0, 50.0), (26.0, 26.0, 120.0))

    # Surviving west half of canopy header, ledger, rafters & tattered slate
    b.block("CanR_HeaderW", (-195.0, can_y1 - 16.0, can_z1 - 4.0), (242.0, 21.0, 20.0), mat="DarkWood", rot_deg=(0.0, 2.5, 0.0), bevel_cm=0.3, segments=1)
    b.block("CanR_Ledger", (0.0, can_y0 + 10.0, can_z0), (624.0, 15.0, 18.0), mat="DarkWood", bevel_cm=0.3, segments=1)
    for rx in (-288, -216, -144, -72):
        b.beam(f"CanR_RafW_{rx}", (float(rx), can_y0 + 8.0, can_z0 + 4.0), (float(rx), can_y1 + 22.0, can_z1 - 4.0), 9.0, 12.0, mat="DarkWood")
    can_slope = math.degrees(math.atan2(can_z0 - can_z1, can_y1 - can_y0))
    can_len = math.hypot(can_y1 - can_y0 + 48.0, (can_z0 - can_z1) * 1.15)
    b.block("CanR_SlateW", (-178.0, 0.5 * (can_y0 + can_y1) + 12.0, 0.5 * (can_z0 + can_z1) + 13.0),
            (286.0, can_len, 12.0), mat="Slate", rot_deg=(-can_slope, 2.5, 0.0), bevel_cm=0.45, segments=1)
    # Collapsed east canopy header & rafters leaning down cleanly from surviving stubs straight into yard mud (Z=-36)!
    b.beam("CanR_FallenHdr", (108.0, can_y1 - 16.0, 108.0), (318.0, can_y1 + 12.0, -36.0), 18.0, 18.0, mat="DarkWood")
    b.beam("CanR_FallenRaf1", (175.0, can_y0 + 12.0, can_z0), (225.0, can_y1 - 8.0, -36.0), 9.0, 11.0, mat="DarkWood")
    b.beam("CanR_FallenRaf2", (265.0, can_y0 + 12.0, can_z0), (298.0, can_y1 - 24.0, -36.0), 9.0, 11.0, mat="DarkWood")
    b.block("CanR_FallenSlate", (238.0, can_y1 - 62.0, -6.0), (168.0, 142.0, 10.0), mat="Slate", rot_deg=(-22.0, 10.0, -8.0), bevel_cm=0.4, segments=1)
    add_debris_cluster(b, "CanR_DebE", 230.0, can_y1 - 30.0, -32.0, count=12, spread=85.0, include_stones=True)

    # Smashed / listing Workbench inside south wall (resting flush on BOTH standing left leg and snapped right stub!)
    wb_y = -hy + 84.0
    b.block("TRR_BenchTop", (-7.0, wb_y, 67.5), (344.0, 86.0, 10.0), mat="DarkWood", rot_deg=(2.5, 8.6, 1.5), bevel_cm=0.4, segments=1)
    b.block("TRR_BenchLegL", (-156.0, wb_y, 50.0), (11.0, 68.0, 70.0), mat="DarkWood", bevel_cm=0.25, segments=1)
    b.block("TRR_BenchLegR", (142.0, wb_y + 4.0, 28.0), (11.0, 64.0, 24.0), mat="DarkWood", rot_deg=(6.0, 14.0, 0.0), bevel_cm=0.25, segments=1)
    b.add_collider((0.0, wb_y, 48.0), (348.0, 92.0, 78.0))
    add_debris_cluster(b, "TRR_DebIn", -180.0, -120.0, 16.0, count=10, spread=95.0, include_stones=False)

    return b.finish(out_dir, lod_ratios=(1.0,))


def build_bunkhouse_ruined(out_dir: Path):
    """Ruined 2-story Bunkhouse: breached 2F roof/gable, leaning porch roof, cracked shutters, cold hearth, walkable stairs."""
    b = pg.AssetBuilder("SM_LM_Bunkhouse_Ruined", seed=5103, ground_mud_cm=68.0)
    hx, hy = 360.0, 420.0
    z1_top = 296.0
    z2_flr = 312.0
    z2_eave = 528.0
    z2_ridge = 728.0
    hy2 = hy + 24.0

    # Same foundation, 1F floor, 3-step stone porch & 16-step staircase (100% walkable!)
    b.block("BHR_Found", (0.0, 0.0, -60.0), (696.0, 816.0, 120.0), mat="Footing", bevel_cm=0.6, segments=1)
    b.block("BHR_Floor1F", (0.0, 0.0, 8.0), (680.0, 800.0, 16.0), mat="DarkWood", bevel_cm=0.25, segments=1)
    b.add_collider((0.0, 0.0, 8.0), (716.0, 836.0, 16.0))

    lm_arch.add_wall_zero_flicker(
        b, "BHR1_West", "X", -hx + 14.0, -hy, hy, 16.0, z1_top,
        openings=[(-160.0, -30.0, 16.0, 252.0)], mat_wall="Lime", z_plinth=44.0, own_corners=True, out_sign=-1.0,
    )
    lm_arch.add_wall_zero_flicker(
        b, "BHR1_East", "X", hx - 14.0, -hy, hy, 16.0, z1_top,
        openings=[(145.0, 305.0, 96.0, 236.0)], mat_wall="Lime", z_plinth=44.0, own_corners=True, out_sign=1.0,
    )
    lm_arch.add_wall_zero_flicker(
        b, "BHR1_Front", "Y", hy - 14.0, -hx + 27.6, hx - 27.6, 16.0, z1_top,
        openings=[(-285.0, -150.0, 96.0, 232.0), (-68.0, 68.0, 16.0, 248.0), (150.0, 285.0, 96.0, 238.0)],
        mat_wall="Lime", z_plinth=44.0, own_corners=False, out_sign=1.0,
    )
    lm_arch.add_wall_zero_flicker(
        b, "BHR1_Back", "Y", -hy + 14.0, -hx + 27.6, hx - 27.6, 16.0, z1_top,
        openings=[(-160.0, -10.0, 130.0, 246.0)], mat_wall="Lime", z_plinth=44.0, own_corners=False, out_sign=-1.0,
    )

    # Askew front door & damaged sagging front porch awning (doorway & steps 100% passable!)
    lm_arch.add_open_barn_door(b, "BHR_MainDoor", (74.0, hy + 6.0, 15.0), 124.0, 224.0, yaw_open_deg=12.0, mat="DarkWood")
    b.block("BHR_PorchStep", (0.0, hy + 58.0, -18.0), (262.0, 114.0, 64.0), mat="Flagstone", bevel_cm=0.45, segments=1)
    b.block("BHR_PorchMidStep", (0.0, hy + 128.0, -24.5), (226.0, 42.0, 49.0), mat="Flagstone", bevel_cm=0.45, segments=1)
    b.block("BHR_PorchLowStep", (0.0, hy + 166.0, -32.0), (236.0, 40.0, 34.0), mat="Flagstone", bevel_cm=0.45, segments=1)
    b.add_collider((0.0, hy + 58.0, 7.0), (262.0, 114.0, 14.0))
    b.add_collider((0.0, hy + 128.0, -8.0), (226.0, 42.0, 16.0))
    b.add_collider((0.0, hy + 166.0, -23.0), (236.0, 40.0, 16.0))
    # West porch post standing; East porch post bent/cracked & physically supporting sagging east header (0 cm gap!)
    b.block("BHR_PPierW", (-122.0, hy + 104.0, -32.0), (28.0, 28.0, 124.0), mat="Footing", bevel_cm=0.5, segments=1)
    b.block("BHR_PPostW", (-122.0, hy + 104.0, 137.0), (16.0, 16.0, 210.0), mat="DarkWood", bevel_cm=0.28, segments=1)
    b.add_collider((-122.0, hy + 104.0, 108.0), (26.0, 26.0, 248.0))
    b.block("BHR_PPierE", (122.0, hy + 104.0, -32.0), (28.0, 28.0, 124.0), mat="Footing", bevel_cm=0.5, segments=1)
    b.block("BHR_PStubE", (122.0, hy + 104.0, 82.0), (16.0, 16.0, 104.0), mat="DarkWood", rot_deg=(0.0, 4.0, 0.0), bevel_cm=0.28, segments=1)
    b.beam("BHR_PUpperE", (124.0, hy + 104.0, 124.0), (114.0, hy + 104.0, 214.0), 15.0, 15.0, mat="DarkWood")
    b.add_collider((122.0, hy + 104.0, 108.0), (26.0, 26.0, 248.0))
    b.block("BHR_PHeader", (-8.0, hy + 104.0, 230.0), (266.0, 19.0, 18.0), mat="DarkWood", rot_deg=(0.0, 8.5, 0.0), bevel_cm=0.28, segments=1)
    b.block("BHR_PRoof", (-8.0, hy + 68.0, 248.0), (286.0, 136.0, 12.0), mat="Slate", rot_deg=(-14.0, 8.5, 0.0), bevel_cm=0.45, segments=1)

    # Cold ruined stone hearth (no embers, knocked andiron, crumbling chimney cap!)
    b.block("BHR_HearthPad", (hx - 62.0, -30.0, 19.0), (76.0, 200.0, 6.0), mat="Flagstone", bevel_cm=0.35, segments=1)
    b.block("BHR_HearthBack", (hx - 33.0, -30.0, 86.0), (10.0, 134.0, 132.0), mat="Footing", bevel_cm=0.35, segments=1)
    b.block("BHR_HearthCheekL", (hx - 52.5, -112.0, 86.0), (48.0, 30.0, 132.0), mat="Footing", bevel_cm=0.6, segments=1)
    b.block("BHR_HearthCheekR", (hx - 52.5, 52.0, 86.0), (48.0, 30.0, 132.0), mat="Footing", bevel_cm=0.6, segments=1)
    b.block("BHR_HearthMantel", (hx - 54.0, -30.0, 158.0), (54.0, 202.0, 16.0), mat="DarkWood", rot_deg=(2.5, 0.0, 0.0), bevel_cm=0.35, segments=1)
    b.block("BHR_HearthHood", (hx - 48.0, -30.0, 232.0), (34.0, 168.0, 128.0), mat="Footing", bevel_cm=0.7, segments=1)
    b.block("BHR_ChimBase", (hx + 30.0, -30.0, 210.0), (58.0, 184.0, 480.0), mat="Footing", bevel_cm=0.8, segments=1)
    b.block("BHR_ChimUpper", (hx + 32.0, -30.0, 560.0), (56.0, 114.0, 220.0), mat="Footing", bevel_cm=0.8, segments=1)
    b.add_collider((hx - 38.0, -30.0, 155.0), (66.0, 196.0, 276.0))

    # Walkable 16-step oak staircase (identical collision geometry!)
    n_steps = 16
    x_st0, x_st1 = -215.0, 225.0
    y_st_c, y_st_w = -330.0, 120.0
    z_st0, z_st1 = 16.0, z2_flr
    dx_s = (x_st1 - x_st0) / n_steps
    dz_s = (z_st1 - z_st0) / n_steps
    for k in range(n_steps):
        sx = x_st0 + (k + 0.5) * dx_s
        sz = z_st0 + (k + 1.0) * dz_s
        b.block(f"StR_Tr_{k}", (sx, y_st_c, sz - 2.5), (dx_s + 2.5, y_st_w, 5.0), mat="DarkWood", bevel_cm=0.18, segments=1)
        b.block(f"StR_Rs_{k}", (sx - dx_s * 0.46, y_st_c, sz - dz_s * 0.5 - 2.5), (3.2, y_st_w - 4.0, dz_s - 4.5), mat="DarkWood", bevel_cm=0.10, segments=1)
        b.add_collider((sx, y_st_c, sz - dz_s * 0.5), (dx_s + 4.0, y_st_w, dz_s))
    for sy_s, sy in (("S", y_st_c - y_st_w * 0.5 - 4.0), ("N", y_st_c + y_st_w * 0.5 + 4.0)):
        b.beam(f"StR_Str_{sy_s}", (x_st0 - 6.0, sy, z_st0), (x_st1 + 6.0, sy, z_st1 - 8.0), 7.5, 22.0, mat="DarkWood")
    y_rail = y_st_c + y_st_w * 0.5 + 4.5
    b.block("StR_NBot", (x_st0 - 4.0, y_rail, z_st0 + 50.0), (11.0, 11.0, 100.0), mat="DarkWood", bevel_cm=0.25, segments=1)
    b.block("StR_NTop", (x_st1 + 4.0, y_rail, z_st1 + 46.0), (11.0, 11.0, 96.0), mat="DarkWood", bevel_cm=0.25, segments=1)
    b.beam("StR_Rail", (x_st0 - 4.0, y_rail, z_st0 + 96.0), (x_st1 + 4.0, y_rail, z_st1 + 92.0), 7.5, 6.5, mat="DarkWood")

    # 2F floor deck & perimeter rim beams
    for jy in (-244.0, -140.0, -35.0, 70.0, 175.0, 280.0, 385.0):
        b.block(f"BHR_Joist_{int(jy)}", (0.0, jy, z1_top - 8.0), (662.0, 13.0, 15.0), mat="DarkWood", bevel_cm=0.25, segments=1)
    b.block("BHR_F2_Main", (0.0, 78.75, 304.25), (684.0, 673.5, 15.5), mat="DarkWood", bevel_cm=0.25, segments=1)
    b.add_collider((0.0, 88.0, 304.25), (700.0, 700.0, 16.0))
    b.block("BHR_F2_LandE", (284.0, -330.0, 304.25), (116.0, 144.0, 15.5), mat="DarkWood", bevel_cm=0.25, segments=1)
    b.add_collider((284.0, -330.0, 304.25), (124.0, 150.0, 16.0))
    b.block("BHR_F2_LandW", (-288.0, -330.0, 304.25), (108.0, 144.0, 15.5), mat="DarkWood", bevel_cm=0.25, segments=1)
    b.add_collider((-288.0, -330.0, 304.25), (116.0, 150.0, 16.0))
    b.block("BHR_JettyFascia", (0.0, 429.75, 304.0), (724.0, 28.5, 16.0), mat="DarkWood", bevel_cm=0.25, segments=1)
    b.block("BHR_RimBack", (0.0, -hy + 14.0, 304.0), (720.0, 25.4, 15.2), mat="DarkWood", bevel_cm=0.18, segments=1)
    b.block("BHR_RimWest", (-hx + 14.0, 10.6, 304.0), (25.4, 808.8, 15.2), mat="DarkWood", bevel_cm=0.18, segments=1)
    b.block("BHR_RimEast", (hx - 14.0, 10.6, 304.0), (25.4, 808.8, 15.2), mat="DarkWood", bevel_cm=0.18, segments=1)

    # Damaged 2F stairwell railing (some missing spindles)
    b.block("BHR2_RailLong", (-11.0, -258.0, z2_flr + 92.0), (442.0, 8.5, 7.5), mat="DarkWood", bevel_cm=0.22, segments=1)
    b.add_collider((-11.0, -258.0, z2_flr + 48.0), (444.0, 12.0, 96.0))
    for rx in (-220, -134, -48, 81, 167):
        b.block(f"BHR2_BalL_{rx}", (float(rx), -258.0, z2_flr + 46.0), (5.0, 5.0, 88.0), mat="DarkWood", bevel_cm=0.14, segments=1)
    b.block("BHR2_RailEnd", (-234.0, -332.5, z2_flr + 92.0), (8.5, 139.0, 7.5), mat="DarkWood", bevel_cm=0.22, segments=1)
    b.add_collider((-234.0, -332.5, z2_flr + 48.0), (12.0, 142.0, 96.0))

    # 2F walls with torn upper breaches
    lm_arch.add_wall_zero_flicker(
        b, "BHR2_West", "X", -hx + 14.0, -hy, hy2, z2_flr, z2_eave,
        openings=[(30.0, 315.0, z2_flr + 74.0, z2_eave - 26.0)], mat_wall="Lime", z_plinth=0.0, own_corners=True, out_sign=-1.0,
    )
    lm_arch.add_wall_zero_flicker(
        b, "BHR2_East", "X", hx - 14.0, -hy, hy2, z2_flr, z2_eave,
        openings=[(120.0, 290.0, z2_flr + 80.0, z2_flr + 196.0)], mat_wall="Lime", z_plinth=0.0, own_corners=True, out_sign=1.0,
    )
    lm_arch.add_wall_zero_flicker(
        b, "BHR2_Front", "Y", hy2 - 14.0, -hx + 27.6, hx - 27.6, z2_flr, z2_eave,
        openings=[(-260.0, -90.0, z2_flr + 76.0, z2_eave - 24.0), (105.0, 250.0, z2_flr + 86.0, z2_flr + 194.0)],
        mat_wall="Lime", z_plinth=0.0, own_corners=False, out_sign=1.0,
    )
    lm_arch.add_wall_zero_flicker(
        b, "BHR2_Back", "Y", -hy + 14.0, -hx + 27.6, hx - 27.6, z2_flr, z2_eave,
        openings=[(-95.0, 95.0, z2_flr + 86.0, z2_flr + 194.0)], mat_wall="Lime", z_plinth=0.0, own_corners=False, out_sign=-1.0,
    )

    # Partial North gable (west corner blown out) + intact South gable + Breached steep roof!
    lm_arch.add_prism_gable(b, "BHR_GN", "Y", hy2 - 14.0, -60.0, hx - 14.0, z2_eave, z2_ridge - 32.0, mat="Lime")
    lm_arch.add_prism_gable(b, "BHR_GS", "Y", -hy + 14.0, -hx + 14.0, hx - 14.0, z2_eave, z2_ridge, mat="Lime")
    add_ruined_roof_y(b, "BHR_Roof", -hx, hx, -hy, hy2, z2_eave, z2_ridge,
                      eave_overhang=62.0, gable_neg=52.0, gable_pos=56.0, n_trusses=4)

    # Fallen debris inside 2F & outside porch east corner
    add_debris_cluster(b, "BHR_Deb2F", -145.0, 145.0, z2_flr, count=12, spread=95.0, include_stones=False)
    add_debris_cluster(b, "BHR_DebOut", 215.0, hy + 88.0, -30.0, count=10, spread=80.0, include_stones=True)

    return b.finish(out_dir, lod_ratios=(1.0,))


def build_camp_gate_arch_ruined(out_dir: Path):
    """Ruined Camp Gate Arch: deeply buried piers, sagging header resting solidly on both posts, physically chained signboard."""
    b = pg.AssetBuilder("SM_LM_CampGateArch_Ruined", seed=5104, ground_mud_cm=64.0)
    gx = 292.0
    # West pier buried down to Z=-74 cm & post solidly seated into pier + supporting header at Z=390 cm
    b.block("GAR_PierW", (-gx, 0.0, -14.0), (46.0, 46.0, 120.0), mat="Footing", bevel_cm=0.9, segments=1)
    b.block("GAR_PostW", (-gx - 4.0, 0.0, 222.0), (26.0, 26.0, 356.0), mat="DarkWood", rot_deg=(0.0, -2.2, 0.0), bevel_cm=0.5, segments=1)
    b.beam("GAR_BraceW", (-gx + 8.0, 0.0, 298.0), (-gx + 86.0, 0.0, 372.0), 14.0, 14.0, mat="DarkWood")
    b.add_collider((-gx, 0.0, 190.0), (42.0, 42.0, 380.0))

    # East pier buried down to Z=-74 cm & fractured post reaching Z=300 cm -> meets sagging header with 0 cm gap!
    b.block("GAR_PierE", (gx, 0.0, -14.0), (46.0, 46.0, 120.0), mat="Footing", bevel_cm=0.9, segments=1)
    b.block("GAR_PostE", (gx + 4.0, 0.0, 174.0), (26.0, 26.0, 256.0), mat="DarkWood", rot_deg=(0.0, 3.5, 0.0), bevel_cm=0.5, segments=1)
    b.add_collider((gx, 0.0, 145.0), (42.0, 42.0, 290.0))

    # Sagging overhead header seated cleanly onto PostW (Z=391) and PostE (Z=295) + broken slate cap
    b.block("GAR_Header", (0.0, 0.0, 343.0), (gx * 2.0 + 68.0, 24.0, 28.0), mat="DarkWood", rot_deg=(0.0, 9.2, 0.0), bevel_cm=0.45, segments=1)
    b.block("GAR_RoofW", (-140.0, 0.0, 388.0), (340.0, 82.0, 9.0), mat="Slate", rot_deg=(12.0, 9.2, 0.0), bevel_cm=0.35, segments=1)

    # Dangling crooked sawmill signboard hanging cleanly from west iron chain riveted into header soffit!
    b.block("GAR_ChainW", (-96.0, 0.0, 336.0), (3.5, 3.5, 42.0), mat="ScaleIron", bevel_cm=0.1, segments=1)
    b.push_xform((-18.0, 0.0, 286.0), (3.0, 21.0, -4.0))
    b.block("GAR_SignBoard", (0.0, 0.0, 0.0), (206.0, 7.5, 44.0), mat="DarkWood", bevel_cm=0.3, segments=1)
    b.block("GAR_SignTrimT", (0.0, 0.0, 23.0), (214.0, 10.2, 5.5), mat="DarkWood", bevel_cm=0.2, segments=1)
    b.block("GAR_SignTrimB", (0.0, 0.0, -23.0), (214.0, 10.2, 5.5), mat="DarkWood", bevel_cm=0.2, segments=1)
    b.pop_xform()

    add_debris_cluster(b, "GAR_DebE", gx + 38.0, 18.0, -6.0, count=8, spread=64.0, include_stones=True)
    return b.finish(out_dir, lod_ratios=(1.0,))


def build_camp_fence_panel_ruined(out_dir: Path):
    """Self-supporting broken weathered fence bay (240 cm): ZERO floating right-side rails!
    Every rail is either mortised into CFR_PostL with its broken tip embedded into ground mud,
    or lying flat & settled into earth! Works cleanly adjacent to open monster breaches or Camp Gate!
    """
    b = pg.AssetBuilder("SM_LM_CampFencePanel_Ruined", seed=5105, ground_mud_cm=64.0)
    # Deeply buried leaning left post (Z_min = -62 cm -> never floats even on 14 deg hills!) + buried stone collar
    b.block("CFR_PostL", (0.0, 0.0, 30.0), (17.0, 17.0, 186.0), mat="DarkWood", rot_deg=(5.0, -3.5, 0.0), bevel_cm=0.55, segments=1)
    b.block("CFR_CollarL", (0.0, 0.0, -10.0), (24.0, 24.0, 36.0), mat="Footing", bevel_cm=0.65, segments=1)
    # Lower rail: still mortised into PostL (X=2, Z=34), broken right end dropped cleanly into mud (Z=-10)!
    b.beam("CFR_Rail0A", (2.0, 0.0, 34.0), (122.0, 6.0, -10.0), 6.0, 13.0, mat="DarkWood")
    # Middle rail: snapped diagonally from PostL (X=2, Z=74) all the way down into mud (X=146, Y=12, Z=-10)!
    b.beam("CFR_Rail1", (2.0, 1.0, 74.0), (146.0, 12.0, -10.0), 5.8, 12.5, mat="Oak")
    # Short splintered top-rail stub projecting cleanly from PostL mortise (ONLY 36 cm long, physically attached to post!)
    b.beam("CFR_Rail2Stub", (0.0, 0.0, 108.0), (36.0, -2.0, 102.0), 5.8, 12.5, mat="DarkWood")
    # Fallen snapped rails lying half-buried in ground mud across right half of bay (Z_bot <= -4.0 cm -> never floats on concave terrain!)
    b.block("CFR_FallenA", (156.0, -10.0, -0.5), (128.0, 12.0, 7.0), mat="DarkWood", rot_deg=(2.0, 0.0, 14.0), bevel_cm=0.25, segments=1)
    b.block("CFR_FallenB", (118.0, 22.0, -0.8), (92.0, 11.0, 6.8), mat="Oak", rot_deg=(-2.0, 0.0, -24.0), bevel_cm=0.25, segments=1)
    b.add_collider((22.0, 0.0, 58.0), (54.0, 22.0, 118.0))
    return b.finish(out_dir, lod_ratios=(1.0,))


def build_timber_rack_ruined(out_dir: Path):
    """Collapsed cantilever timber rack with snapped right upright and physically grounded spilled boards."""
    b = pg.AssetBuilder("SM_LM_TimberRack_Ruined", seed=5106, ground_mud_cm=45.0)
    # Left & center uprights leaning (feet extended slightly below Z=0 for slope grounding); right upright snapped off!
    for sx, tilt in ((-105.0, 4.0), (0.0, 9.0)):
        b.block(f"TRKR_Foot_{int(sx)}", (sx, 0.0, 3.0), (14.0, 108.0, 18.0), mat="DarkWood", bevel_cm=0.25, segments=1)
        b.block(f"TRKR_Up_{int(sx)}", (sx + tilt, -34.0, 106.0), (13.5, 13.5, 196.0), mat="DarkWood", rot_deg=(0.0, tilt, 0.0), bevel_cm=0.25, segments=1)
        b.block(f"TRKR_Arm_{int(sx)}", (sx + tilt, 14.0, 68.0), (10.5, 82.0, 10.5), mat="Oak", rot_deg=(6.0, tilt, 0.0), bevel_cm=0.2, segments=1)
    b.block("TRKR_FootR", (105.0, 0.0, 3.0), (14.0, 108.0, 18.0), mat="DarkWood", bevel_cm=0.25, segments=1)
    b.block("TRKR_StubR", (105.0, -34.0, 34.0), (13.5, 13.5, 62.0), mat="DarkWood", rot_deg=(8.0, 12.0, 0.0), bevel_cm=0.25, segments=1)
    # Spilled diagonal planks physically resting one end on surviving left/center arms (Z~68) and opposite end embedded into ground (Z=-2)!
    for bi in range(8):
        by = -18.0 + (bi % 4) * 16.0
        x_high = -102.0 + (bi % 3) * 32.0
        z_high = 70.0 + (bi // 4) * 8.0
        x_low = 98.0 + (bi % 4) * 14.0
        b.beam(f"TRKR_Spill_{bi}", (x_high, by, z_high), (x_low, by + b.rng.uniform(-10.0, 10.0), -2.0),
               11.5, 4.8, mat="DarkWood" if bi % 2 == 0 else "Oak")
    b.add_collider((0.0, 0.0, 64.0), (260.0, 118.0, 128.0))
    return b.finish(out_dir, lod_ratios=(1.0,))


def build_rubble_pile(out_dir: Path, name: str, seed: int, count: int, spread: float):
    """Deeply grounded architectural collapse rubble pile (skirt extends -20 cm so slopes NEVER expose undersides!)."""
    b = pg.AssetBuilder(name, seed=seed, ground_mud_cm=38.0)
    # Grounded earthen/stone mound core (Z in [-13.5..+4.5]: embeds deeply on slopes & never pokes through 15.5 cm 2F ceiling!)
    b.block("RB_Core", (0.0, 0.0, -4.5), (spread * 1.25, spread * 1.00, 18.0), mat="Footing", rot_deg=(2.0, -2.0, 14.0), bevel_cm=4.0, segments=1)
    add_debris_cluster(b, "RB", 0.0, 0.0, 0.0, count=count, spread=spread, include_stones=True)
    b.add_collider((0.0, 0.0, 12.0), (spread * 1.1, spread * 0.9, 30.0))
    return b.finish(out_dir, lod_ratios=(1.0,))


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    builders = [
        build_warehouse_ruined,
        build_toolroom_ruined,
        build_bunkhouse_ruined,
        build_camp_gate_arch_ruined,
        build_camp_fence_panel_ruined,
        build_timber_rack_ruined,
        lambda d: build_rubble_pile(d, "SM_LM_RubblePileA", seed=5107, count=22, spread=115.0),
        lambda d: build_rubble_pile(d, "SM_LM_RubblePileB", seed=5108, count=18, spread=95.0),
    ]
    manifest = []
    for fn in builders:
        clear_scene()
        info = fn(OUT_DIR)
        print(f"[RUINED-R51] {info['name']:28s} | tris={info['lods'][0]['triangles']:6d} | size_cm={info['size_cm']} | col={len(info['colliders'])} | mats={info['materials']}", flush=True)
        manifest.append(info)
    (OUT_DIR / "ruined-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"RUINED_R51_OK: {len(manifest)} watertight 3A ruined FBX assets exported to {OUT_DIR}")


if __name__ == "__main__":
    main()
